"""
Improved categorization service with hybrid approach.
Combines semantic similarity with keyword-based hints for better accuracy.
"""

import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity

from models import Category
from core.embedding_service import get_embedding_service
from core.database_service import get_database_service
from utils import get_logger, TextProcessor
from config import get_settings

logger = get_logger(__name__)


class CategorizationService:
    """
    Improved categorization with hybrid approach.
    Combines semantic embeddings with keyword-based hints.
    """
    
    # Keyword patterns for BROAD category detection
    CATEGORY_KEYWORDS = {
        'Academic Work': [
            'assignment', 'homework', 'due', 'problem set', 'exercises',
            'hw', 'pset', 'quiz', 'test prep', 'project', 'essay', 'paper',
            'submission', 'deadline', 'coursework', 'assessment'
        ],
        'Course Materials': [
            'lecture', 'notes', 'chapter', 'slides', 'presentation',
            'class notes', 'course notes', 'week', 'textbook', 'reading',
            'syllabus', 'handout', 'material', 'content'
        ],
        'Research & Papers': [
            'research', 'paper', 'study', 'journal', 'publication',
            'thesis', 'dissertation', 'article', 'review', 'analysis',
            'findings', 'methodology', 'conclusion', 'abstract'
        ],
        'Science & Tech': [
            'programming', 'algorithm', 'data structure', 'software',
            'code', 'python', 'java', 'c++', 'computer', 'cs', 'coding',
            'engineering', 'physics', 'chemistry', 'biology', 'lab',
            'experiment', 'laboratory', 'scientific', 'technical'
        ],
        'Mathematics': [
            'math', 'calculus', 'algebra', 'geometry', 'equation',
            'theorem', 'proof', 'statistics', 'probability', 'formula',
            'calculation', 'numerical', 'mathematical'
        ],
        'Business & Finance': [
            'business', 'finance', 'economics', 'management', 'marketing',
            'accounting', 'investment', 'budget', 'financial', 'corporate',
            'strategy', 'planning', 'analysis'
        ],
        'Language & Arts': [
            'literature', 'writing', 'language', 'english', 'art', 'design',
            'creative', 'poetry', 'novel', 'story', 'essay', 'composition',
            'grammar', 'linguistics', 'humanities'
        ],
        'Health & Medicine': [
            'medical', 'health', 'anatomy', 'physiology', 'medicine',
            'clinical', 'patient', 'diagnosis', 'treatment', 'therapy',
            'nursing', 'pharmacy', 'healthcare'
        ],
        'Social Sciences': [
            'psychology', 'sociology', 'history', 'politics', 'philosophy',
            'anthropology', 'geography', 'social', 'cultural', 'behavioral',
            'human', 'society', 'community'
        ],
    }
    
    # Subject keywords
    SUBJECT_KEYWORDS = {
        'Computer Science': [
            'programming', 'algorithm', 'data structure', 'software',
            'code', 'python', 'java', 'c++', 'computer', 'cs', 'coding'
        ],
        'Mathematics': [
            'math', 'calculus', 'algebra', 'geometry', 'equation',
            'theorem', 'proof', 'statistics', 'probability'
        ],
        'Biology': [
            'biology', 'bio', 'cell', 'organism', 'dna', 'genetics',
            'evolution', 'ecology', 'anatomy'
        ],
        'Chemistry': [
            'chemistry', 'chem', 'molecule', 'reaction', 'compound',
            'element', 'organic', 'inorganic', 'chemical'
        ],
        'Physics': [
            'physics', 'force', 'energy', 'motion', 'quantum',
            'mechanics', 'thermodynamics', 'electromagnetic'
        ],
    }
    
    def __init__(
        self,
        similarity_threshold: Optional[float] = None,
        max_categories: Optional[int] = None
    ):
        """Initialize improved categorization service."""
        settings = get_settings()
        
        self.similarity_threshold = similarity_threshold or settings.similarity_threshold
        self.max_categories = max_categories or settings.max_categories
        self.standard_categories = settings.standard_categories
        
        self.embedding_service = get_embedding_service()
        self.db_service = get_database_service()
        
        logger.info(
            f"CategorizationService initialized "
            f"(threshold={self.similarity_threshold}, max={self.max_categories})"
        )
    
    def initialize_standard_categories(self, user_id: str) -> List[int]:
        """
        Initialize standard categories for a new user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of created category IDs
        """
        try:
            existing_categories = self.db_service.get_categories_by_user(user_id)
            
            if existing_categories:
                logger.info(f"User {user_id} already has {len(existing_categories)} categories")
                return [cat['id'] for cat in existing_categories]
            
            category_ids = []
            
            # Create each standard category
            for category_name in self.standard_categories:
                # Start with zero centroid (will be updated with first document)
                zero_centroid = np.zeros(self.embedding_service.get_dimension())
                
                category_id = self.db_service.insert_category(
                    label=category_name,
                    centroid=zero_centroid,
                    user_id=user_id
                )
                
                category_ids.append(category_id)
                logger.info(f"Created standard category: {category_name} (ID: {category_id})")
            
            logger.info(f"Initialized {len(category_ids)} standard categories for user {user_id}")
            return category_ids
        
        except Exception as e:
            logger.error(f"Failed to initialize categories: {e}")
            return []
    
    def detect_category_from_keywords(
        self,
        content: str,
        filename: str
    ) -> List[str]:
        """
        Detect likely categories based on keywords in content and filename.
        Uses semantic-aware keyword detection to avoid company names.
        
        Args:
            content: Document content
            filename: Document filename
        
        Returns:
            List of suggested category names (prioritized)
        """
        text = (filename + " " + content[:1000]).lower()
        suggestions = []
        
        # Check category type keywords (more semantic)
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                suggestions.append(category)
        
        # Check subject keywords (more semantic)
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                suggestions.append(subject)
        
        # Special handling for cover letters and job applications
        if any(word in text for word in ['cover letter', 'application', 'resume', 'cv', 'job', 'position', 'hiring', 'employment', 'career']):
            suggestions.append('Professional Documents')  # Professional documents
        
        # Default fallback
        if not suggestions:
            suggestions.append('General Documents')
        
        return suggestions
    
    def categorize_document_hybrid(
        self,
        document_id: str,
        user_id: str,
        aggregated_embedding: np.ndarray,
        content: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Enhanced hybrid categorization with multi-pass analysis and confidence scoring.
        
        Args:
            document_id: Document ID
            user_id: User ID
            aggregated_embedding: Document embedding
            content: Document content (for keyword extraction)
            filename: Document filename (for keyword hints)
        
        Returns:
            Categorization result with confidence scoring
        """
        try:
            logger.info(f"Hybrid categorizing document {document_id}")
            
            # Get existing categories
            existing_categories = self.db_service.get_categories_by_user(user_id)
            
            if not existing_categories:
                # Create a general category if none exist
                general_cat_id = self.db_service.get_or_create_general_category(user_id)
                if general_cat_id:
                    # Update document
                    self.db_service.update_document(document_id, cluster_id=general_cat_id)
                    
                    return {
                        'success': True,
                        'category_id': general_cat_id,
                        'category_name': 'General Documents',
                        'is_new': True,
                        'similarity': 1.0,
                        'keyword_match': False,
                        'default': True
                    }
            
            # Simple keyword analysis
            suggested_categories = self._analyze_keywords(content, filename)
            logger.info(f"Keyword suggestions: {suggested_categories}")
            
            # Find best semantic match
            best_match = None
            best_similarity = 0.0
            
            for category in existing_categories:
                if category.get('centroid'):
                    try:
                        # Convert centroid to numpy array
                        centroid_array = np.array(category['centroid'], dtype=np.float32)
                        
                        # Calculate cosine similarity
                        similarity = self._calculate_cosine_similarity(aggregated_embedding, centroid_array)
                        
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_match = {
                                'category_id': category['id'],
                                'category': category,
                                'similarity': similarity
                            }
                    except Exception as e:
                        logger.warning(f"Error calculating similarity for category {category['id']}: {e}")
                        continue
            
            # Use simple threshold
            dynamic_threshold = self.similarity_threshold
            
            if best_match and best_match['similarity'] >= dynamic_threshold:
                category_id = best_match['category_id']
                category = best_match['category']
                
                # Update document
                self.db_service.update_document(document_id, cluster_id=category_id)
                
                # Update centroid
                self.db_service.update_category_centroid(category_id, aggregated_embedding.tolist())
                
                logger.info(
                    f"✓ Assigned to '{category['label']}' "
                    f"(similarity: {best_match['similarity']:.3f}, "
                    f"threshold: {dynamic_threshold:.3f})"
                )
                
                return {
                    'success': True,
                    'category_id': category_id,
                    'category_name': category['label'],
                    'is_new': False,
                    'similarity': best_match['similarity'],
                    'keyword_match': category['label'] in suggested_categories,
                    'method': 'semantic'
                }
            
            # Step 5: Use best semantic match even if below threshold (no keyword fallback)
            elif best_match:
                category_id = best_match['category_id']
                category = best_match['category']
                
                self.db_service.update_document(document_id, cluster_id=category_id)
                self.db_service.update_category_centroid(category_id, aggregated_embedding.tolist())
                
                logger.info(
                    f"✓ Assigned to '{category['label']}' via semantic match "
                    f"(similarity: {best_match['similarity']:.3f}, below threshold)"
                )
                
                return {
                    'success': True,
                    'category_id': category_id,
                    'category_name': category['label'],
                    'is_new': False,
                    'similarity': best_match['similarity'],
                    'keyword_match': False,
                    'semantic_match': True
                }
            
            # Step 6: Assign to General Documents as last resort
            general_cat = next(
                (cat for cat in existing_categories if cat['label'] == 'General Documents'),
                None
            )
            
            if general_cat:
                self.db_service.update_document(document_id, cluster_id=general_cat['id'])
                
                logger.info(f"✓ Assigned to 'General Documents' (no clear match)")
                
                return {
                    'success': True,
                    'category_id': general_cat['id'],
                    'category_name': 'General Documents',
                    'is_new': False,
                    'similarity': 0.0,
                    'keyword_match': False,
                    'default': True
                }
            
            # Step 7: If no General Documents category exists, create it
            logger.warning("No 'General Documents' category found, creating one")
            general_cat_id = self.db_service.create_category(
                label='General Documents',
                user_id=user_id
            )
            
            self.db_service.update_document(document_id, cluster_id=general_cat_id)
            
            logger.info(f"✓ Created and assigned to 'General Documents' (ID: {general_cat_id})")
            
            return {
                'success': True,
                'category_id': general_cat_id,
                'category_name': 'General Documents',
                'is_new': True,
                'similarity': 1.0,
                'keyword_match': False,
                'default': True
            }
        
        except Exception as e:
            logger.error(f"Hybrid categorization failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def categorize_from_chunks(
        self,
        document_id: str,
        user_id: str,
        filename: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Categorize document by aggregating chunk embeddings (hybrid approach).
        
        Args:
            document_id: Document ID
            user_id: User ID
            filename: Document filename for keyword hints
        
        Returns:
            Categorization result
        """
        try:
            # Get document content
            doc = self.db_service.get_document(document_id)
            if not doc:
                raise ValueError("Document not found")
            
            content = doc.get('content', '')
            
            # Get chunks from database
            chunks = self.db_service.get_chunks_by_document(document_id)
            
            if not chunks:
                raise ValueError("No chunks found for document")
            
            # Extract embeddings
            embeddings = []
            for chunk in chunks:
                embedding = self.db_service.parse_embedding(chunk.get('embedding'))
                if embedding is not None:
                    embeddings.append(embedding)
            
            if not embeddings:
                raise ValueError("No valid embeddings in chunks")
            
            # Aggregate embeddings (mean pooling)
            aggregated_embedding = np.mean(embeddings, axis=0)
            
            # Normalize
            aggregated_embedding = aggregated_embedding / (np.linalg.norm(aggregated_embedding) + 1e-8)
            
            # Update document embedding
            self.db_service.update_document(
                document_id,
                embedding=aggregated_embedding
            )
            
            # Use hybrid categorization
            result = self.categorize_document_hybrid(
                document_id,
                user_id,
                aggregated_embedding,
                content,
                filename
            )
            
            result['chunks_processed'] = len(embeddings)
            
            return result
        
        except Exception as e:
            logger.error(f"Chunk-based hybrid categorization failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _load_categories(self, user_id: str) -> List[Category]:
        """Load categories for a user."""
        categories_data = self.db_service.get_categories_by_user(user_id)
        
        categories = []
        for cat_data in categories_data:
            centroid = self.db_service.parse_embedding(cat_data.get('centroid'))
            if centroid is not None:
                category = Category(
                    id=cat_data['id'],
                    label=cat_data['label'],
                    centroid=centroid,
                    doc_count=0,
                    user_id=cat_data['user_id'],
                    created_at=cat_data['created_at']
                )
                categories.append(category)
        
        return categories
    
    def _find_best_category(
        self,
        embedding: np.ndarray,
        categories: List[Category]
    ) -> Optional[Dict[str, Any]]:
        """Find best matching category for an embedding."""
        if not categories:
            return None
        
        best_similarity = -1.0
        best_category = None
        
        for category in categories:
            # Skip zero centroids (uninitialized categories)
            if np.allclose(category['centroid'], 0):
                continue
            
            # Compute cosine similarity
            sim = float(cosine_similarity(
                embedding.reshape(1, -1),
                np.array(category['centroid']).reshape(1, -1)
            )[0, 0])
            
            if sim > best_similarity:
                best_similarity = sim
                best_category = category
        
        if best_category is None:
            return None
        
        return {
            'category_id': best_category.id,
            'category': best_category,
            'similarity': best_similarity
        }
    
    def _update_category_centroid(
        self,
        category_id: int,
        category: Category,
        new_embedding: np.ndarray,
        update_weight: float = 0.1
    ) -> None:
        """
        Update category centroid with new document embedding.
        Uses exponential moving average for stability.
        """
        # If centroid is zero (uninitialized), just use new embedding
        if np.allclose(category['centroid'], 0):
            updated_centroid = new_embedding
        else:
            # Exponential moving average
            updated_centroid = (
                (1 - update_weight) * np.array(category['centroid']) +
                update_weight * new_embedding
            )
        
        # Normalize
        updated_centroid = updated_centroid / (np.linalg.norm(updated_centroid) + 1e-8)
        
        # Update in database
        self.db_service.update_category(
            category_id,
            centroid=updated_centroid
        )
        
        logger.debug(f"Updated centroid for category {category_id}")

    def _analyze_keywords(self, content: str, filename: str) -> List[str]:
        """
        Simple keyword analysis to suggest categories based on content and filename.
        """
        try:
            content_lower = content.lower()
            filename_lower = filename.lower()
            
            # Define keyword mappings
            keyword_mappings = {
                'Academic Work': ['research', 'thesis', 'dissertation', 'academic', 'scholar', 'university', 'college'],
                'Course Materials': ['course', 'lecture', 'assignment', 'homework', 'syllabus', 'curriculum'],
                'Research & Papers': ['research', 'paper', 'study', 'analysis', 'findings', 'methodology'],
                'Science & Tech': ['science', 'technology', 'tech', 'engineering', 'programming', 'code', 'software'],
                'Language & Arts': ['language', 'literature', 'art', 'creative', 'writing', 'poetry', 'novel'],
                'Health & Medicine': ['health', 'medical', 'medicine', 'doctor', 'patient', 'treatment', 'therapy'],
                'Business & Finance': ['business', 'finance', 'money', 'investment', 'market', 'economy', 'corporate'],
                'General Documents': ['document', 'file', 'text', 'general']
            }
            
            suggested_categories = []
            
            # Check content keywords
            for category, keywords in keyword_mappings.items():
                for keyword in keywords:
                    if keyword in content_lower or keyword in filename_lower:
                        suggested_categories.append(category)
                        break
            
            # If no keywords found, suggest General Documents
            if not suggested_categories:
                suggested_categories.append('General Documents')
            
            return suggested_categories
            
        except Exception as e:
            logger.error(f"Keyword analysis failed: {e}")
            return ['General Documents']


# Singleton instance
_categorization_service: Optional[CategorizationService] = None


def get_categorization_service() -> CategorizationService:
    """Get or create categorization service singleton."""
    global _categorization_service
    if _categorization_service is None:
        _categorization_service = CategorizationService()
    return _categorization_service


    def _enhanced_keyword_analysis(self, content: str, filename: str) -> Dict[str, Any]:
        """
        Enhanced keyword analysis with weighted scoring and confidence.
        """
        text = f"{filename} {content}".lower()
        
        # Enhanced keyword patterns with weights
        enhanced_keywords = {
            'Academic Work': {
                'high': ['assignment', 'homework', 'due', 'problem set', 'quiz', 'test', 'project'],
                'medium': ['essay', 'paper', 'submission', 'deadline', 'coursework'],
                'low': ['exercise', 'practice', 'assessment', 'hw', 'pset']
            },
            'Science & Tech': {
                'high': ['programming', 'algorithm', 'code', 'python', 'java', 'software', 'computer'],
                'medium': ['engineering', 'technical', 'system', 'cs', 'coding'],
                'low': ['data', 'analysis', 'computing', 'digital', 'tech']
            },
            'Research & Papers': {
                'high': ['research', 'study', 'journal', 'publication', 'thesis', 'paper'],
                'medium': ['article', 'analysis', 'methodology', 'findings', 'investigation'],
                'low': ['review', 'survey', 'examination', 'report']
            }
        }
        
        category_scores = {}
        total_score = 0
        
        for category, keywords in enhanced_keywords.items():
            score = 0
            
            # High weight keywords (3 points)
            for keyword in keywords['high']:
                if keyword in text:
                    score += 3
            
            # Medium weight keywords (2 points)
            for keyword in keywords['medium']:
                if keyword in text:
                    score += 2
            
            # Low weight keywords (1 point)
            for keyword in keywords['low']:
                if keyword in text:
                    score += 1
            
            category_scores[category] = score
            total_score += score
        
        # Calculate confidence based on score distribution
        if total_score > 0:
            max_score = max(category_scores.values())
            confidence = min(max_score / total_score * 2, 1.0)  # Normalize to 0-1
        else:
            confidence = 0.0
        
        # Get suggestions (top 2 categories)
        suggestions = sorted(category_scores.keys(), key=lambda k: category_scores[k], reverse=True)[:2]
        
        return {
            'suggestions': suggestions,
            'confidence': confidence,
            'scores': category_scores
        }
    
    def _get_enhanced_candidates(self, suggested_categories: List[str], existing_categories: List[Dict], user_id: str) -> List[Dict]:
        """
        Enhanced candidate filtering with dynamic category creation.
        """
        candidates = [
            cat for cat in existing_categories
            if cat['label'] in suggested_categories
        ]
        
        # Create missing categories if needed
        if not candidates and suggested_categories:
            logger.info(f"No existing categories match suggestions: {suggested_categories}")
            for suggested_cat in suggested_categories:
                if suggested_cat in self.standard_categories:
                    logger.info(f"Creating missing standard category: {suggested_cat}")
                    zero_centroid = np.zeros(self.embedding_service.get_dimension())
                    category_id = self.db_service.insert_category(
                        label=suggested_cat,
                        centroid=zero_centroid,
                        user_id=user_id
                    )
                    logger.info(f"Created category {suggested_cat} with ID {category_id}")
            
            # Reload categories
            existing_categories = self._load_categories(user_id)
            candidates = [
                cat for cat in existing_categories
                if cat['label'] in suggested_categories
            ]
        
        # If still no candidates, use all categories
        if not candidates:
            candidates = existing_categories
        
        return candidates
    
    def _enhanced_semantic_matching(self, embedding: np.ndarray, candidates: List[Dict], content: str, filename: str) -> Dict[str, Any]:
        """
        Enhanced semantic matching with confidence scoring.
        """
        if not candidates:
            return {'best_match': None, 'confidence': 0.0}
        
        similarities = []
        
        for category in candidates:
            centroid = self.db_service.parse_embedding(category.get('centroid'))
            if centroid is not None:
                similarity = float(np.dot(embedding, centroid) / (
                    np.linalg.norm(embedding) * np.linalg.norm(centroid) + 1e-8
                ))
                similarities.append({
                    'category_id': category['id'],
                    'category': category,
                    'similarity': similarity
                })
        
        if not similarities:
            return {'best_match': None, 'confidence': 0.0}
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        best_match = similarities[0]
        
        # Calculate confidence based on similarity distribution
        if len(similarities) > 1:
            similarity_gap = best_match['similarity'] - similarities[1]['similarity']
            confidence = min(best_match['similarity'] + similarity_gap * 0.5, 1.0)
        else:
            confidence = best_match['similarity']
        
        return {
            'best_match': best_match,
            'confidence': confidence,
            'all_similarities': similarities
        }
    
    def _calculate_dynamic_threshold(self, similarity: float, keyword_confidence: float, semantic_confidence: float, category_count: int) -> float:
        """
        Calculate dynamic threshold based on multiple factors.
        """
        base_threshold = self.similarity_threshold
        
        # Adjust based on confidence levels
        if keyword_confidence > 0.7 and semantic_confidence > 0.7:
            # High confidence in both methods - be more lenient
            threshold = base_threshold - 0.05
        elif keyword_confidence < 0.3 or semantic_confidence < 0.3:
            # Low confidence - be more strict
            threshold = base_threshold + 0.1
        else:
            threshold = base_threshold
        
        # Adjust based on category density
        if category_count > 10:
            threshold += 0.05  # More categories = stricter
        elif category_count < 5:
            threshold -= 0.05  # Fewer categories = more lenient
        
        # Clamp to reasonable range
        return max(0.25, min(0.75, threshold))
    
    def _calculate_overall_confidence(self, similarity: float, keyword_confidence: float, semantic_confidence: float, keyword_match: bool) -> float:
        """
        Calculate overall confidence score.
        """
        # Weighted combination
        weights = {
            'semantic': 0.5,
            'keyword': 0.3,
            'match': 0.2
        }
        
        confidence = (
            similarity * weights['semantic'] +
            keyword_confidence * weights['keyword'] +
            (1.0 if keyword_match else 0.0) * weights['match']
        )
        
        return min(confidence, 1.0)
    
    def _update_category_centroid_with_learning(self, category_id: int, category: Dict, new_embedding: np.ndarray, confidence: float):
        """
        Update category centroid with adaptive learning rate based on confidence.
        """
        try:
            current_centroid = self.db_service.parse_embedding(category.get('centroid'))
            if current_centroid is None:
                return
            
            # Adaptive learning rate based on confidence
            learning_rate = 0.1 * confidence  # Higher confidence = faster learning
            
            # Update centroid with learning rate
            updated_centroid = (1 - learning_rate) * current_centroid + learning_rate * new_embedding
            updated_centroid = updated_centroid / (np.linalg.norm(updated_centroid) + 1e-8)
            
            # Update in database
            self.db_service.update_category(category_id, centroid=updated_centroid)
            
            logger.debug(f"Updated category {category_id} centroid with learning rate {learning_rate:.3f}")
        
        except Exception as e:
            logger.error(f"Failed to update category centroid with learning: {e}")

    return _categorization_service


# Backward compatibility alias
def get_improved_categorization_service() -> CategorizationService:
    """Get or create categorization service singleton (backward compatibility)."""
    return get_categorization_service()

