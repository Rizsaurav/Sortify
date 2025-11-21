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
from utils import get_logger, TextProcessor, get_categorization_debugger
from settings import get_settings

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
        'Professional Documents': [
            'resume', 'cv', 'cover letter', 'application', 'job', 'position',
            'hiring', 'employment', 'career', 'experience', 'skills', 'qualification',
            'professional', 'portfolio', 'linkedin', 'references', 'objective',
            'summary', 'education', 'work history', 'candidate'
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
        self.debugger = get_categorization_debugger()
        
        logger.info(
            f"CategorizationService initialized "
            f"(threshold={self.similarity_threshold}, "
            f"max={self.max_categories}, "
            f"debug={self.debugger.enabled})"
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
        filename: str,
        chunk_count: int = 0
    ) -> Dict[str, Any]:
        """
        Enhanced hybrid categorization with multi-pass analysis and confidence scoring.

        Args:
            document_id: Document ID
            user_id: User ID
            aggregated_embedding: Document embedding
            content: Document content (for keyword extraction)
            filename: Document filename (for keyword hints)
            chunk_count: Number of chunks aggregated (for debugging)

        Returns:
            Categorization result with confidence scoring
        """
        try:
            logger.info(f"Hybrid categorizing document {document_id}")
            # Normalize/clean embedding input defensively
            aggregated_embedding = np.array(aggregated_embedding, dtype=np.float32).reshape(-1)
            if aggregated_embedding.size == 0:
                raise ValueError("Empty embedding received for categorization")

            embedding_norm = float(np.linalg.norm(aggregated_embedding))
            if embedding_norm > 0:
                aggregated_embedding = aggregated_embedding / (embedding_norm + 1e-8)

            self.debugger.start_categorization(document_id, filename)
            self.debugger.log_embedding_info(
                embedding_dim=len(aggregated_embedding),
                embedding_norm=embedding_norm,
                num_chunks=chunk_count,
                sample=aggregated_embedding.tolist()[:10]
            )

            # Get existing categories
            existing_categories = self.db_service.get_categories_by_user(user_id)

            if not existing_categories:
                # Initialize standard categories for new user
                logger.info(f"No categories found for user {user_id}, initializing standard categories")
                self.initialize_standard_categories(user_id)

                # Reload categories after initialization
                existing_categories = self.db_service.get_categories_by_user(user_id)

                if not existing_categories:
                    # Fallback: Create a general category if initialization failed
                    logger.warning("Standard category initialization failed, creating General Documents")
                    general_cat_id = self.db_service.get_or_create_general_category(user_id)
                    if general_cat_id:
                        # Update document
                        self.db_service.update_document(document_id, cluster_id=general_cat_id)

                        reason = "No categories available; created General Documents fallback"
                        self.debugger.log_decision(
                            decision="fallback_general",
                            reason=reason,
                            category='General Documents',
                            similarity=1.0
                        )
                        self.debugger.log_final_result({
                            'category_id': general_cat_id,
                            'category_name': 'General Documents',
                            'method': 'fallback_initialize',
                            'chunks_processed': chunk_count
                        })
                        self.debugger.end_categorization()

                        return {
                            'success': True,
                            'category_id': general_cat_id,
                            'category_name': 'General Documents',
                            'is_new': True,
                            'similarity': 1.0,
                            'keyword_match': False,
                            'default': True
                        }
            
            # Enhanced keyword analysis
            suggested_categories = self._analyze_keywords(content, filename)
            logger.info(f"Keyword suggestions: {suggested_categories}")
            keyword_scores = self._get_keyword_scores(content, filename)
            self.debugger.log_keyword_analysis(
                suggested_categories=suggested_categories,
                keyword_scores=keyword_scores,
                filename=filename,
                content_preview=content[:500]
            )

            # Find best semantic matches (including zero-centroid categories for keyword matching)
            semantic_matches = []

            for category in existing_categories:
                centroid_array = self.db_service.parse_embedding(category.get('centroid'))
                if centroid_array is None:
                    logger.warning(f"Skipping category {category.get('id')} due to unparsable centroid")
                    continue
                try:
                    # Check if centroid is initialized (non-zero)
                    is_initialized = not np.allclose(centroid_array, 0)

                    # Calculate cosine similarity (0 for uninitialized centroids)
                    if is_initialized:
                        similarity = self._calculate_cosine_similarity(aggregated_embedding, centroid_array)
                    else:
                        similarity = 0.0  # No semantic info for uninitialized categories

                    # Boost similarity if category matches keyword suggestions
                    # BUT: Don't boost 'General Documents' - it should only be a fallback
                    keyword_boost = 0.0
                    if category['label'] in suggested_categories and category['label'] != 'General Documents':
                        # Boost by position in suggestions (first match gets higher boost)
                        position = suggested_categories.index(category['label'])

                        # For uninitialized categories, rely heavily on keyword matching
                        # But still differentiate by position
                        if not is_initialized:
                            keyword_boost = 0.8 - (position * 0.1)  # 0.8, 0.7, 0.6 for positions 0, 1, 2
                        else:
                            keyword_boost = 0.15 - (position * 0.05)  # 0.15, 0.10, 0.05 for initialized

                        logger.info(f"Keyword boost for '{category['label']}': +{keyword_boost:.2f} (initialized={is_initialized})")

                    boosted_similarity = min(1.0, similarity + keyword_boost)

                    # Include category if it has semantic similarity OR keyword match (but not General Documents)
                    if is_initialized or (category['label'] in suggested_categories and category['label'] != 'General Documents'):
                        semantic_matches.append({
                            'category_id': category['id'],
                            'category': category,
                            'similarity': similarity,
                            'boosted_similarity': boosted_similarity,
                            'keyword_match': category['label'] in suggested_categories,
                            'is_initialized': is_initialized
                        })
                except Exception as e:
                    logger.warning(f"Error calculating similarity for category {category.get('id')}: {e}")
                    continue

            # Sort by boosted similarity
            semantic_matches.sort(key=lambda x: x['boosted_similarity'], reverse=True)
            best_match = semantic_matches[0] if semantic_matches else None

            # Dynamic threshold based on keyword confidence
            base_threshold = self.similarity_threshold
            # Lower threshold if strong keyword match
            if best_match and best_match['keyword_match']:
                dynamic_threshold = base_threshold - 0.1  # More lenient with keyword match
            else:
                dynamic_threshold = base_threshold

            self.debugger.log_similarity_matrix(
                similarities=semantic_matches[:10],
                threshold=base_threshold,
                dynamic_threshold=dynamic_threshold
            )
            
            if best_match and best_match['boosted_similarity'] >= dynamic_threshold:
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

                reason = (
                    f"Boosted similarity ({best_match['boosted_similarity']:.3f}) "
                    f"above dynamic threshold ({dynamic_threshold:.3f}) "
                    f"keyword_match={best_match['keyword_match']}"
                )
                self.debugger.log_decision(
                    decision="assigned",
                    reason=reason,
                    category=category['label'],
                    similarity=best_match['similarity']
                )
                self.debugger.log_final_result({
                    'category_id': category_id,
                    'category_name': category['label'],
                    'similarity': best_match['similarity'],
                    'method': 'semantic',
                    'chunks_processed': chunk_count
                })
                self.debugger.end_categorization()
                
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

                reason = (
                    f"Best semantic match below threshold ({best_match['similarity']:.3f} "
                    f"< {dynamic_threshold:.3f}) but used as fallback"
                )
                self.debugger.log_decision(
                    decision="semantic_fallback",
                    reason=reason,
                    category=category['label'],
                    similarity=best_match['similarity']
                )
                self.debugger.log_final_result({
                    'category_id': category_id,
                    'category_name': category['label'],
                    'similarity': best_match['similarity'],
                    'method': 'semantic_fallback',
                    'chunks_processed': chunk_count
                })
                self.debugger.end_categorization()
                
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

                reason = "No categories exceeded threshold; defaulting to General Documents"
                self.debugger.log_decision(
                    decision="default_general",
                    reason=reason,
                    category='General Documents',
                    similarity=0.0
                )
                self.debugger.log_final_result({
                    'category_id': general_cat['id'],
                    'category_name': 'General Documents',
                    'similarity': 0.0,
                    'method': 'default',
                    'chunks_processed': chunk_count
                })
                self.debugger.end_categorization()
                
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

            reason = "General Documents category was missing; created and assigned"
            self.debugger.log_decision(
                decision="create_general",
                reason=reason,
                category='General Documents',
                similarity=1.0
            )
            self.debugger.log_final_result({
                'category_id': general_cat_id,
                'category_name': 'General Documents',
                'similarity': 1.0,
                'method': 'created_default',
                'chunks_processed': chunk_count
            })
            self.debugger.end_categorization()
            
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
            self.debugger.log_decision(
                decision="error",
                reason=str(e),
                category=None,
                similarity=0.0
            )
            self.debugger.end_categorization()
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
                # FALLBACK: Use document content directly
                logger.warning(
                    f"No chunks found for document {document_id}, "
                    "falling back to content-based categorization"
                )
                return self.categorize_from_document_content(
                    document_id, user_id, filename
                )

            # Extract embeddings
            embeddings = []
            for chunk in chunks:
                embedding = self.db_service.parse_embedding(chunk.get('embedding'))
                if embedding is not None:
                    embeddings.append(embedding)

            if not embeddings:
                logger.warning("No valid embeddings in chunks; falling back to content-based categorization")
                return self.categorize_from_document_content(
                    document_id=document_id,
                    user_id=user_id,
                    filename=filename
                )

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
                document_id=document_id,
                user_id=user_id,
                aggregated_embedding=aggregated_embedding,
                content=content,
                filename=filename,
                chunk_count=len(embeddings)
            )

            result['chunks_processed'] = len(embeddings)
            return result

        except Exception as e:
            logger.error(f"Chunk-based hybrid categorization failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def categorize_from_document_content(
        self,
        document_id: str,
        user_id: str,
        filename: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Fallback categorization using full document content when chunks are unavailable.
        """
        try:
            logger.info(
                f"Using content-based categorization for document {document_id}"
            )

            # Fetch document to access raw content
            document = self.db_service.get_document(document_id)
            if not document:
                raise ValueError("Document not found")

            content = document.get('content', '')
            if not content:
                raise ValueError("Document has no content")

            # Generate embedding for entire document content
            embedding = self.embedding_service.encode(content)

            # Normalize embedding for consistency with chunk-based approach
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)

            # Reuse hybrid categorization pipeline
            result = self.categorize_document_hybrid(
                document_id=document_id,
                user_id=user_id,
                aggregated_embedding=embedding,
                content=content,
                filename=filename,
                chunk_count=0
            )

            result['method'] = 'content_fallback'
            result['chunks_processed'] = 0
            return result

        except Exception as e:
            logger.error(f"Content-based categorization failed: {e}")
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

    def _calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # Ensure embeddings are numpy arrays
            emb1 = np.array(embedding1, dtype=np.float32)
            emb2 = np.array(embedding2, dtype=np.float32)

            # Normalize vectors
            emb1_norm = emb1 / (np.linalg.norm(emb1) + 1e-8)
            emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-8)

            # Calculate cosine similarity
            similarity = float(np.dot(emb1_norm, emb2_norm))

            # Clamp to [0, 1]
            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def _calculate_keyword_scores(self, content: str, filename: str) -> Dict[str, int]:
        """Calculate keyword scores for each category."""
        # Use filename and first 2000 chars of content for efficiency
        text_sample = content[:2000] if len(content) > 2000 else content
        content_lower = text_sample.lower()
        filename_lower = filename.lower()

        category_scores: Dict[str, int] = {}

        # Check CATEGORY_KEYWORDS (main patterns)
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in filename_lower:
                    score += 3
                elif keyword in content_lower:
                    score += 1

            if score > 0:
                category_scores[category] = score

        # Check SUBJECT_KEYWORDS (specific subjects)
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in filename_lower:
                    score += 3
                elif keyword in content_lower:
                    score += 1

            if score > 0:
                if subject in ['Computer Science']:
                    category_scores['Science & Tech'] = category_scores.get('Science & Tech', 0) + score
                elif subject in ['Mathematics']:
                    category_scores['Mathematics'] = category_scores.get('Mathematics', 0) + score
                elif subject in ['Biology', 'Chemistry', 'Physics']:
                    category_scores['Science & Tech'] = category_scores.get('Science & Tech', 0) + score

        return category_scores

    def _get_keyword_scores(self, content: str, filename: str) -> Dict[str, int]:
        """Safe wrapper to expose keyword scores for debugging."""
        try:
            return self._calculate_keyword_scores(content, filename)
        except Exception as e:
            logger.error(f"Keyword score calculation failed: {e}")
            return {}

    def _analyze_keywords(self, content: str, filename: str) -> List[str]:
        """
        Enhanced keyword analysis using comprehensive keyword patterns.
        Weighs filename more heavily than content, checks first 2000 chars of content.
        """
        try:
            category_scores = self._calculate_keyword_scores(content, filename)

            if category_scores:
                sorted_categories = sorted(
                    category_scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                suggested = [cat for cat, score in sorted_categories if score >= 1][:3]

                if suggested:
                    logger.info(f"Keyword suggestions (scores): {[(c, category_scores[c]) for c in suggested]}")
                    return suggested

            return ['General Documents']

        except Exception as e:
            logger.error(f"Keyword analysis failed: {e}")
            return ['General Documents']

    def recategorize_uncategorized_documents(self, limit: int = 25) -> Dict[str, int]:
        """
        Re-run categorization for documents without an assigned category.

        Args:
            limit: Maximum number of uncategorized documents to process in one pass
        """
        docs = self.db_service.get_uncategorized_documents(limit=limit)
        stats = {
            'found': len(docs),
            'processed': 0,
            'skipped': 0,
            'errors': 0,
        }

        for doc in docs:
            doc_id = doc.get('id')
            metadata = doc.get('metadata') or {}
            user_id = metadata.get('user_id')
            filename = doc.get('filename') or doc.get('title') or doc.get('name') or 'unknown'

            if not doc_id or not user_id:
                stats['skipped'] += 1
                continue

            try:
                result = self.categorize_from_chunks(
                    document_id=doc_id,
                    user_id=user_id,
                    filename=filename
                )
                if result.get('success'):
                    stats['processed'] += 1
                else:
                    stats['errors'] += 1
            except Exception as exc:
                logger.error(f"Failed to recategorize document {doc_id}: {exc}")
                stats['errors'] += 1

        logger.info(
            "Recategorized uncategorized documents "
            f"(found={stats['found']}, processed={stats['processed']}, "
            f"skipped={stats['skipped']}, errors={stats['errors']})"
        )
        return stats

    def recategorize_documents(self, limit: int = 200, only_general: bool = True) -> Dict[str, int]:
        """
        Re-run categorization for existing documents (optionally limited to General/uncategorized).

        Args:
            limit: maximum documents to process
            only_general: if True, only recategorize docs in General or uncategorized
        """
        docs = self.db_service.get_documents(limit=limit)
        stats = {
            'found': len(docs),
            'processed': 0,
            'skipped': 0,
            'errors': 0,
        }

        # Cache general category ids per user to avoid repeat lookups
        general_id_cache: Dict[str, Optional[int]] = {}

        for doc in docs:
            doc_id = doc.get('id')
            metadata = doc.get('metadata') or {}
            user_id = metadata.get('user_id')
            filename = doc.get('filename') or doc.get('title') or doc.get('name') or 'unknown'
            cluster_id = doc.get('cluster_id')

            if not doc_id or not user_id:
                stats['skipped'] += 1
                continue

            if only_general:
                if user_id not in general_id_cache:
                    cats = self.db_service.get_categories_by_user(user_id)
                    general = next((c for c in cats if c.get('label') == 'General Documents'), None)
                    general_id_cache[user_id] = general.get('id') if general else None
                general_id = general_id_cache[user_id]

                # Skip if the doc is already in a non-general category
                if cluster_id is not None and cluster_id != general_id:
                    stats['skipped'] += 1
                    continue

            try:
                result = self.categorize_from_chunks(
                    document_id=doc_id,
                    user_id=user_id,
                    filename=filename
                )
                if result.get('success'):
                    stats['processed'] += 1
                else:
                    stats['errors'] += 1
            except Exception as exc:
                logger.error(f"Failed to recategorize document {doc_id}: {exc}")
                stats['errors'] += 1

        logger.info(
            "Recategorized documents "
            f"(found={stats['found']}, processed={stats['processed']}, "
            f"skipped={stats['skipped']}, errors={stats['errors']})"
        )
        return stats


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


# Backward compatibility alias
def get_improved_categorization_service() -> CategorizationService:
    """Get or create categorization service singleton (backward compatibility)."""
    return get_categorization_service()
