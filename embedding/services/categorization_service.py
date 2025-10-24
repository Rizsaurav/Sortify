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
        Categorize document using hybrid approach (semantic + keywords).
        
        Args:
            document_id: Document ID
            user_id: User ID
            aggregated_embedding: Document embedding
            content: Document content (for keyword extraction)
            filename: Document filename (for keyword hints)
        
        Returns:
            Categorization result
        """
        try:
            logger.info(f"Hybrid categorizing document {document_id}")
            
            # Get existing categories
            existing_categories = self._load_categories(user_id)
            
            if not existing_categories:
                # Initialize standard categories for new user
                logger.info(f"No categories found for user {user_id}, initializing standard categories")
                self.initialize_standard_categories(user_id)
                existing_categories = self._load_categories(user_id)
                
                # If still no categories, create a General Documents category
                if not existing_categories:
                    logger.warning("Standard category initialization failed, creating General Documents category")
                    general_cat_id = self.db_service.insert_category(
                        label='General Documents',
                        centroid=aggregated_embedding,
                        user_id=user_id
                    )
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
            
            # Step 1: Keyword-based hints
            suggested_categories = self.detect_category_from_keywords(content, filename)
            logger.info(f"Keyword suggestions: {suggested_categories}")
            
            # Step 2: Filter to relevant candidates
            if suggested_categories:
                candidates = [
                    cat for cat in existing_categories
                    if cat.label in suggested_categories
                ]
                # If no matches, create missing categories
                if not candidates:
                    logger.info(f"No existing categories match suggestions: {suggested_categories}")
                    # Create missing categories
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
                    
                    # Reload categories to include new ones
                    existing_categories = self._load_categories(user_id)
                    candidates = [
                        cat for cat in existing_categories
                        if cat.label in suggested_categories
                    ]
                
                # If still no candidates, use all categories
                if not candidates:
                    candidates = existing_categories
            else:
                candidates = existing_categories
            
            # Step 3: Find best semantic match
            best_match = self._find_best_category(aggregated_embedding, candidates)
            
            # Step 4: Validate with threshold
            if best_match and best_match['similarity'] >= self.similarity_threshold:
                category_id = best_match['category_id']
                category = best_match['category']
                
                # Update document
                self.db_service.update_document(document_id, cluster_id=category_id)
                
                # Update category centroid
                self._update_category_centroid(
                    category_id,
                    category,
                    aggregated_embedding
                )
                
                logger.info(
                    f"✓ Assigned to '{category.label}' "
                    f"(similarity: {best_match['similarity']:.3f}, "
                    f"keyword_match: {category.label in suggested_categories})"
                )
                
                return {
                    'success': True,
                    'category_id': category_id,
                    'category_name': category.label,
                    'is_new': False,
                    'similarity': best_match['similarity'],
                    'keyword_match': category.label in suggested_categories
                }
            
            # Step 5: Use best semantic match even if below threshold (no keyword fallback)
            elif best_match:
                category_id = best_match['category_id']
                category = best_match['category']
                
                self.db_service.update_document(document_id, cluster_id=category_id)
                self._update_category_centroid(
                    category_id,
                    category,
                    aggregated_embedding
                )
                
                logger.info(
                    f"✓ Assigned to '{category.label}' via semantic match "
                    f"(similarity: {best_match['similarity']:.3f}, below threshold)"
                )
                
                return {
                    'success': True,
                    'category_id': category_id,
                    'category_name': category.label,
                    'is_new': False,
                    'similarity': best_match['similarity'],
                    'keyword_match': False,
                    'semantic_match': True
                }
            
            # Step 6: Assign to General Documents as last resort
            general_cat = next(
                (cat for cat in existing_categories if cat.label == 'General Documents'),
                None
            )
            
            if general_cat:
                self.db_service.update_document(document_id, cluster_id=general_cat.id)
                
                logger.info(f"✓ Assigned to 'General Documents' (no clear match)")
                
                return {
                    'success': True,
                    'category_id': general_cat.id,
                    'category_name': 'General Documents',
                    'is_new': False,
                    'similarity': 0.0,
                    'keyword_match': False,
                    'default': True
                }
            
            # Step 7: If no General Documents category exists, create it
            logger.warning("No 'General Documents' category found, creating one")
            general_cat_id = self.db_service.insert_category(
                label='General Documents',
                centroid=aggregated_embedding,
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
            if np.allclose(category.centroid, 0):
                continue
            
            # Compute cosine similarity
            sim = float(cosine_similarity(
                embedding.reshape(1, -1),
                category.centroid.reshape(1, -1)
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
        if np.allclose(category.centroid, 0):
            updated_centroid = new_embedding
        else:
            # Exponential moving average
            updated_centroid = (
                (1 - update_weight) * category.centroid +
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


# Singleton instance
_categorization_service: Optional[CategorizationService] = None


def get_categorization_service() -> CategorizationService:
    """Get or create categorization service singleton."""
    global _categorization_service
    if _categorization_service is None:
        _categorization_service = CategorizationService()
    return _categorization_service


# Backward compatibility alias
def get_improved_categorization_service() -> CategorizationService:
    """Get or create categorization service singleton (backward compatibility)."""
    return get_categorization_service()

