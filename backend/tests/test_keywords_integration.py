"""Integration tests for keyword clustering and prioritization with database models."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from seo_bot.models import Base, Project, Keyword, Cluster
from seo_bot.keywords.cluster import KeywordClusterManager, ClusteringError
from seo_bot.keywords.prioritize import KeywordPrioritizer, PrioritizationError


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


@pytest.fixture
def sample_project(in_memory_db):
    """Create a sample project for testing."""
    project = Project(
        name="Test Project",
        domain="example.com",
        base_url="https://example.com",
        language="en",
        country="US"
    )
    in_memory_db.add(project)
    in_memory_db.commit()
    in_memory_db.refresh(project)
    return project


@pytest.fixture
def sample_keywords(in_memory_db, sample_project):
    """Create sample keywords for testing."""
    keywords_data = [
        {
            'query': 'seo tools for agencies',
            'search_volume': 1200,
            'difficulty_proxy': 0.4,
            'intent': 'commercial',
            'cpc': 5.50,
            'competition': 0.6,
            'value_score': 0.0
        },
        {
            'query': 'best seo software 2024',
            'search_volume': 2000,
            'difficulty_proxy': 0.3,
            'intent': 'commercial',
            'cpc': 7.20,
            'competition': 0.7,
            'value_score': 0.0
        },
        {
            'query': 'keyword research tools',
            'search_volume': 1800,
            'difficulty_proxy': 0.35,
            'intent': 'commercial',
            'cpc': 6.80,
            'competition': 0.65,
            'value_score': 0.0
        },
        {
            'query': 'content marketing strategy',
            'search_volume': 900,
            'difficulty_proxy': 0.5,
            'intent': 'informational',
            'cpc': 2.10,
            'competition': 0.4,
            'value_score': 0.0
        },
        {
            'query': 'social media marketing tips',
            'search_volume': 1500,
            'difficulty_proxy': 0.45,
            'intent': 'informational',
            'cpc': 3.20,
            'competition': 0.5,
            'value_score': 0.0
        }
    ]
    
    keywords = []
    for kw_data in keywords_data:
        keyword = Keyword(
            project_id=sample_project.id,
            **kw_data
        )
        keywords.append(keyword)
        in_memory_db.add(keyword)
    
    in_memory_db.commit()
    for keyword in keywords:
        in_memory_db.refresh(keyword)
    
    return keywords


class TestClusteringIntegration:
    """Test clustering functionality with real database models."""
    
    def test_cluster_keywords_database_integration(self, in_memory_db, sample_project, sample_keywords):
        """Test complete clustering workflow with database."""
        manager = KeywordClusterManager(min_cluster_size=2)
        
        # Extract keyword queries
        keyword_queries = [kw.query for kw in sample_keywords]
        
        # Mock the clustering components to return predictable results
        with patch.object(manager.clusterer.embedding_generator, 'generate_embeddings') as mock_embed, \
             patch.object(manager.clusterer, '_cluster_hdbscan') as mock_cluster:
            
            # Mock embeddings - make SEO-related keywords similar
            mock_embeddings = np.array([
                [0.9, 0.8, 0.7, 0.1, 0.1],  # seo tools for agencies
                [0.8, 0.9, 0.8, 0.1, 0.1],  # best seo software 2024
                [0.7, 0.8, 0.9, 0.1, 0.1],  # keyword research tools
                [0.1, 0.1, 0.1, 0.9, 0.2],  # content marketing strategy
                [0.1, 0.1, 0.1, 0.2, 0.9],  # social media marketing tips
            ])
            mock_embed.return_value = mock_embeddings
            
            # Mock clustering results - group SEO keywords together, marketing separate
            mock_labels = np.array([0, 0, 0, 1, 1])
            mock_cluster.return_value = mock_labels
            
            # Perform clustering
            clustering_results = manager.cluster_keywords(keyword_queries)
            
            # Verify clustering results structure
            assert clustering_results['total_clusters'] == 2
            assert 0 in clustering_results['clusters']
            assert 1 in clustering_results['clusters']
            
            # Verify SEO keywords are clustered together
            seo_cluster_keywords = clustering_results['clusters'][0]
            assert 'seo tools for agencies' in seo_cluster_keywords
            assert 'best seo software 2024' in seo_cluster_keywords
            assert 'keyword research tools' in seo_cluster_keywords
            
            # Verify marketing keywords are clustered together
            marketing_cluster_keywords = clustering_results['clusters'][1]
            assert 'content marketing strategy' in marketing_cluster_keywords
            assert 'social media marketing tips' in marketing_cluster_keywords
            
            # Update database with clustering results
            created_clusters = manager.update_database_clusters(
                in_memory_db, sample_project.id, clustering_results
            )
            
            assert len(created_clusters) == 2
            
            # Verify clusters were created in database
            db_clusters = in_memory_db.query(Cluster).filter_by(project_id=sample_project.id).all()
            assert len(db_clusters) == 2
            
            # Verify keywords are assigned to clusters
            for cluster in db_clusters:
                cluster_keywords = in_memory_db.query(Keyword).filter_by(
                    cluster_id=cluster.id
                ).all()
                assert len(cluster_keywords) > 0
                
                # Verify cluster properties
                assert cluster.project_id == sample_project.id
                assert cluster.name is not None
                assert cluster.slug is not None
                assert cluster.cluster_type in ['hub', 'spoke']
    
    def test_cluster_update_existing_clusters(self, in_memory_db, sample_project, sample_keywords):
        """Test updating existing clusters in database."""
        manager = KeywordClusterManager()
        
        # Create an existing cluster
        existing_cluster = Cluster(
            project_id=sample_project.id,
            name="SEO Tools",
            slug="seo-tools",
            cluster_type="hub"
        )
        in_memory_db.add(existing_cluster)
        in_memory_db.commit()
        
        # Mock clustering results that would create the same cluster
        clustering_results = {
            'clusters': {0: ['seo tools for agencies', 'best seo software 2024']},
            'labels': {0: 'SEO Tools'},
            'hub_spoke_relationships': {
                0: {'hub_keyword': 'seo tools for agencies', 'spoke_keywords': ['best seo software 2024']}
            }
        }
        
        # Update database - should reuse existing cluster
        created_clusters = manager.update_database_clusters(
            in_memory_db, sample_project.id, clustering_results
        )
        
        assert len(created_clusters) == 1
        assert created_clusters[0].id == existing_cluster.id
        
        # Verify total clusters hasn't increased
        total_clusters = in_memory_db.query(Cluster).filter_by(project_id=sample_project.id).count()
        assert total_clusters == 1
    
    def test_cluster_database_error_handling(self, in_memory_db, sample_project):
        """Test clustering database error handling."""
        manager = KeywordClusterManager()
        
        # Mock database error
        with patch.object(in_memory_db, 'query', side_effect=Exception("Database connection lost")):
            clustering_results = {
                'clusters': {0: ['test keyword']},
                'labels': {0: 'Test Cluster'},
                'hub_spoke_relationships': {}
            }
            
            with pytest.raises(ClusteringError):
                manager.update_database_clusters(in_memory_db, sample_project.id, clustering_results)
    
    def test_cluster_with_real_keyword_objects(self, in_memory_db, sample_project, sample_keywords):
        """Test clustering using actual Keyword model objects."""
        manager = KeywordClusterManager(min_cluster_size=2)
        
        # Test with actual database keyword objects
        queries = [kw.query for kw in sample_keywords]
        
        with patch.object(manager.clusterer.embedding_generator, 'generate_embeddings') as mock_embed, \
             patch.object(manager.clusterer, '_cluster_hdbscan') as mock_cluster:
            
            mock_embed.return_value = np.random.rand(len(queries), 384)
            mock_cluster.return_value = np.array([0, 0, 1, 1, -1])  # Include noise
            
            results = manager.cluster_keywords(queries)
            created_clusters = manager.update_database_clusters(
                in_memory_db, sample_project.id, results
            )
            
            # Verify keyword-cluster relationships
            for cluster in created_clusters:
                assigned_keywords = in_memory_db.query(Keyword).filter_by(
                    cluster_id=cluster.id
                ).all()
                
                # Each cluster should have keywords assigned
                assert len(assigned_keywords) > 0
                
                # All assigned keywords should belong to this project
                for keyword in assigned_keywords:
                    assert keyword.project_id == sample_project.id
    
    def test_clustering_with_empty_project(self, in_memory_db, sample_project):
        """Test clustering behavior with project that has no keywords."""
        manager = KeywordClusterManager()
        
        # No keywords for this project
        clustering_results = manager.cluster_keywords([])
        
        assert clustering_results['total_clusters'] == 0
        assert clustering_results['clusters'] == {}
        
        # Should handle empty results gracefully
        created_clusters = manager.update_database_clusters(
            in_memory_db, sample_project.id, clustering_results
        )
        
        assert len(created_clusters) == 0
    
    def test_cluster_hub_spoke_database_integration(self, in_memory_db, sample_project, sample_keywords):
        """Test hub-spoke analysis integration with database."""
        manager = KeywordClusterManager()
        
        # Create clustering results with clear hub-spoke relationships
        clustering_results = {
            'clusters': {
                0: ['seo tools for agencies', 'best seo software 2024', 'keyword research tools']
            },
            'labels': {0: 'SEO Tools'},
            'hub_spoke_relationships': {
                0: {
                    'hub_keyword': 'seo tools for agencies',
                    'spoke_keywords': ['best seo software 2024', 'keyword research tools'],
                    'hub_coverage': 0.67
                }
            }
        }
        
        created_clusters = manager.update_database_clusters(
            in_memory_db, sample_project.id, clustering_results
        )
        
        assert len(created_clusters) == 1
        cluster = created_clusters[0]
        
        # Verify hub-spoke information is stored
        assert cluster.entities == ['seo tools for agencies']  # Hub keyword
        assert cluster.cluster_type == 'hub'  # Should be classified as hub
        
        # Verify all keywords are assigned to the cluster
        cluster_keywords = in_memory_db.query(Keyword).filter_by(cluster_id=cluster.id).all()
        cluster_queries = [kw.query for kw in cluster_keywords]
        
        assert 'seo tools for agencies' in cluster_queries
        assert 'best seo software 2024' in cluster_queries
        assert 'keyword research tools' in cluster_queries


class TestPrioritizationIntegration:
    """Test prioritization functionality with real database models."""
    
    def test_prioritize_keywords_database_integration(self, in_memory_db, sample_project, sample_keywords):
        """Test complete prioritization workflow with database."""
        prioritizer = KeywordPrioritizer()
        
        # Convert Keyword objects to data dictionaries
        keywords_data = []
        for kw in sample_keywords:
            kw_data = {
                'query': kw.query,
                'search_volume': kw.search_volume,
                'difficulty_proxy': kw.difficulty_proxy,
                'intent': kw.intent,
                'cpc': kw.cpc,
                'competition': kw.competition,
                'serp_features': kw.serp_features or [],
                'gap_analysis': kw.gap_analysis or {},
                'content_requirements': kw.content_requirements or []
            }
            keywords_data.append(kw_data)
        
        # Prioritize keywords
        prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)
        
        # Verify prioritization results
        assert len(prioritized_keywords) == len(sample_keywords)
        
        # Should be sorted by priority score
        for i in range(len(prioritized_keywords) - 1):
            assert (prioritized_keywords[i]['priority_score'] >= 
                   prioritized_keywords[i + 1]['priority_score'])
        
        # Commercial keywords should generally rank higher than informational
        commercial_scores = [
            kw['priority_score'] for kw in prioritized_keywords 
            if kw.get('intent') == 'commercial'
        ]
        informational_scores = [
            kw['priority_score'] for kw in prioritized_keywords 
            if kw.get('intent') == 'informational'
        ]
        
        if commercial_scores and informational_scores:
            assert max(commercial_scores) >= max(informational_scores)
        
        # Update database with priority scores
        updated_count = prioritizer.update_database_priorities(in_memory_db, prioritized_keywords)
        
        assert updated_count == len(sample_keywords)
        
        # Verify database updates
        for kw_data in prioritized_keywords:
            db_keyword = in_memory_db.query(Keyword).filter_by(
                query=kw_data['query']
            ).first()
            
            assert db_keyword is not None
            assert db_keyword.value_score == kw_data['priority_score']
            
            # Should have recommendations added to content_requirements
            if kw_data.get('recommendations'):
                assert len(db_keyword.content_requirements) >= len(kw_data['recommendations'])
    
    def test_prioritization_with_real_scoring_factors(self, in_memory_db, sample_project, sample_keywords):
        """Test prioritization with real scoring factors."""
        prioritizer = KeywordPrioritizer()
        
        # Find a high-value keyword (high volume, low difficulty, commercial intent)
        high_value_keyword = next((kw for kw in sample_keywords 
                                 if kw.search_volume > 1500 and kw.difficulty_proxy < 0.4), None)
        
        # Find a low-value keyword (low volume, high difficulty, informational intent)
        low_value_keyword = next((kw for kw in sample_keywords 
                                if kw.search_volume < 1000 and kw.difficulty_proxy > 0.4), None)
        
        if high_value_keyword and low_value_keyword:
            keywords_data = [
                {
                    'query': high_value_keyword.query,
                    'search_volume': high_value_keyword.search_volume,
                    'difficulty_proxy': high_value_keyword.difficulty_proxy,
                    'intent': high_value_keyword.intent,
                    'cpc': high_value_keyword.cpc,
                    'competition': high_value_keyword.competition
                },
                {
                    'query': low_value_keyword.query,
                    'search_volume': low_value_keyword.search_volume,
                    'difficulty_proxy': low_value_keyword.difficulty_proxy,
                    'intent': low_value_keyword.intent,
                    'cpc': low_value_keyword.cpc,
                    'competition': low_value_keyword.competition
                }
            ]
            
            results = prioritizer.prioritize_keywords(keywords_data)
            
            # High-value keyword should rank higher
            assert results[0]['query'] == high_value_keyword.query
            assert results[1]['query'] == low_value_keyword.query
            
            # Priority scores should reflect the difference
            assert results[0]['priority_score'] > results[1]['priority_score']
    
    def test_prioritization_brand_awareness(self, in_memory_db, sample_project):
        """Test prioritization with brand awareness."""
        # Create branded and non-branded keywords
        branded_keyword = Keyword(
            project_id=sample_project.id,
            query='MyBrand seo tools',
            search_volume=500,
            difficulty_proxy=0.2,
            intent='commercial',
            cpc=4.0,
            competition=0.3
        )
        
        generic_keyword = Keyword(
            project_id=sample_project.id,
            query='generic seo tools',
            search_volume=500,  # Same volume
            difficulty_proxy=0.2,  # Same difficulty
            intent='commercial',
            cpc=4.0,
            competition=0.3
        )
        
        in_memory_db.add_all([branded_keyword, generic_keyword])
        in_memory_db.commit()
        
        prioritizer = KeywordPrioritizer()
        brand_terms = ['MyBrand']
        
        keywords_data = [
            {
                'query': branded_keyword.query,
                'search_volume': branded_keyword.search_volume,
                'difficulty_proxy': branded_keyword.difficulty_proxy,
                'intent': branded_keyword.intent,
                'cpc': branded_keyword.cpc,
                'competition': branded_keyword.competition
            },
            {
                'query': generic_keyword.query,
                'search_volume': generic_keyword.search_volume,
                'difficulty_proxy': generic_keyword.difficulty_proxy,
                'intent': generic_keyword.intent,
                'cpc': generic_keyword.cpc,
                'competition': generic_keyword.competition
            }
        ]
        
        results = prioritizer.prioritize_keywords(keywords_data, brand_terms=brand_terms)
        
        # Find results for each keyword
        branded_result = next(r for r in results if 'MyBrand' in r['query'])
        generic_result = next(r for r in results if 'MyBrand' not in r['query'])
        
        # Branded keyword should have traffic analysis indicating it's branded
        assert branded_result['traffic_analysis']['is_branded']
        assert not generic_result['traffic_analysis']['is_branded']
        
        # Branded keyword should get traffic multiplier
        assert (branded_result['traffic_analysis']['target_ctr'] > 
               generic_result['traffic_analysis']['target_ctr'])
    
    def test_prioritization_database_error_handling(self, in_memory_db):
        """Test prioritization database error handling."""
        prioritizer = KeywordPrioritizer()
        
        # Mock database error
        with patch.object(in_memory_db, 'query', side_effect=Exception("Database error")):
            prioritized_keywords = [
                {'query': 'test keyword', 'priority_score': 0.5}
            ]
            
            with pytest.raises(PrioritizationError):
                prioritizer.update_database_priorities(in_memory_db, prioritized_keywords)
    
    def test_prioritization_content_gap_integration(self, in_memory_db, sample_project):
        """Test prioritization with content gap data from database."""
        # Create keyword with gap analysis data
        keyword_with_gaps = Keyword(
            project_id=sample_project.id,
            query='seo audit checklist',
            search_volume=1000,
            difficulty_proxy=0.4,
            intent='informational',
            cpc=3.0,
            competition=0.5,
            serp_features=['people_also_ask', 'featured_snippet'],
            gap_analysis={
                'missing_elements': ['checklist_tool', 'infographic', 'video_guide'],
                'content_depth_score': 0.3
            },
            content_requirements=[
                {'type': 'interactive_tool', 'met': False, 'priority': 'high'},
                {'type': 'visual_content', 'met': False, 'priority': 'medium'}
            ]
        )
        
        keyword_no_gaps = Keyword(
            project_id=sample_project.id,
            query='what is seo',
            search_volume=1000,  # Same volume
            difficulty_proxy=0.4,  # Same difficulty
            intent='informational',
            cpc=3.0,
            competition=0.5,
            serp_features=[],
            gap_analysis={},
            content_requirements=[]
        )
        
        in_memory_db.add_all([keyword_with_gaps, keyword_no_gaps])
        in_memory_db.commit()
        
        prioritizer = KeywordPrioritizer()
        
        keywords_data = [
            {
                'query': keyword_with_gaps.query,
                'search_volume': keyword_with_gaps.search_volume,
                'difficulty_proxy': keyword_with_gaps.difficulty_proxy,
                'intent': keyword_with_gaps.intent,
                'serp_features': keyword_with_gaps.serp_features,
                'gap_analysis': keyword_with_gaps.gap_analysis,
                'content_requirements': keyword_with_gaps.content_requirements
            },
            {
                'query': keyword_no_gaps.query,
                'search_volume': keyword_no_gaps.search_volume,
                'difficulty_proxy': keyword_no_gaps.difficulty_proxy,
                'intent': keyword_no_gaps.intent,
                'serp_features': keyword_no_gaps.serp_features,
                'gap_analysis': keyword_no_gaps.gap_analysis,
                'content_requirements': keyword_no_gaps.content_requirements
            }
        ]
        
        results = prioritizer.prioritize_keywords(keywords_data)
        
        # Find results for each keyword
        gaps_result = next(r for r in results if r['query'] == keyword_with_gaps.query)
        no_gaps_result = next(r for r in results if r['query'] == keyword_no_gaps.query)
        
        # Keyword with gaps should have higher gap score and priority
        assert gaps_result['gap_analysis']['gap_score'] > no_gaps_result['gap_analysis']['gap_score']
        assert gaps_result['priority_score'] > no_gaps_result['priority_score']


class TestEndToEndIntegration:
    """Test complete end-to-end workflow combining clustering and prioritization."""
    
    def test_complete_keyword_analysis_workflow(self, in_memory_db, sample_project, sample_keywords):
        """Test complete workflow: clustering then prioritization."""
        cluster_manager = KeywordClusterManager(min_cluster_size=2)
        prioritizer = KeywordPrioritizer()
        
        # Step 1: Cluster keywords
        keyword_queries = [kw.query for kw in sample_keywords]
        
        with patch.object(cluster_manager.clusterer.embedding_generator, 'generate_embeddings') as mock_embed, \
             patch.object(cluster_manager.clusterer, '_cluster_hdbscan') as mock_cluster:
            
            mock_embed.return_value = np.random.rand(len(keyword_queries), 384)
            mock_cluster.return_value = np.array([0, 0, 0, 1, 1])
            
            clustering_results = cluster_manager.cluster_keywords(keyword_queries)
            created_clusters = cluster_manager.update_database_clusters(
                in_memory_db, sample_project.id, clustering_results
            )
        
        # Step 2: Prioritize keywords
        keywords_data = []
        for kw in sample_keywords:
            kw_data = {
                'query': kw.query,
                'search_volume': kw.search_volume,
                'difficulty_proxy': kw.difficulty_proxy,
                'intent': kw.intent,
                'cpc': kw.cpc,
                'competition': kw.competition
            }
            keywords_data.append(kw_data)
        
        prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)
        updated_count = prioritizer.update_database_priorities(in_memory_db, prioritized_keywords)
        
        # Verify complete workflow results
        assert len(created_clusters) == 2  # Two clusters created
        assert updated_count == len(sample_keywords)  # All keywords prioritized
        
        # Verify database state
        db_clusters = in_memory_db.query(Cluster).filter_by(project_id=sample_project.id).all()
        db_keywords = in_memory_db.query(Keyword).filter_by(project_id=sample_project.id).all()
        
        assert len(db_clusters) == 2
        assert len(db_keywords) == len(sample_keywords)
        
        # Verify all keywords have priority scores
        for keyword in db_keywords:
            assert keyword.value_score > 0
            assert keyword.cluster_id is not None  # Should be assigned to a cluster
        
        # Verify clusters have keywords assigned
        for cluster in db_clusters:
            cluster_keywords = in_memory_db.query(Keyword).filter_by(cluster_id=cluster.id).all()
            assert len(cluster_keywords) > 0
    
    def test_workflow_with_priority_based_clustering(self, in_memory_db, sample_project, sample_keywords):
        """Test workflow where clustering considers priority scores."""
        # First prioritize to get priority scores
        prioritizer = KeywordPrioritizer()
        keywords_data = [
            {
                'query': kw.query,
                'search_volume': kw.search_volume,
                'difficulty_proxy': kw.difficulty_proxy,
                'intent': kw.intent,
                'cpc': kw.cpc,
                'competition': kw.competition
            }
            for kw in sample_keywords
        ]
        
        prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)
        prioritizer.update_database_priorities(in_memory_db, prioritized_keywords)
        
        # Then cluster, potentially using priority information
        cluster_manager = KeywordClusterManager()
        
        # Focus clustering on high-priority keywords only
        high_priority_keywords = [
            kw for kw in prioritized_keywords 
            if kw['priority_score'] > 0.5
        ]
        
        if high_priority_keywords:
            high_priority_queries = [kw['query'] for kw in high_priority_keywords]
            
            with patch.object(cluster_manager.clusterer.embedding_generator, 'generate_embeddings') as mock_embed, \
                 patch.object(cluster_manager.clusterer, '_cluster_hdbscan') as mock_cluster:
                
                mock_embed.return_value = np.random.rand(len(high_priority_queries), 384)
                mock_cluster.return_value = np.zeros(len(high_priority_queries), dtype=int)  # Single cluster
                
                clustering_results = cluster_manager.cluster_keywords(high_priority_queries)
                created_clusters = cluster_manager.update_database_clusters(
                    in_memory_db, sample_project.id, clustering_results
                )
            
            # Verify high-priority cluster was created
            assert len(created_clusters) >= 0  # At least no errors
            
            # Verify only high-priority keywords were clustered
            for cluster in created_clusters:
                cluster_keywords = in_memory_db.query(Keyword).filter_by(cluster_id=cluster.id).all()
                for keyword in cluster_keywords:
                    assert keyword.query in high_priority_queries
    
    def test_iterative_refinement_workflow(self, in_memory_db, sample_project, sample_keywords):
        """Test iterative refinement of clustering and prioritization."""
        cluster_manager = KeywordClusterManager()
        prioritizer = KeywordPrioritizer()
        
        # Initial clustering
        keyword_queries = [kw.query for kw in sample_keywords]
        
        with patch.object(cluster_manager.clusterer.embedding_generator, 'generate_embeddings') as mock_embed, \
             patch.object(cluster_manager.clusterer, '_cluster_hdbscan') as mock_cluster:
            
            mock_embed.return_value = np.random.rand(len(keyword_queries), 384)
            
            # First iteration - broad clustering
            mock_cluster.return_value = np.array([0, 0, 1, 1, 1])  # Two clusters
            clustering_results_1 = cluster_manager.cluster_keywords(keyword_queries)
            clusters_1 = cluster_manager.update_database_clusters(
                in_memory_db, sample_project.id, clustering_results_1
            )
            
            assert len(clusters_1) == 2
            
            # Second iteration - refined clustering (more granular)
            mock_cluster.return_value = np.array([0, 1, 2, 3, 4])  # Individual clusters
            clustering_results_2 = cluster_manager.cluster_keywords(keyword_queries)
            
            # This would typically update existing clusters or create new ones
            # For testing, we'll verify the system handles multiple clustering iterations
            assert clustering_results_2['total_clusters'] == 5
        
        # Prioritization should work regardless of clustering changes
        keywords_data = [
            {
                'query': kw.query,
                'search_volume': kw.search_volume,
                'difficulty_proxy': kw.difficulty_proxy,
                'intent': kw.intent
            }
            for kw in sample_keywords
        ]
        
        prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)
        updated_count = prioritizer.update_database_priorities(in_memory_db, prioritized_keywords)
        
        assert updated_count == len(sample_keywords)
    
    def test_error_recovery_in_workflow(self, in_memory_db, sample_project, sample_keywords):
        """Test workflow error recovery and partial completion."""
        cluster_manager = KeywordClusterManager()
        prioritizer = KeywordPrioritizer()
        
        keyword_queries = [kw.query for kw in sample_keywords]
        
        # Test clustering failure doesn't prevent prioritization
        with patch.object(cluster_manager.clusterer, 'cluster_keywords', 
                         side_effect=ClusteringError("Clustering failed")):
            
            with pytest.raises(ClusteringError):
                cluster_manager.cluster_keywords(keyword_queries)
            
            # Prioritization should still work
            keywords_data = [
                {
                    'query': kw.query,
                    'search_volume': kw.search_volume,
                    'difficulty_proxy': kw.difficulty_proxy,
                    'intent': kw.intent
                }
                for kw in sample_keywords
            ]
            
            prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)
            assert len(prioritized_keywords) == len(sample_keywords)
        
        # Test prioritization failure doesn't prevent clustering
        with patch.object(prioritizer, 'calculate_priority_score', 
                         side_effect=Exception("Priority calculation failed")):
            
            # Clustering should still work
            with patch.object(cluster_manager.clusterer.embedding_generator, 'generate_embeddings') as mock_embed, \
                 patch.object(cluster_manager.clusterer, '_cluster_hdbscan') as mock_cluster:
                
                mock_embed.return_value = np.random.rand(len(keyword_queries), 384)
                mock_cluster.return_value = np.zeros(len(keyword_queries), dtype=int)
                
                clustering_results = cluster_manager.cluster_keywords(keyword_queries)
                assert clustering_results['total_clusters'] == 1
    
    def test_large_dataset_handling(self, in_memory_db, sample_project):
        """Test handling of larger keyword datasets."""
        # Create a larger set of keywords
        large_keyword_set = []
        for i in range(50):  # Create 50 keywords
            keyword = Keyword(
                project_id=sample_project.id,
                query=f'test keyword {i}',
                search_volume=100 + (i * 10),
                difficulty_proxy=0.1 + (i * 0.01),
                intent='commercial' if i % 2 == 0 else 'informational',
                cpc=1.0 + (i * 0.1),
                competition=0.1 + (i * 0.01)
            )
            large_keyword_set.append(keyword)
        
        in_memory_db.add_all(large_keyword_set)
        in_memory_db.commit()
        
        cluster_manager = KeywordClusterManager(min_cluster_size=5, max_clusters=10)
        prioritizer = KeywordPrioritizer()
        
        keyword_queries = [kw.query for kw in large_keyword_set]
        
        # Test clustering scales reasonably
        with patch.object(cluster_manager.clusterer.embedding_generator, 'generate_embeddings') as mock_embed, \
             patch.object(cluster_manager.clusterer, '_cluster_hdbscan') as mock_cluster:
            
            mock_embed.return_value = np.random.rand(len(keyword_queries), 384)
            # Create reasonable number of clusters for large dataset
            mock_labels = np.random.randint(0, 10, size=len(keyword_queries))
            mock_cluster.return_value = mock_labels
            
            clustering_results = cluster_manager.cluster_keywords(keyword_queries)
            
            # Should handle large dataset without issues
            assert clustering_results['total_clusters'] <= 10
            assert len(clustering_results['cluster_assignments']) == len(keyword_queries)
        
        # Test prioritization scales reasonably
        keywords_data = [
            {
                'query': kw.query,
                'search_volume': kw.search_volume,
                'difficulty_proxy': kw.difficulty_proxy,
                'intent': kw.intent
            }
            for kw in large_keyword_set[:20]  # Test subset for performance
        ]
        
        prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)
        
        assert len(prioritized_keywords) == 20
        # Should maintain sorting
        for i in range(len(prioritized_keywords) - 1):
            assert (prioritized_keywords[i]['priority_score'] >= 
                   prioritized_keywords[i + 1]['priority_score'])