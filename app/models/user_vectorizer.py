"""User vectorization module - Creates 76-dimensional vectors for students"""
import numpy as np
import pandas as pd
import re
from typing import Optional, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.data_manager import DataManager, CarreraMapper


class UserVectorizer:
    """Vectorizes user data into 76-dimensional vectors (69 technical + 7 soft skills)"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.habilidades = self.data_manager.habilidades
        self.grupos_bge_ngram = self.data_manager.grupos_bge_ngram
        self.tfidf_epn_69d = self.data_manager.tfidf_epn_69d
        
        # Initialize TF-IDF vectorizer for soft skill similarity search
        self.vectorizer = TfidfVectorizer().fit(self.habilidades)
    
    def get_academic_vector_69d(self, carrera_académica: str) -> Optional[np.ndarray]:
        """
        Get base academic vector (69 dimensions) for a career
        
        Args:
            carrera_académica: Career name in tfidf_epn_69d format
            
        Returns:
            numpy array of shape (69,) or None if career not found
        """
        try:
            if carrera_académica not in self.tfidf_epn_69d.columns:
                return None
            return self.tfidf_epn_69d.T.loc[carrera_académica].values
        except Exception as e:
            print(f"Error getting academic vector for {carrera_académica}: {e}")
            return None
    
    def _normalize_text(self, texto: str) -> List[str]:
        """
        Normalize text into list of items (split by comma, semicolon, etc.)
        
        Args:
            texto: Input text
            
        Returns:
            List of normalized strings
        """
        if not isinstance(texto, str) or not texto.strip():
            return []
        
        items = [a.strip().lower() for a in re.split(r',|;|/|\n', texto) if a.strip()]
        return items
    
    def _find_similar_skills(self, asignatura: str, threshold: float = 0.5) -> List[str]:
        """
        Find skills similar to a given subject using TF-IDF similarity
        
        Args:
            asignatura: Subject name
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar skills
        """
        if not asignatura.strip():
            return []
        
        try:
            vect_asig = self.vectorizer.transform([asignatura])
            vect_habs = self.vectorizer.transform(self.habilidades)
            sims = cosine_similarity(vect_asig, vect_habs).flatten()
            
            similar_skills = [self.habilidades[i] for i in np.where(sims >= threshold)[0]]
            return similar_skills
        except Exception as e:
            print(f"Error finding similar skills for '{asignatura}': {e}")
            return []
    
    def personalize_vector_69d(self, vector_base_69d: np.ndarray, 
                               asignaturas_relevantes: str) -> np.ndarray:
        """
        Personalize academic vector based on relevant subjects
        
        Args:
            vector_base_69d: Base academic vector (shape: 69,)
            asignaturas_relevantes: String with comma-separated subjects
            
        Returns:
            Personalized vector (shape: 69,)
        """
        if vector_base_69d is None or len(vector_base_69d) != 69:
            return vector_base_69d
        
        vector = vector_base_69d.copy()
        
        for asignatura in self._normalize_text(asignaturas_relevantes):
            similar_skills = self._find_similar_skills(asignatura)
            for skill in similar_skills:
                try:
                    skill_idx = self.habilidades.index(skill)
                    if 0 <= skill_idx < len(vector):
                        vector[skill_idx] = 0.99  # Set to maximum personalization
                except ValueError:
                    continue
        
        return vector
    
    def _normalize_soft_skills(self, valores_1_a_5: List[int]) -> np.ndarray:
        """
        Normalize soft skill ratings from [1,5] to [0,1]
        
        Args:
            valores_1_a_5: List of ratings 1-5
            
        Returns:
            numpy array with values in [0, 1]
        """
        if not valores_1_a_5 or len(valores_1_a_5) != 7:
            # Return default middle values if invalid
            return np.ones(7) * 0.5
        
        try:
            values = np.array(valores_1_a_5, dtype=float)
            # Clip to [1, 5] range just in case
            values = np.clip(values, 1, 5)
            # Normalize to [0, 1]
            normalized = (values - 1) / 4
            return normalized
        except Exception as e:
            print(f"Error normalizing soft skills: {e}")
            return np.ones(7) * 0.5
    
    def create_vector_76d(self, 
                         carrera_académica: str,
                         asignaturas_relevantes: str,
                         soft_skills_1_to_5: List[int]) -> Optional[np.ndarray]:
        """
        Create complete 76-dimensional vector for a student
        
        Args:
            carrera_académica: Career in tfidf_epn_69d format
            asignaturas_relevantes: Comma-separated relevant subjects
            soft_skills_1_to_5: List of 7 ratings (1-5) for soft skills
            
        Returns:
            76-dimensional vector or None if error
        """
        # Get base academic vector
        vector_69d = self.get_academic_vector_69d(carrera_académica)
        if vector_69d is None:
            return None
        
        # Personalize based on subjects
        vector_69d_personalized = self.personalize_vector_69d(
            vector_69d, 
            asignaturas_relevantes
        )
        
        # Normalize soft skills
        vector_7d = self._normalize_soft_skills(soft_skills_1_to_5)
        
        # Concatenate: 69 technical + 7 soft skills = 76 total
        vector_76d = np.concatenate([vector_69d_personalized, vector_7d])
        
        return vector_76d
    
    def get_vector_info(self, vector_76d: np.ndarray) -> dict:
        """
        Get information about a 76-dimensional vector
        
        Args:
            vector_76d: 76-dimensional vector
            
        Returns:
            Dictionary with vector information
        """
        if not isinstance(vector_76d, np.ndarray) or vector_76d.shape[0] != 76:
            return {}
        
        return {
            'shape': (76,),
            'technical_dims': 69,
            'soft_skills_dims': 7,
            'technical_vector': vector_76d[:69].tolist(),
            'soft_skills_vector': vector_76d[69:].tolist(),
            'soft_skills_labels': CarreraMapper.SOFT_SKILLS_LABELS,
            'technical_mean': float(np.mean(vector_76d[:69])),
            'soft_skills_mean': float(np.mean(vector_76d[69:])),
            'overall_mean': float(np.mean(vector_76d))
        }
