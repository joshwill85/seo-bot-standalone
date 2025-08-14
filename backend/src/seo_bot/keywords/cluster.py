"""Keyword clustering module for SEO-Bot.

This module provides functionality for clustering keywords based on semantic similarity,
identifying hub/spoke relationships, generating cluster labels, and building topic hierarchies
with statistical validation.
"""

import logging
import re
import statistics
import traceback
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from sqlalchemy.orm import Session

from ..models import Cluster, Keyword

logger = logging.getLogger(__name__)


class ClusteringError(Exception):
    """Base exception for clustering operations."""
    pass


class EmbeddingGenerator:
    """Generates text embeddings with fallback options."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize embedding generator.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        self._model: Optional[Any] = None
        self._fallback_mode = False
        
    def _load_model(self) -> None:
        """Load the sentence transformer model with fallback."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded sentence transformer model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, using fallback TF-IDF")
            self._fallback_mode = True
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            logger.warning("Falling back to TF-IDF embeddings")
            self._fallback_mode = True
    
    def _generate_tfidf_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate TF-IDF embeddings as fallback.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Array of embeddings with shape (n_texts, n_features)
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.decomposition import TruncatedSVD
            
            # Use TF-IDF with SVD dimensionality reduction
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            # Reduce dimensions to 384 to match sentence transformer output
            n_components = min(384, tfidf_matrix.shape[1], len(texts) - 1)
            if n_components > 0:
                svd = TruncatedSVD(n_components=n_components, random_state=42)
                embeddings = svd.fit_transform(tfidf_matrix)
            else:
                embeddings = tfidf_matrix.toarray()
            
            return embeddings.astype(np.float32)
            
        except ImportError:
            raise ClusteringError("Neither sentence-transformers nor scikit-learn available")
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Array of embeddings with shape (n_texts, embedding_dim)
            
        Raises:
            ClusteringError: If embedding generation fails
        """
        if not texts:
            return np.array([]).reshape(0, 384)
        
        if self._model is None:
            self._load_model()
        
        try:
            if self._fallback_mode:
                return self._generate_tfidf_embeddings(texts)
            else:
                embeddings = self._model.encode(texts, convert_to_numpy=True)
                return embeddings.astype(np.float32)
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise ClusteringError(f"Failed to generate embeddings: {e}")


class KeywordClusterer:
    """Clusters keywords using various algorithms."""
    
    def __init__(
        self,
        min_cluster_size: int = 3,
        min_samples: int = 2,
        cluster_selection_epsilon: float = 0.5,
        max_clusters: int = 50
    ) -> None:
        """Initialize clusterer.
        
        Args:
            min_cluster_size: Minimum size for HDBSCAN clusters
            min_samples: Minimum samples for HDBSCAN core points
            cluster_selection_epsilon: HDBSCAN cluster selection threshold
            max_clusters: Maximum number of clusters to create
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.max_clusters = max_clusters
        self.embedding_generator = EmbeddingGenerator()
        
    def _preprocess_keywords(self, keywords: List[str]) -> List[str]:
        """Preprocess keywords for clustering.
        
        Args:
            keywords: List of keyword strings
            
        Returns:
            Preprocessed keyword strings
        """
        processed = []
        for keyword in keywords:
            # Clean and normalize
            clean_keyword = re.sub(r'[^\w\s]', ' ', keyword.lower().strip())
            clean_keyword = re.sub(r'\s+', ' ', clean_keyword)
            processed.append(clean_keyword)
        
        return processed
    
    def _cluster_hdbscan(self, embeddings: np.ndarray) -> np.ndarray:
        """Cluster embeddings using HDBSCAN.
        
        Args:
            embeddings: Array of embeddings
            
        Returns:
            Array of cluster labels
        """
        try:
            import hdbscan
            
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=self.min_samples,
                cluster_selection_epsilon=self.cluster_selection_epsilon,
                metric='euclidean'
            )
            
            cluster_labels = clusterer.fit_predict(embeddings)
            return cluster_labels
            
        except ImportError:
            logger.warning("HDBSCAN not available, falling back to K-means")
            return self._cluster_kmeans(embeddings)
    
    def _cluster_kmeans(self, embeddings: np.ndarray) -> np.ndarray:
        """Cluster embeddings using K-means.
        
        Args:
            embeddings: Array of embeddings
            
        Returns:
            Array of cluster labels
        """
        try:
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
            
            n_samples = embeddings.shape[0]
            max_k = min(self.max_clusters, n_samples // 2)
            
            if max_k < 2:
                return np.zeros(n_samples, dtype=int)
            
            best_k = 2
            best_score = -1
            
            # Find optimal number of clusters using silhouette score
            for k in range(2, max_k + 1):
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(embeddings)
                
                if len(set(labels)) > 1:  # Need at least 2 clusters for silhouette score
                    score = silhouette_score(embeddings, labels)
                    if score > best_score:
                        best_score = score
                        best_k = k
            
            # Fit final model
            kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            return kmeans.fit_predict(embeddings)
            
        except ImportError:
            logger.warning("scikit-learn not available, falling back to agglomerative")
            return self._cluster_agglomerative(embeddings)
    
    def _cluster_agglomerative(self, embeddings: np.ndarray) -> np.ndarray:
        """Cluster embeddings using Agglomerative clustering.
        
        Args:
            embeddings: Array of embeddings
            
        Returns:
            Array of cluster labels
        """
        try:
            from sklearn.cluster import AgglomerativeClustering
            from sklearn.metrics import silhouette_score
            
            n_samples = embeddings.shape[0]
            max_k = min(self.max_clusters, n_samples // 2)
            
            if max_k < 2:
                return np.zeros(n_samples, dtype=int)
            
            best_k = 2
            best_score = -1
            
            # Find optimal number of clusters
            for k in range(2, max_k + 1):
                clustering = AgglomerativeClustering(
                    n_clusters=k,
                    linkage='ward'
                )
                labels = clustering.fit_predict(embeddings)
                
                if len(set(labels)) > 1:
                    score = silhouette_score(embeddings, labels)
                    if score > best_score:
                        best_score = score
                        best_k = k
            
            # Fit final model
            clustering = AgglomerativeClustering(
                n_clusters=best_k,
                linkage='ward'
            )
            return clustering.fit_predict(embeddings)
            
        except ImportError:
            logger.error("No clustering libraries available")
            raise ClusteringError("No clustering algorithms available")
    
    def cluster_keywords(
        self,
        keywords: List[str],
        method: str = "hdbscan"
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Cluster keywords and return labels and embeddings.
        
        Args:
            keywords: List of keyword strings to cluster
            method: Clustering method ('hdbscan', 'kmeans', 'agglomerative')
            
        Returns:
            Tuple of (cluster_labels, embeddings)
            
        Raises:
            ClusteringError: If clustering fails
        """
        if len(keywords) < 2:
            return np.zeros(len(keywords), dtype=int), np.array([])
        
        try:
            # Preprocess keywords
            processed_keywords = self._preprocess_keywords(keywords)
            
            # Generate embeddings
            embeddings = self.embedding_generator.generate_embeddings(processed_keywords)
            
            # Cluster based on method
            if method == "hdbscan":
                labels = self._cluster_hdbscan(embeddings)
            elif method == "kmeans":
                labels = self._cluster_kmeans(embeddings)
            elif method == "agglomerative":
                labels = self._cluster_agglomerative(embeddings)
            else:
                raise ClusteringError(f"Unknown clustering method: {method}")
            
            return labels, embeddings
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            logger.error(traceback.format_exc())
            raise ClusteringError(f"Keyword clustering failed: {e}")


class ClusterLabeler:
    """Generates labels for keyword clusters."""
    
    def __init__(self, min_ngram_freq: int = 2) -> None:
        """Initialize cluster labeler.
        
        Args:
            min_ngram_freq: Minimum frequency for n-gram to be considered
        """
        self.min_ngram_freq = min_ngram_freq
    
    def _extract_ngrams(self, text: str, n: int = 2) -> List[str]:
        """Extract n-grams from text.
        
        Args:
            text: Input text
            n: N-gram size
            
        Returns:
            List of n-grams
        """
        words = text.lower().split()
        if len(words) < n:
            return words
        
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i + n])
            ngrams.append(ngram)
        
        return ngrams
    
    def _get_stopwords(self) -> Set[str]:
        """Get English stopwords.
        
        Returns:
            Set of stopwords
        """
        try:
            import nltk
            from nltk.corpus import stopwords
            
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)
            
            return set(stopwords.words('english'))
        except ImportError:
            # Fallback stopwords
            return {
                'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                'to', 'was', 'were', 'will', 'with', 'how', 'what', 'when', 'where',
                'who', 'why', 'best', 'top', 'can', 'do', 'does', 'get', 'make'
            }
    
    def generate_cluster_labels(
        self,
        keywords_by_cluster: Dict[int, List[str]]
    ) -> Dict[int, str]:
        """Generate descriptive labels for clusters.
        
        Args:
            keywords_by_cluster: Dictionary mapping cluster IDs to keyword lists
            
        Returns:
            Dictionary mapping cluster IDs to generated labels
        """
        stopwords = self._get_stopwords()
        labels = {}
        
        for cluster_id, keywords in keywords_by_cluster.items():
            if cluster_id == -1:  # Noise cluster
                labels[cluster_id] = "Miscellaneous"
                continue
            
            if not keywords:
                labels[cluster_id] = f"Cluster {cluster_id}"
                continue
            
            # Collect all words and n-grams
            all_text = ' '.join(keywords)
            
            # Extract unigrams and bigrams
            unigrams = []
            bigrams = []
            
            for keyword in keywords:
                words = [w for w in keyword.lower().split() if w not in stopwords]
                unigrams.extend(words)
                bigrams.extend(self._extract_ngrams(keyword, 2))
            
            # Count frequencies
            unigram_counts = Counter(unigrams)
            bigram_counts = Counter(bigrams)
            
            # Find most common meaningful terms
            label_candidates = []
            
            # Add high-frequency bigrams
            for bigram, count in bigram_counts.most_common(5):
                if count >= self.min_ngram_freq:
                    # Filter out bigrams that are just stopwords
                    words = bigram.split()
                    if not all(word in stopwords for word in words):
                        label_candidates.append((bigram, count))
            
            # Add high-frequency unigrams if no good bigrams
            if not label_candidates:
                for unigram, count in unigram_counts.most_common(3):
                    if count >= self.min_ngram_freq and unigram not in stopwords:
                        label_candidates.append((unigram, count))
            
            # Generate label
            if label_candidates:
                # Use the most frequent meaningful term
                label = label_candidates[0][0].title()
                # Clean up the label
                label = re.sub(r'\s+', ' ', label).strip()
            else:
                # Fallback: use first keyword
                label = keywords[0].title()
            
            labels[cluster_id] = label
        
        return labels


class HubSpokeAnalyzer:
    """Identifies hub and spoke relationships in keyword clusters."""
    
    def __init__(self, hub_threshold: float = 0.7) -> None:
        """Initialize hub-spoke analyzer.
        
        Args:
            hub_threshold: Similarity threshold for hub identification
        """
        self.hub_threshold = hub_threshold
    
    def _calculate_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """Calculate cosine similarity matrix.
        
        Args:
            embeddings: Array of embeddings
            
        Returns:
            Similarity matrix
        """
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            return cosine_similarity(embeddings)
        except ImportError:
            # Manual cosine similarity calculation
            norm_embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            return np.dot(norm_embeddings, norm_embeddings.T)
    
    def _find_cluster_hub(
        self,
        keywords: List[str],
        embeddings: np.ndarray
    ) -> Tuple[str, List[str]]:
        """Find hub keyword and spokes for a cluster.
        
        Args:
            keywords: List of keywords in cluster
            embeddings: Embeddings for the keywords
            
        Returns:
            Tuple of (hub_keyword, spoke_keywords)
        """
        if len(keywords) <= 1:
            return keywords[0] if keywords else "", []
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(embeddings)
        
        # Find keyword with highest average similarity to others
        avg_similarities = []
        for i in range(len(keywords)):
            # Exclude self-similarity
            other_similarities = [
                similarity_matrix[i][j] for j in range(len(keywords)) if i != j
            ]
            avg_similarity = np.mean(other_similarities) if other_similarities else 0
            avg_similarities.append(avg_similarity)
        
        # Hub is the keyword with highest average similarity
        hub_idx = np.argmax(avg_similarities)
        hub_keyword = keywords[hub_idx]
        
        # Spokes are other keywords with similarity above threshold
        spoke_keywords = []
        for i, keyword in enumerate(keywords):
            if i != hub_idx and similarity_matrix[hub_idx][i] >= self.hub_threshold:
                spoke_keywords.append(keyword)
        
        return hub_keyword, spoke_keywords
    
    def analyze_hub_spoke_relationships(
        self,
        keywords_by_cluster: Dict[int, List[str]],
        embeddings_by_cluster: Dict[int, np.ndarray]
    ) -> Dict[int, Dict[str, Union[str, List[str]]]]:
        """Analyze hub-spoke relationships for all clusters.
        
        Args:
            keywords_by_cluster: Keywords grouped by cluster
            embeddings_by_cluster: Embeddings grouped by cluster
            
        Returns:
            Dictionary with hub-spoke analysis for each cluster
        """
        relationships = {}
        
        for cluster_id, keywords in keywords_by_cluster.items():
            if cluster_id == -1:  # Skip noise cluster
                continue
            
            embeddings = embeddings_by_cluster.get(cluster_id, np.array([]))
            if embeddings.size == 0:
                continue
            
            hub, spokes = self._find_cluster_hub(keywords, embeddings)
            
            relationships[cluster_id] = {
                'hub_keyword': hub,
                'spoke_keywords': spokes,
                'total_keywords': len(keywords),
                'hub_coverage': len(spokes) / max(len(keywords) - 1, 1)
            }
        
        return relationships


class SemanticRelationshipMapper:
    """Maps semantic relationships between keywords and clusters."""
    
    def __init__(self, similarity_threshold: float = 0.6):
        """Initialize semantic relationship mapper.
        
        Args:
            similarity_threshold: Minimum similarity for relationship detection
        """
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _calculate_semantic_distance(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate semantic distance between two embeddings."""
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embedding1], [embedding2])[0][0]
            return 1.0 - similarity  # Convert similarity to distance
        except ImportError:
            # Manual calculation
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            if norm1 == 0 or norm2 == 0:
                return 1.0
            
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return 1.0 - similarity
    
    def _classify_relationship_type(self, keyword1: str, keyword2: str, distance: float) -> Optional[str]:
        """Classify the type of relationship between two keywords."""
        kw1_lower = keyword1.lower()
        kw2_lower = keyword2.lower()
        
        # Exact substring relationships
        if kw1_lower in kw2_lower or kw2_lower in kw1_lower:
            return "hierarchical"
        
        # Similar word patterns
        kw1_words = set(kw1_lower.split())
        kw2_words = set(kw2_lower.split())
        
        overlap = len(kw1_words.intersection(kw2_words))
        total_unique = len(kw1_words.union(kw2_words))
        
        if overlap > 0:
            word_similarity = overlap / total_unique
            if word_similarity > 0.5:
                return "synonymous" if word_similarity > 0.8 else "related"
        
        # Semantic similarity from embedding distance
        if distance < 0.2:
            return "synonymous"
        elif distance < 0.4:
            return "related"
        elif distance < 0.6:
            return "topically_related"
        
        return None
    
    def map_keyword_relationships(
        self,
        keywords: List[str],
        embeddings: np.ndarray,
        cluster_assignments: Dict[str, int]
    ) -> Dict[str, List[Dict]]:
        """Map semantic relationships between keywords.
        
        Args:
            keywords: List of keywords
            embeddings: Keyword embeddings
            cluster_assignments: Cluster assignments for keywords
            
        Returns:
            Dictionary mapping keywords to their relationships
        """
        relationships = defaultdict(list)
        
        for i, keyword1 in enumerate(keywords):
            for j, keyword2 in enumerate(keywords[i+1:], i+1):
                distance = self._calculate_semantic_distance(embeddings[i], embeddings[j])
                
                if distance <= (1.0 - self.similarity_threshold):
                    relationship_type = self._classify_relationship_type(keyword1, keyword2, distance)
                    
                    if relationship_type:
                        # Determine relationship strength
                        strength = max(0.0, 1.0 - distance)
                        
                        # Check if keywords are in same cluster
                        same_cluster = (cluster_assignments.get(keyword1) == 
                                      cluster_assignments.get(keyword2))
                        
                        relationship = {
                            'target_keyword': keyword2,
                            'relationship_type': relationship_type,
                            'strength': strength,
                            'semantic_distance': distance,
                            'same_cluster': same_cluster,
                            'cluster_source': cluster_assignments.get(keyword1),
                            'cluster_target': cluster_assignments.get(keyword2)
                        }
                        
                        relationships[keyword1].append(relationship)
                        
                        # Add reverse relationship
                        reverse_relationship = relationship.copy()
                        reverse_relationship['target_keyword'] = keyword1
                        reverse_relationship['cluster_source'] = cluster_assignments.get(keyword2)
                        reverse_relationship['cluster_target'] = cluster_assignments.get(keyword1)
                        relationships[keyword2].append(reverse_relationship)
        
        return dict(relationships)
    
    def build_cluster_relationship_graph(
        self,
        clustering_results: Dict[str, Any],
        keyword_relationships: Dict[str, List[Dict]]
    ) -> Dict[int, Dict]:
        """Build relationships between clusters based on keyword relationships.
        
        Args:
            clustering_results: Results from keyword clustering
            keyword_relationships: Mapped keyword relationships
            
        Returns:
            Dictionary mapping cluster IDs to their relationships
        """
        cluster_relationships = defaultdict(lambda: defaultdict(list))
        
        # Aggregate relationships between clusters
        for keyword, relationships in keyword_relationships.items():
            source_cluster = clustering_results['cluster_assignments'].get(keyword)
            
            if source_cluster is not None:
                for rel in relationships:
                    target_cluster = rel['cluster_target']
                    
                    if target_cluster is not None and source_cluster != target_cluster:
                        cluster_relationships[source_cluster][target_cluster].append(rel)
        
        # Summarize cluster relationships
        cluster_summary = {}
        for source_cluster, targets in cluster_relationships.items():
            cluster_summary[source_cluster] = {}
            
            for target_cluster, relationships in targets.items():
                # Calculate average strength and most common relationship type
                strengths = [rel['strength'] for rel in relationships]
                types = [rel['relationship_type'] for rel in relationships]
                
                avg_strength = statistics.mean(strengths) if strengths else 0.0
                most_common_type = Counter(types).most_common(1)[0][0] if types else 'unknown'
                
                cluster_summary[source_cluster][target_cluster] = {
                    'relationship_type': most_common_type,
                    'average_strength': avg_strength,
                    'connection_count': len(relationships),
                    'sample_keywords': [rel['target_keyword'] for rel in relationships[:3]]
                }
        
        return cluster_summary


class TopicHierarchyBuilder:
    """Builds hierarchical topic structures from keyword clusters."""
    
    def __init__(self):
        """Initialize topic hierarchy builder."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _calculate_cluster_generality_score(self, cluster_keywords: List[str]) -> float:
        """Calculate how general/broad a cluster is based on its keywords."""
        # More keywords = potentially more general
        keyword_count_score = min(1.0, len(cluster_keywords) / 20.0)
        
        # Shorter average keyword length = potentially more general
        avg_keyword_length = statistics.mean(len(kw.split()) for kw in cluster_keywords)
        length_score = max(0.0, 1.0 - (avg_keyword_length - 1.0) / 4.0)
        
        # Presence of broad terms
        broad_terms = {'guide', 'tips', 'best', 'how to', 'what is', 'overview', 'basics'}
        broad_term_score = 0.0
        for keyword in cluster_keywords:
            if any(term in keyword.lower() for term in broad_terms):
                broad_term_score += 0.2
        
        broad_term_score = min(1.0, broad_term_score)
        
        # Combine scores
        generality_score = (keyword_count_score * 0.4 + 
                          length_score * 0.4 + 
                          broad_term_score * 0.2)
        
        return generality_score
    
    def _identify_parent_child_relationships(
        self,
        clusters: Dict[int, List[str]],
        cluster_relationships: Dict[int, Dict],
        cluster_labels: Dict[int, str]
    ) -> Dict[int, Dict]:
        """Identify parent-child relationships between clusters."""
        hierarchy = {}
        
        # Calculate generality scores for all clusters
        generality_scores = {}
        for cluster_id, keywords in clusters.items():
            generality_scores[cluster_id] = self._calculate_cluster_generality_score(keywords)
        
        # For each cluster, find potential parents and children
        for cluster_id, keywords in clusters.items():
            cluster_info = {
                'cluster_id': cluster_id,
                'label': cluster_labels.get(cluster_id, f'Cluster {cluster_id}'),
                'generality_score': generality_scores[cluster_id],
                'keyword_count': len(keywords),
                'potential_parents': [],
                'potential_children': [],
                'siblings': []
            }
            
            # Check relationships with other clusters
            if cluster_id in cluster_relationships:
                for related_cluster_id, relationship_info in cluster_relationships[cluster_id].items():
                    related_generality = generality_scores.get(related_cluster_id, 0.0)
                    
                    # Parent relationship: more general cluster with hierarchical relationship
                    if (related_generality > generality_scores[cluster_id] + 0.1 and
                        relationship_info['relationship_type'] in ['hierarchical', 'related'] and
                        relationship_info['average_strength'] > 0.6):
                        
                        cluster_info['potential_parents'].append({
                            'cluster_id': related_cluster_id,
                            'label': cluster_labels.get(related_cluster_id, f'Cluster {related_cluster_id}'),
                            'strength': relationship_info['average_strength'],
                            'generality_difference': related_generality - generality_scores[cluster_id]
                        })
                    
                    # Child relationship: less general cluster
                    elif (related_generality < generality_scores[cluster_id] - 0.1 and
                          relationship_info['relationship_type'] in ['hierarchical', 'related'] and
                          relationship_info['average_strength'] > 0.6):
                        
                        cluster_info['potential_children'].append({
                            'cluster_id': related_cluster_id,
                            'label': cluster_labels.get(related_cluster_id, f'Cluster {related_cluster_id}'),
                            'strength': relationship_info['average_strength'],
                            'generality_difference': generality_scores[cluster_id] - related_generality
                        })
                    
                    # Sibling relationship: similar generality
                    elif (abs(related_generality - generality_scores[cluster_id]) <= 0.1 and
                          relationship_info['relationship_type'] in ['related', 'synonymous'] and
                          relationship_info['average_strength'] > 0.5):
                        
                        cluster_info['siblings'].append({
                            'cluster_id': related_cluster_id,
                            'label': cluster_labels.get(related_cluster_id, f'Cluster {related_cluster_id}'),
                            'strength': relationship_info['average_strength']
                        })
            
            # Sort by strength
            cluster_info['potential_parents'].sort(key=lambda x: x['strength'], reverse=True)
            cluster_info['potential_children'].sort(key=lambda x: x['strength'], reverse=True)
            cluster_info['siblings'].sort(key=lambda x: x['strength'], reverse=True)
            
            hierarchy[cluster_id] = cluster_info
        
        return hierarchy
    
    def build_topic_hierarchy(
        self,
        clustering_results: Dict[str, Any],
        cluster_relationships: Dict[int, Dict]
    ) -> Dict[str, Any]:
        """Build complete topic hierarchy from clustering results.
        
        Args:
            clustering_results: Results from keyword clustering
            cluster_relationships: Relationships between clusters
            
        Returns:
            Dictionary containing the topic hierarchy
        """
        clusters = clustering_results['clusters']
        cluster_labels = clustering_results['labels']
        
        # Identify hierarchical relationships
        hierarchy = self._identify_parent_child_relationships(
            clusters, cluster_relationships, cluster_labels
        )
        
        # Build tree structure
        root_clusters = []  # Clusters with no parents
        tree_structure = {}
        
        for cluster_id, cluster_info in hierarchy.items():
            if not cluster_info['potential_parents']:
                root_clusters.append(cluster_id)
            
            tree_structure[cluster_id] = {
                'label': cluster_info['label'],
                'generality_score': cluster_info['generality_score'],
                'keyword_count': cluster_info['keyword_count'],
                'children': [child['cluster_id'] for child in cluster_info['potential_children']],
                'parent': cluster_info['potential_parents'][0]['cluster_id'] if cluster_info['potential_parents'] else None,
                'level': 0  # Will be calculated
            }
        
        # Calculate hierarchy levels
        def calculate_level(cluster_id, visited=None):
            if visited is None:
                visited = set()
            
            if cluster_id in visited:
                return 0  # Avoid cycles
            
            visited.add(cluster_id)
            parent_id = tree_structure[cluster_id]['parent']
            
            if parent_id is None:
                level = 0
            else:
                level = calculate_level(parent_id, visited) + 1
            
            tree_structure[cluster_id]['level'] = level
            visited.remove(cluster_id)
            return level
        
        for cluster_id in tree_structure:
            calculate_level(cluster_id)
        
        return {
            'hierarchy': hierarchy,
            'tree_structure': tree_structure,
            'root_clusters': root_clusters,
            'max_depth': max(info['level'] for info in tree_structure.values()) if tree_structure else 0,
            'total_clusters': len(hierarchy)
        }


class StatisticalValidator:
    """Validates clustering results using statistical methods."""
    
    def __init__(self):
        """Initialize statistical validator."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_silhouette_score(self, embeddings: np.ndarray, cluster_labels: np.ndarray) -> float:
        """Calculate silhouette score for clustering quality."""
        try:
            from sklearn.metrics import silhouette_score
            if len(set(cluster_labels)) < 2:
                return 0.0
            return silhouette_score(embeddings, cluster_labels)
        except ImportError:
            return self._manual_silhouette_score(embeddings, cluster_labels)
    
    def _manual_silhouette_score(self, embeddings: np.ndarray, cluster_labels: np.ndarray) -> float:
        """Manual silhouette score calculation."""
        if len(set(cluster_labels)) < 2:
            return 0.0
        
        scores = []
        for i, point in enumerate(embeddings):
            # Calculate intra-cluster distance (a)
            same_cluster_points = embeddings[cluster_labels == cluster_labels[i]]
            if len(same_cluster_points) > 1:
                a = np.mean([np.linalg.norm(point - other) for other in same_cluster_points if not np.array_equal(point, other)])
            else:
                a = 0
            
            # Calculate nearest-cluster distance (b)
            b = float('inf')
            for cluster_id in set(cluster_labels):
                if cluster_id != cluster_labels[i]:
                    other_cluster_points = embeddings[cluster_labels == cluster_id]
                    avg_distance = np.mean([np.linalg.norm(point - other) for other in other_cluster_points])
                    b = min(b, avg_distance)
            
            if b == float('inf'):
                b = 0
            
            # Silhouette coefficient
            if max(a, b) > 0:
                scores.append((b - a) / max(a, b))
            else:
                scores.append(0)
        
        return np.mean(scores) if scores else 0.0
    
    def calculate_inertia(self, embeddings: np.ndarray, cluster_labels: np.ndarray) -> float:
        """Calculate within-cluster sum of squares (inertia)."""
        inertia = 0.0
        
        for cluster_id in set(cluster_labels):
            cluster_points = embeddings[cluster_labels == cluster_id]
            if len(cluster_points) > 0:
                centroid = np.mean(cluster_points, axis=0)
                cluster_inertia = np.sum([np.linalg.norm(point - centroid) ** 2 for point in cluster_points])
                inertia += cluster_inertia
        
        return inertia
    
    def calculate_cluster_stability(
        self,
        keywords: List[str],
        embeddings: np.ndarray,
        cluster_labels: np.ndarray,
        n_iterations: int = 5
    ) -> Dict[int, float]:
        """Calculate stability of each cluster through bootstrap sampling."""
        cluster_stability = {}
        unique_clusters = set(cluster_labels)
        
        for cluster_id in unique_clusters:
            if cluster_id == -1:  # Skip noise cluster
                continue
            
            cluster_indices = np.where(cluster_labels == cluster_id)[0]
            if len(cluster_indices) < 3:
                cluster_stability[cluster_id] = 0.0
                continue
            
            stability_scores = []
            
            for _ in range(n_iterations):
                # Bootstrap sample
                sample_size = max(2, len(cluster_indices) // 2)
                sample_indices = np.random.choice(cluster_indices, size=sample_size, replace=True)
                
                # Calculate pairwise similarities within sample
                sample_embeddings = embeddings[sample_indices]
                similarities = []
                
                for i in range(len(sample_embeddings)):
                    for j in range(i + 1, len(sample_embeddings)):
                        similarity = np.dot(sample_embeddings[i], sample_embeddings[j]) / (
                            np.linalg.norm(sample_embeddings[i]) * np.linalg.norm(sample_embeddings[j])
                        )
                        similarities.append(similarity)
                
                if similarities:
                    stability_scores.append(np.mean(similarities))
            
            cluster_stability[cluster_id] = np.mean(stability_scores) if stability_scores else 0.0
        
        return cluster_stability
    
    def validate_clustering_results(
        self,
        keywords: List[str],
        embeddings: np.ndarray,
        clustering_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive statistical validation of clustering results.
        
        Args:
            keywords: Original keywords
            embeddings: Keyword embeddings
            clustering_results: Clustering results to validate
            
        Returns:
            Dictionary containing validation metrics
        """
        cluster_labels = np.array([
            clustering_results['cluster_assignments'].get(kw, -1) for kw in keywords
        ])
        
        # Calculate quality metrics
        silhouette = self.calculate_silhouette_score(embeddings, cluster_labels)
        inertia = self.calculate_inertia(embeddings, cluster_labels)
        stability = self.calculate_cluster_stability(keywords, embeddings, cluster_labels)
        
        # Calculate cluster-specific metrics
        cluster_metrics = {}
        for cluster_id, cluster_keywords in clustering_results['clusters'].items():
            cluster_indices = [i for i, kw in enumerate(keywords) if kw in cluster_keywords]
            cluster_embeddings = embeddings[cluster_indices]
            
            if len(cluster_embeddings) > 1:
                # Intra-cluster similarity
                similarities = []
                for i in range(len(cluster_embeddings)):
                    for j in range(i + 1, len(cluster_embeddings)):
                        sim = np.dot(cluster_embeddings[i], cluster_embeddings[j]) / (
                            np.linalg.norm(cluster_embeddings[i]) * np.linalg.norm(cluster_embeddings[j])
                        )
                        similarities.append(sim)
                
                avg_similarity = np.mean(similarities) if similarities else 0.0
                similarity_std = np.std(similarities) if similarities else 0.0
                
                cluster_metrics[cluster_id] = {
                    'size': len(cluster_keywords),
                    'avg_intra_similarity': avg_similarity,
                    'similarity_std': similarity_std,
                    'stability_score': stability.get(cluster_id, 0.0),
                    'quality_score': avg_similarity * (1 - similarity_std)  # Higher similarity, lower variance = better
                }
        
        # Overall validation score
        valid_clusters = len([c for c in cluster_metrics.values() if c['quality_score'] > 0.5])
        total_clusters = len(cluster_metrics)
        validation_score = (silhouette * 0.4 + 
                          (valid_clusters / max(total_clusters, 1)) * 0.4 + 
                          np.mean(list(stability.values())) * 0.2 if stability else 0.0)
        
        return {
            'silhouette_score': silhouette,
            'inertia': inertia,
            'cluster_stability': stability,
            'cluster_metrics': cluster_metrics,
            'validation_score': validation_score,
            'quality_assessment': self._assess_quality(validation_score),
            'recommendations': self._generate_recommendations(validation_score, cluster_metrics)
        }
    
    def _assess_quality(self, validation_score: float) -> str:
        """Assess overall clustering quality."""
        if validation_score >= 0.8:
            return "excellent"
        elif validation_score >= 0.6:
            return "good"
        elif validation_score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def _generate_recommendations(self, validation_score: float, cluster_metrics: Dict) -> List[str]:
        """Generate recommendations for improving clustering."""
        recommendations = []
        
        if validation_score < 0.6:
            recommendations.append("Consider adjusting clustering parameters for better separation")
        
        poor_clusters = [cid for cid, metrics in cluster_metrics.items() 
                        if metrics['quality_score'] < 0.4]
        
        if poor_clusters:
            recommendations.append(f"Review clusters {poor_clusters} - they may need refinement")
        
        small_clusters = [cid for cid, metrics in cluster_metrics.items() 
                         if metrics['size'] < 3]
        
        if len(small_clusters) > len(cluster_metrics) * 0.3:
            recommendations.append("Too many small clusters - consider merging similar ones")
        
        return recommendations


class KeywordClusterManager:
    """Main manager for keyword clustering operations."""
    
    def __init__(
        self,
        min_cluster_size: int = 3,
        min_samples: int = 2,
        cluster_selection_epsilon: float = 0.5,
        max_clusters: int = 50
    ) -> None:
        """Initialize cluster manager.
        
        Args:
            min_cluster_size: Minimum size for clusters
            min_samples: Minimum samples for core points
            cluster_selection_epsilon: Cluster selection threshold
            max_clusters: Maximum number of clusters
        """
        self.clusterer = KeywordClusterer(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            cluster_selection_epsilon=cluster_selection_epsilon,
            max_clusters=max_clusters
        )
        self.labeler = ClusterLabeler()
        self.hub_spoke_analyzer = HubSpokeAnalyzer()
        self.relationship_mapper = SemanticRelationshipMapper()
        self.hierarchy_builder = TopicHierarchyBuilder()
        self.validator = StatisticalValidator()
    
    def cluster_keywords(
        self,
        keywords: List[str],
        method: str = "hdbscan"
    ) -> Dict[str, Any]:
        """Perform complete keyword clustering analysis.
        
        Args:
            keywords: List of keyword strings
            method: Clustering method to use
            
        Returns:
            Dictionary containing clustering results
            
        Raises:
            ClusteringError: If clustering fails
        """
        if not keywords:
            return {
                'clusters': {},
                'labels': {},
                'hub_spoke_relationships': {},
                'embeddings': np.array([]),
                'total_clusters': 0,
                'noise_keywords': []
            }
        
        try:
            # Perform clustering
            cluster_labels, embeddings = self.clusterer.cluster_keywords(keywords, method)
            
            # Group keywords by cluster
            keywords_by_cluster = defaultdict(list)
            embeddings_by_cluster = defaultdict(list)
            
            for i, (keyword, label) in enumerate(zip(keywords, cluster_labels)):
                keywords_by_cluster[int(label)].append(keyword)
                embeddings_by_cluster[int(label)].append(embeddings[i])
            
            # Convert embedding lists to arrays
            embeddings_by_cluster = {
                cluster_id: np.array(emb_list)
                for cluster_id, emb_list in embeddings_by_cluster.items()
            }
            
            # Generate cluster labels
            cluster_names = self.labeler.generate_cluster_labels(dict(keywords_by_cluster))
            
            # Analyze hub-spoke relationships
            hub_spoke_relationships = self.hub_spoke_analyzer.analyze_hub_spoke_relationships(
                dict(keywords_by_cluster), embeddings_by_cluster
            )
            
            # Map semantic relationships between keywords
            cluster_assignments = dict(zip(keywords, cluster_labels))
            keyword_relationships = self.relationship_mapper.map_keyword_relationships(
                keywords, embeddings, cluster_assignments
            )
            
            # Build cluster relationship graph
            cluster_relationships = self.relationship_mapper.build_cluster_relationship_graph(
                {'cluster_assignments': cluster_assignments}, keyword_relationships
            )
            
            # Build topic hierarchy
            topic_hierarchy = self.hierarchy_builder.build_topic_hierarchy(
                {'clusters': dict(keywords_by_cluster), 'labels': cluster_names}, 
                cluster_relationships
            )
            
            # Validate clustering results
            validation_results = self.validator.validate_clustering_results(
                keywords, embeddings, {'clusters': dict(keywords_by_cluster), 'cluster_assignments': cluster_assignments}
            )
            
            # Identify noise keywords
            noise_keywords = keywords_by_cluster.get(-1, [])
            if -1 in keywords_by_cluster:
                del keywords_by_cluster[-1]
            
            return {
                'clusters': dict(keywords_by_cluster),
                'labels': cluster_names,
                'hub_spoke_relationships': hub_spoke_relationships,
                'keyword_relationships': keyword_relationships,
                'cluster_relationships': cluster_relationships,
                'topic_hierarchy': topic_hierarchy,
                'validation_results': validation_results,
                'embeddings': embeddings,
                'total_clusters': len(keywords_by_cluster),
                'noise_keywords': noise_keywords,
                'cluster_assignments': cluster_assignments
            }
            
        except Exception as e:
            logger.error(f"Keyword clustering failed: {e}")
            logger.error(traceback.format_exc())
            raise ClusteringError(f"Clustering analysis failed: {e}")
    
    def update_database_clusters(
        self,
        db: Session,
        project_id: str,
        clustering_results: Dict[str, Any]
    ) -> List[Cluster]:
        """Update database with clustering results.
        
        Args:
            db: Database session
            project_id: Project ID
            clustering_results: Results from cluster_keywords
            
        Returns:
            List of created/updated cluster objects
        """
        created_clusters = []
        
        try:
            # Create clusters for each cluster group
            for cluster_id, keywords in clustering_results['clusters'].items():
                if not keywords:
                    continue
                
                cluster_name = clustering_results['labels'].get(cluster_id, f"Cluster {cluster_id}")
                
                # Create cluster slug
                cluster_slug = re.sub(r'[^\w\s-]', '', cluster_name.lower())
                cluster_slug = re.sub(r'[-\s]+', '-', cluster_slug).strip('-')
                
                # Check if cluster already exists
                existing_cluster = db.query(Cluster).filter_by(
                    project_id=project_id,
                    slug=cluster_slug
                ).first()
                
                if existing_cluster:
                    cluster = existing_cluster
                else:
                    # Create new cluster
                    cluster = Cluster(
                        project_id=project_id,
                        name=cluster_name,
                        slug=cluster_slug,
                        cluster_type="hub"  # Will be updated based on hub-spoke analysis
                    )
                    db.add(cluster)
                    db.flush()  # Get the ID
                
                # Update cluster with analysis results
                hub_spoke_info = clustering_results['hub_spoke_relationships'].get(cluster_id, {})
                
                if hub_spoke_info:
                    cluster.entities = [hub_spoke_info.get('hub_keyword', '')]
                    
                    # Determine if this is a hub or spoke cluster
                    hub_coverage = hub_spoke_info.get('hub_coverage', 0)
                    cluster.cluster_type = "hub" if hub_coverage > 0.5 else "spoke"
                
                # Update keywords to belong to this cluster
                for keyword_text in keywords:
                    keyword = db.query(Keyword).filter_by(
                        project_id=project_id,
                        query=keyword_text
                    ).first()
                    
                    if keyword:
                        keyword.cluster = cluster
                
                created_clusters.append(cluster)
            
            db.commit()
            logger.info(f"Created/updated {len(created_clusters)} clusters for project {project_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update database clusters: {e}")
            raise ClusteringError(f"Database update failed: {e}")
        
        return created_clusters


# Factory function for easy usage
def create_cluster_manager(**kwargs) -> KeywordClusterManager:
    """Create a keyword cluster manager with custom settings.
    
    Args:
        **kwargs: Configuration parameters for clustering
        
    Returns:
        Configured KeywordClusterManager instance
    """
    return KeywordClusterManager(**kwargs)