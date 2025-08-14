"""Tests for keyword clustering functionality."""

import numpy as np
import pytest
from unittest.mock import Mock, patch, MagicMock

from seo_bot.keywords.cluster import (
    EmbeddingGenerator,
    KeywordClusterer,
    ClusterLabeler,
    HubSpokeAnalyzer,
    KeywordClusterManager,
    ClusteringError,
    create_cluster_manager,
)


class TestEmbeddingGenerator:
    """Test embedding generation with fallback options."""
    
    def test_init_default(self):
        """Test default initialization."""
        generator = EmbeddingGenerator()
        assert generator.model_name == "all-MiniLM-L6-v2"
        assert generator._model is None
        assert generator._fallback_mode is False
    
    def test_init_custom_model(self):
        """Test initialization with custom model."""
        generator = EmbeddingGenerator("custom-model")
        assert generator.model_name == "custom-model"
    
    @patch('seo_bot.keywords.cluster.logger')
    def test_load_model_success(self, mock_logger):
        """Test successful model loading."""
        with patch('seo_bot.keywords.cluster.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_st.return_value = mock_model
            
            generator = EmbeddingGenerator()
            generator._load_model()
            
            assert generator._model == mock_model
            assert generator._fallback_mode is False
            mock_logger.info.assert_called_once()
    
    @patch('seo_bot.keywords.cluster.logger')
    def test_load_model_import_error(self, mock_logger):
        """Test fallback on ImportError."""
        with patch('seo_bot.keywords.cluster.SentenceTransformer', side_effect=ImportError):
            generator = EmbeddingGenerator()
            generator._load_model()
            
            assert generator._model is None
            assert generator._fallback_mode is True
            mock_logger.warning.assert_called_once()
    
    @patch('seo_bot.keywords.cluster.logger')
    def test_load_model_other_error(self, mock_logger):
        """Test fallback on other errors."""
        with patch('seo_bot.keywords.cluster.SentenceTransformer', side_effect=RuntimeError("Model error")):
            generator = EmbeddingGenerator()
            generator._load_model()
            
            assert generator._model is None
            assert generator._fallback_mode is True
            assert mock_logger.error.call_count == 1
            assert mock_logger.warning.call_count == 1
    
    def test_generate_tfidf_embeddings(self):
        """Test TF-IDF embedding generation."""
        with patch('seo_bot.keywords.cluster.TfidfVectorizer') as mock_tfidf, \
             patch('seo_bot.keywords.cluster.TruncatedSVD') as mock_svd:
            
            # Mock TF-IDF vectorizer
            mock_vectorizer = Mock()
            mock_matrix = Mock()
            mock_matrix.shape = (3, 1000)
            mock_vectorizer.fit_transform.return_value = mock_matrix
            mock_tfidf.return_value = mock_vectorizer
            
            # Mock SVD
            mock_svd_instance = Mock()
            mock_embeddings = np.random.rand(3, 384).astype(np.float32)
            mock_svd_instance.fit_transform.return_value = mock_embeddings
            mock_svd.return_value = mock_svd_instance
            
            generator = EmbeddingGenerator()
            texts = ["keyword one", "keyword two", "keyword three"]
            embeddings = generator._generate_tfidf_embeddings(texts)
            
            assert isinstance(embeddings, np.ndarray)
            assert embeddings.dtype == np.float32
    
    def test_generate_tfidf_embeddings_import_error(self):
        """Test TF-IDF fallback ImportError."""
        with patch('seo_bot.keywords.cluster.TfidfVectorizer', side_effect=ImportError):
            generator = EmbeddingGenerator()
            with pytest.raises(ClusteringError):
                generator._generate_tfidf_embeddings(["test"])
    
    def test_generate_embeddings_empty_input(self):
        """Test handling of empty input."""
        generator = EmbeddingGenerator()
        embeddings = generator.generate_embeddings([])
        
        assert embeddings.shape == (0, 384)
    
    def test_generate_embeddings_sentence_transformer(self):
        """Test embedding generation with sentence transformer."""
        with patch('seo_bot.keywords.cluster.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_embeddings = np.random.rand(2, 384).astype(np.float32)
            mock_model.encode.return_value = mock_embeddings
            mock_st.return_value = mock_model
            
            generator = EmbeddingGenerator()
            generator._load_model()
            
            texts = ["keyword one", "keyword two"]
            embeddings = generator.generate_embeddings(texts)
            
            assert isinstance(embeddings, np.ndarray)
            assert embeddings.shape == (2, 384)
            assert embeddings.dtype == np.float32
    
    def test_generate_embeddings_fallback_mode(self):
        """Test embedding generation in fallback mode."""
        generator = EmbeddingGenerator()
        generator._fallback_mode = True
        
        with patch.object(generator, '_generate_tfidf_embeddings') as mock_tfidf:
            mock_embeddings = np.random.rand(2, 384).astype(np.float32)
            mock_tfidf.return_value = mock_embeddings
            
            texts = ["keyword one", "keyword two"]
            embeddings = generator.generate_embeddings(texts)
            
            assert isinstance(embeddings, np.ndarray)
            mock_tfidf.assert_called_once_with(texts)


class TestKeywordClusterer:
    """Test keyword clustering functionality."""
    
    def test_init_default(self):
        """Test default initialization."""
        clusterer = KeywordClusterer()
        assert clusterer.min_cluster_size == 3
        assert clusterer.min_samples == 2
        assert clusterer.cluster_selection_epsilon == 0.5
        assert clusterer.max_clusters == 50
        assert isinstance(clusterer.embedding_generator, EmbeddingGenerator)
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        clusterer = KeywordClusterer(
            min_cluster_size=5,
            min_samples=3,
            cluster_selection_epsilon=0.3,
            max_clusters=20
        )
        assert clusterer.min_cluster_size == 5
        assert clusterer.min_samples == 3
        assert clusterer.cluster_selection_epsilon == 0.3
        assert clusterer.max_clusters == 20
    
    def test_preprocess_keywords(self):
        """Test keyword preprocessing."""
        clusterer = KeywordClusterer()
        keywords = ["Best SEO Tools!", "seo   tools", "SEO-Tools & More"]
        processed = clusterer._preprocess_keywords(keywords)
        
        expected = ["best seo tools", "seo tools", "seo tools more"]
        assert processed == expected
    
    def test_cluster_hdbscan_success(self):
        """Test HDBSCAN clustering success."""
        with patch('seo_bot.keywords.cluster.hdbscan') as mock_hdbscan:
            mock_clusterer = Mock()
            mock_labels = np.array([0, 0, 1, 1, -1])
            mock_clusterer.fit_predict.return_value = mock_labels
            mock_hdbscan.HDBSCAN.return_value = mock_clusterer
            
            clusterer = KeywordClusterer()
            embeddings = np.random.rand(5, 384)
            labels = clusterer._cluster_hdbscan(embeddings)
            
            assert np.array_equal(labels, mock_labels)
            mock_hdbscan.HDBSCAN.assert_called_once_with(
                min_cluster_size=3,
                min_samples=2,
                cluster_selection_epsilon=0.5,
                metric='cosine'
            )
    
    @patch('seo_bot.keywords.cluster.logger')
    def test_cluster_hdbscan_fallback(self, mock_logger):
        """Test HDBSCAN fallback to K-means."""
        with patch('seo_bot.keywords.cluster.hdbscan', side_effect=ImportError):
            clusterer = KeywordClusterer()
            
            with patch.object(clusterer, '_cluster_kmeans') as mock_kmeans:
                mock_labels = np.array([0, 0, 1, 1, 1])
                mock_kmeans.return_value = mock_labels
                
                embeddings = np.random.rand(5, 384)
                labels = clusterer._cluster_hdbscan(embeddings)
                
                assert np.array_equal(labels, mock_labels)
                mock_logger.warning.assert_called_once()
                mock_kmeans.assert_called_once_with(embeddings)
    
    def test_cluster_kmeans_success(self):
        """Test K-means clustering success."""
        with patch('seo_bot.keywords.cluster.KMeans') as mock_kmeans, \
             patch('seo_bot.keywords.cluster.silhouette_score') as mock_silhouette:
            
            # Mock KMeans
            mock_model = Mock()
            mock_labels = np.array([0, 0, 1, 1, 1])
            mock_model.fit_predict.return_value = mock_labels
            mock_kmeans.return_value = mock_model
            
            # Mock silhouette score
            mock_silhouette.return_value = 0.5
            
            clusterer = KeywordClusterer()
            embeddings = np.random.rand(5, 384)
            labels = clusterer._cluster_kmeans(embeddings)
            
            assert np.array_equal(labels, mock_labels)
    
    def test_cluster_kmeans_few_samples(self):
        """Test K-means with few samples."""
        clusterer = KeywordClusterer()
        embeddings = np.random.rand(1, 384)
        labels = clusterer._cluster_kmeans(embeddings)
        
        expected = np.zeros(1, dtype=int)
        assert np.array_equal(labels, expected)
    
    def test_cluster_keywords_success(self):
        """Test complete keyword clustering."""
        keywords = [
            "best seo tools",
            "seo software reviews", 
            "keyword research tools",
            "content marketing strategy",
            "social media marketing"
        ]
        
        clusterer = KeywordClusterer()
        
        with patch.object(clusterer.embedding_generator, 'generate_embeddings') as mock_embed, \
             patch.object(clusterer, '_cluster_hdbscan') as mock_cluster:
            
            # Mock embeddings
            mock_embeddings = np.random.rand(5, 384)
            mock_embed.return_value = mock_embeddings
            
            # Mock clustering
            mock_labels = np.array([0, 0, 0, 1, 1])
            mock_cluster.return_value = mock_labels
            
            labels, embeddings = clusterer.cluster_keywords(keywords)
            
            assert np.array_equal(labels, mock_labels)
            assert np.array_equal(embeddings, mock_embeddings)
    
    def test_cluster_keywords_few_keywords(self):
        """Test clustering with few keywords."""
        clusterer = KeywordClusterer()
        keywords = ["single keyword"]
        
        labels, embeddings = clusterer.cluster_keywords(keywords)
        
        expected_labels = np.zeros(1, dtype=int)
        assert np.array_equal(labels, expected_labels)
        assert embeddings.size == 0
    
    def test_cluster_keywords_error(self):
        """Test clustering error handling."""
        clusterer = KeywordClusterer()
        keywords = ["keyword one", "keyword two"]
        
        with patch.object(clusterer.embedding_generator, 'generate_embeddings', 
                         side_effect=Exception("Embedding error")):
            with pytest.raises(ClusteringError):
                clusterer.cluster_keywords(keywords)


class TestClusterLabeler:
    """Test cluster labeling functionality."""
    
    def test_init_default(self):
        """Test default initialization."""
        labeler = ClusterLabeler()
        assert labeler.min_ngram_freq == 2
    
    def test_init_custom_freq(self):
        """Test initialization with custom frequency."""
        labeler = ClusterLabeler(min_ngram_freq=3)
        assert labeler.min_ngram_freq == 3
    
    def test_extract_ngrams(self):
        """Test n-gram extraction."""
        labeler = ClusterLabeler()
        text = "best seo tools for small business"
        
        bigrams = labeler._extract_ngrams(text, n=2)
        expected = ["best seo", "seo tools", "tools for", "for small", "small business"]
        assert bigrams == expected
    
    def test_extract_ngrams_short_text(self):
        """Test n-gram extraction with short text."""
        labeler = ClusterLabeler()
        text = "seo"
        
        bigrams = labeler._extract_ngrams(text, n=2)
        assert bigrams == ["seo"]
    
    def test_get_stopwords_with_nltk(self):
        """Test stopwords with NLTK available."""
        with patch('seo_bot.keywords.cluster.nltk') as mock_nltk, \
             patch('seo_bot.keywords.cluster.stopwords') as mock_stopwords:
            
            mock_stopwords.words.return_value = ['a', 'an', 'the']
            
            labeler = ClusterLabeler()
            stopwords = labeler._get_stopwords()
            
            assert stopwords == {'a', 'an', 'the'}
    
    def test_get_stopwords_fallback(self):
        """Test stopwords fallback when NLTK unavailable."""
        with patch('seo_bot.keywords.cluster.nltk', side_effect=ImportError):
            labeler = ClusterLabeler()
            stopwords = labeler._get_stopwords()
            
            assert isinstance(stopwords, set)
            assert 'the' in stopwords
            assert 'and' in stopwords
    
    def test_generate_cluster_labels(self):
        """Test cluster label generation."""
        labeler = ClusterLabeler()
        
        keywords_by_cluster = {
            0: ["seo tools", "best seo tools", "seo software"],
            1: ["content marketing", "content strategy", "marketing content"],
            -1: ["random keyword"]
        }
        
        with patch.object(labeler, '_get_stopwords', return_value={'the', 'for', 'best'}):
            labels = labeler.generate_cluster_labels(keywords_by_cluster)
            
            assert labels[-1] == "Miscellaneous"
            assert "seo" in labels[0].lower() or "tools" in labels[0].lower()
            assert "content" in labels[1].lower() or "marketing" in labels[1].lower()
    
    def test_generate_cluster_labels_empty(self):
        """Test label generation for empty cluster."""
        labeler = ClusterLabeler()
        keywords_by_cluster = {0: []}
        
        labels = labeler.generate_cluster_labels(keywords_by_cluster)
        assert labels[0] == "Cluster 0"
    
    def test_generate_cluster_labels_fallback(self):
        """Test fallback label generation."""
        labeler = ClusterLabeler()
        keywords_by_cluster = {
            0: ["very unique uncommon phrase"]
        }
        
        with patch.object(labeler, '_get_stopwords', return_value=set()):
            labels = labeler.generate_cluster_labels(keywords_by_cluster)
            
            assert labels[0] == "Very Unique Uncommon Phrase"


class TestHubSpokeAnalyzer:
    """Test hub-spoke relationship analysis."""
    
    def test_init_default(self):
        """Test default initialization."""
        analyzer = HubSpokeAnalyzer()
        assert analyzer.hub_threshold == 0.7
    
    def test_init_custom_threshold(self):
        """Test initialization with custom threshold."""
        analyzer = HubSpokeAnalyzer(hub_threshold=0.8)
        assert analyzer.hub_threshold == 0.8
    
    def test_calculate_similarity_matrix_sklearn(self):
        """Test similarity matrix calculation with sklearn."""
        with patch('seo_bot.keywords.cluster.cosine_similarity') as mock_cosine:
            mock_matrix = np.array([[1.0, 0.8], [0.8, 1.0]])
            mock_cosine.return_value = mock_matrix
            
            analyzer = HubSpokeAnalyzer()
            embeddings = np.random.rand(2, 384)
            
            similarity = analyzer._calculate_similarity_matrix(embeddings)
            assert np.array_equal(similarity, mock_matrix)
    
    def test_calculate_similarity_matrix_manual(self):
        """Test manual similarity matrix calculation."""
        with patch('seo_bot.keywords.cluster.cosine_similarity', side_effect=ImportError):
            analyzer = HubSpokeAnalyzer()
            embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
            
            similarity = analyzer._calculate_similarity_matrix(embeddings)
            
            assert similarity.shape == (2, 2)
            assert similarity[0, 0] == pytest.approx(1.0)
            assert similarity[1, 1] == pytest.approx(1.0)
            assert similarity[0, 1] == pytest.approx(0.0)
    
    def test_find_cluster_hub_single_keyword(self):
        """Test hub finding with single keyword."""
        analyzer = HubSpokeAnalyzer()
        keywords = ["single keyword"]
        embeddings = np.random.rand(1, 384)
        
        hub, spokes = analyzer._find_cluster_hub(keywords, embeddings)
        
        assert hub == "single keyword"
        assert spokes == []
    
    def test_find_cluster_hub_multiple_keywords(self):
        """Test hub finding with multiple keywords."""
        analyzer = HubSpokeAnalyzer(hub_threshold=0.6)
        keywords = ["seo tools", "best seo tools", "seo software"]
        
        # Create mock similarity matrix
        similarity_matrix = np.array([
            [1.0, 0.8, 0.7],  # seo tools
            [0.8, 1.0, 0.9],  # best seo tools (should be hub)
            [0.7, 0.9, 1.0]   # seo software
        ])
        
        with patch.object(analyzer, '_calculate_similarity_matrix', return_value=similarity_matrix):
            embeddings = np.random.rand(3, 384)
            hub, spokes = analyzer._find_cluster_hub(keywords, embeddings)
            
            assert hub == "best seo tools"  # Highest average similarity
            assert "seo tools" in spokes or "seo software" in spokes
    
    def test_analyze_hub_spoke_relationships(self):
        """Test complete hub-spoke analysis."""
        analyzer = HubSpokeAnalyzer()
        
        keywords_by_cluster = {
            0: ["seo tools", "best seo tools", "seo software"],
            1: ["content marketing", "content strategy"]
        }
        
        embeddings_by_cluster = {
            0: np.random.rand(3, 384),
            1: np.random.rand(2, 384)
        }
        
        with patch.object(analyzer, '_find_cluster_hub') as mock_hub:
            mock_hub.side_effect = [
                ("best seo tools", ["seo tools", "seo software"]),
                ("content marketing", ["content strategy"])
            ]
            
            relationships = analyzer.analyze_hub_spoke_relationships(
                keywords_by_cluster, embeddings_by_cluster
            )
            
            assert 0 in relationships
            assert 1 in relationships
            assert relationships[0]['hub_keyword'] == "best seo tools"
            assert relationships[0]['total_keywords'] == 3
            assert relationships[0]['hub_coverage'] == 1.0  # 2 spokes / (3-1) total
    
    def test_analyze_hub_spoke_relationships_skip_noise(self):
        """Test skipping noise cluster."""
        analyzer = HubSpokeAnalyzer()
        
        keywords_by_cluster = {
            -1: ["noise keyword"],
            0: ["seo tools", "best seo tools"]
        }
        
        embeddings_by_cluster = {
            -1: np.random.rand(1, 384),
            0: np.random.rand(2, 384)
        }
        
        with patch.object(analyzer, '_find_cluster_hub') as mock_hub:
            mock_hub.return_value = ("seo tools", ["best seo tools"])
            
            relationships = analyzer.analyze_hub_spoke_relationships(
                keywords_by_cluster, embeddings_by_cluster
            )
            
            assert -1 not in relationships
            assert 0 in relationships


class TestKeywordClusterManager:
    """Test main cluster manager functionality."""
    
    def test_init_default(self):
        """Test default initialization."""
        manager = KeywordClusterManager()
        
        assert isinstance(manager.clusterer, KeywordClusterer)
        assert isinstance(manager.labeler, ClusterLabeler)
        assert isinstance(manager.hub_spoke_analyzer, HubSpokeAnalyzer)
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        manager = KeywordClusterManager(
            min_cluster_size=5,
            max_clusters=20
        )
        
        assert manager.clusterer.min_cluster_size == 5
        assert manager.clusterer.max_clusters == 20
    
    def test_cluster_keywords_empty(self):
        """Test clustering with empty keyword list."""
        manager = KeywordClusterManager()
        result = manager.cluster_keywords([])
        
        assert result['total_clusters'] == 0
        assert result['clusters'] == {}
        assert result['noise_keywords'] == []
    
    def test_cluster_keywords_success(self):
        """Test successful keyword clustering."""
        manager = KeywordClusterManager()
        keywords = [
            "seo tools", "best seo tools", "seo software",
            "content marketing", "content strategy"
        ]
        
        # Mock clustering results
        cluster_labels = np.array([0, 0, 0, 1, 1])
        embeddings = np.random.rand(5, 384)
        
        with patch.object(manager.clusterer, 'cluster_keywords') as mock_cluster, \
             patch.object(manager.labeler, 'generate_cluster_labels') as mock_label, \
             patch.object(manager.hub_spoke_analyzer, 'analyze_hub_spoke_relationships') as mock_hub:
            
            mock_cluster.return_value = (cluster_labels, embeddings)
            mock_label.return_value = {0: "SEO Tools", 1: "Content Marketing"}
            mock_hub.return_value = {
                0: {'hub_keyword': 'seo tools', 'spoke_keywords': ['best seo tools'], 'hub_coverage': 0.5},
                1: {'hub_keyword': 'content marketing', 'spoke_keywords': ['content strategy'], 'hub_coverage': 1.0}
            }
            
            result = manager.cluster_keywords(keywords)
            
            assert result['total_clusters'] == 2
            assert 0 in result['clusters']
            assert 1 in result['clusters']
            assert result['labels'][0] == "SEO Tools"
            assert result['labels'][1] == "Content Marketing"
    
    def test_cluster_keywords_with_noise(self):
        """Test clustering with noise cluster."""
        manager = KeywordClusterManager()
        keywords = ["keyword1", "keyword2", "noise"]
        
        cluster_labels = np.array([0, 0, -1])
        embeddings = np.random.rand(3, 384)
        
        with patch.object(manager.clusterer, 'cluster_keywords') as mock_cluster, \
             patch.object(manager.labeler, 'generate_cluster_labels') as mock_label, \
             patch.object(manager.hub_spoke_analyzer, 'analyze_hub_spoke_relationships') as mock_hub:
            
            mock_cluster.return_value = (cluster_labels, embeddings)
            mock_label.return_value = {0: "Cluster 0", -1: "Miscellaneous"}
            mock_hub.return_value = {0: {'hub_keyword': 'keyword1', 'spoke_keywords': ['keyword2']}}
            
            result = manager.cluster_keywords(keywords)
            
            assert result['noise_keywords'] == ["noise"]
            assert -1 not in result['clusters']
            assert result['total_clusters'] == 1
    
    def test_cluster_keywords_error(self):
        """Test clustering error handling."""
        manager = KeywordClusterManager()
        keywords = ["keyword1", "keyword2"]
        
        with patch.object(manager.clusterer, 'cluster_keywords', 
                         side_effect=Exception("Clustering failed")):
            with pytest.raises(ClusteringError):
                manager.cluster_keywords(keywords)
    
    @patch('seo_bot.keywords.cluster.logger')
    def test_update_database_clusters_success(self, mock_logger):
        """Test successful database cluster update."""
        manager = KeywordClusterManager()
        
        # Mock database objects
        mock_db = Mock()
        mock_project_id = "test-project"
        
        # Mock existing keyword
        mock_keyword = Mock()
        mock_db.query().filter_by().first.return_value = mock_keyword
        
        clustering_results = {
            'clusters': {0: ["test keyword"]},
            'labels': {0: "Test Cluster"},
            'hub_spoke_relationships': {0: {'hub_keyword': 'test keyword', 'hub_coverage': 1.0}}
        }
        
        # Mock cluster creation
        with patch('seo_bot.keywords.cluster.Cluster') as mock_cluster_class:
            mock_cluster = Mock()
            mock_cluster_class.return_value = mock_cluster
            
            result = manager.update_database_clusters(mock_db, mock_project_id, clustering_results)
            
            assert len(result) == 1
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    def test_update_database_clusters_error(self):
        """Test database update error handling."""
        manager = KeywordClusterManager()
        
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database error")
        
        clustering_results = {'clusters': {0: ["test"]}, 'labels': {0: "Test"}, 'hub_spoke_relationships': {}}
        
        with pytest.raises(ClusteringError):
            manager.update_database_clusters(mock_db, "test-project", clustering_results)
        
        mock_db.rollback.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_cluster_manager_default(self):
        """Test creating cluster manager with defaults."""
        manager = create_cluster_manager()
        assert isinstance(manager, KeywordClusterManager)
    
    def test_create_cluster_manager_custom(self):
        """Test creating cluster manager with custom parameters."""
        manager = create_cluster_manager(min_cluster_size=10, max_clusters=30)
        assert manager.clusterer.min_cluster_size == 10
        assert manager.clusterer.max_clusters == 30


# Integration-like tests
class TestClusteringIntegration:
    """Test clustering components working together."""
    
    def test_full_clustering_pipeline(self):
        """Test complete clustering pipeline."""
        keywords = [
            "best seo tools 2024",
            "seo software reviews",
            "keyword research tools",
            "content marketing strategy",
            "social media marketing tips",
            "email marketing automation"
        ]
        
        manager = KeywordClusterManager(min_cluster_size=2)
        
        # This would normally use real ML libraries, but for testing we'll mock
        with patch.object(manager.clusterer.embedding_generator, 'generate_embeddings') as mock_embed:
            # Create realistic embeddings (closer for related keywords)
            mock_embeddings = np.array([
                [1.0, 0.8, 0.2, 0.1, 0.1, 0.1],  # seo tools
                [0.8, 1.0, 0.7, 0.1, 0.1, 0.1],  # seo software
                [0.2, 0.7, 1.0, 0.1, 0.1, 0.1],  # keyword research
                [0.1, 0.1, 0.1, 1.0, 0.8, 0.2],  # content marketing
                [0.1, 0.1, 0.1, 0.8, 1.0, 0.3],  # social media
                [0.1, 0.1, 0.1, 0.2, 0.3, 1.0],  # email marketing
            ])
            mock_embed.return_value = mock_embeddings
            
            # Test with fallback clustering (no ML libraries)
            with patch('seo_bot.keywords.cluster.hdbscan', side_effect=ImportError), \
                 patch('seo_bot.keywords.cluster.KMeans', side_effect=ImportError), \
                 patch('seo_bot.keywords.cluster.AgglomerativeClustering', side_effect=ImportError):
                
                with pytest.raises(ClusteringError):
                    manager.cluster_keywords(keywords)
    
    def test_clustering_with_various_keyword_types(self):
        """Test clustering with different types of keywords."""
        keywords = [
            "seo",  # Short
            "best seo tools for small business websites",  # Long-tail
            "SEO Tools & Software!",  # Special characters
            "   seo    tools   ",  # Extra spaces
            ""  # Empty (should be filtered)
        ]
        
        # Filter empty keywords
        keywords = [k for k in keywords if k.strip()]
        
        manager = KeywordClusterManager()
        
        # Mock the clustering to return reasonable results
        with patch.object(manager.clusterer, 'cluster_keywords') as mock_cluster:
            mock_labels = np.array([0, 0, 0, 0])
            mock_embeddings = np.random.rand(4, 384)
            mock_cluster.return_value = (mock_labels, mock_embeddings)
            
            result = manager.cluster_keywords(keywords)
            
            # Should handle all keyword types gracefully
            assert result['total_clusters'] == 1
            assert len(result['cluster_assignments']) == 4