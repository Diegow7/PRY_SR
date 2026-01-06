"""Recommendation system module - Calculates job offer recommendations"""
import pandas as pd
import numpy as np
import os
from typing import Optional, Tuple, List
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.data_manager import DataManager, CarreraMapper

# Global cache to persist offers across requests and instances
_GLOBAL_OFFERS_CACHE: dict = {}


class RecommendationEngine:
    """Generates job offer recommendations based on student vectors (76d)"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.habilidades = self.data_manager.habilidades
        self.grupos_bge_ngram = self.data_manager.grupos_bge_ngram
        
        # Cache for loaded job offers (persist across requests)
        self._ofertas_cache = _GLOBAL_OFFERS_CACHE
    
    def _load_job_offers(self, csv_path: str) -> Optional[Tuple[pd.DataFrame, np.ndarray]]:
        """
        Load and vectorize job offers from a CSV file
        
        Args:
            csv_path: Path to CSV file with job offers
            
        Returns:
            Tuple of (DataFrame with offers, 69D TF-IDF matrix) or None if error
        """
        # Check cache first
        if csv_path in self._ofertas_cache:
            return self._ofertas_cache[csv_path]
        
        try:
            if not os.path.exists(csv_path):
                print(f"File not found: {csv_path}")
                return None
            
            # Load CSV
            df_ofertas = pd.read_csv(csv_path, dtype=str)
            
            # Validate required columns
            required_cols = {'skills', 'description', 'EURACE_skills'}
            if not required_cols.issubset(df_ofertas.columns):
                print(f"Missing required columns in {csv_path}")
                return None
            
            # Vectorize job descriptions
            textos = df_ofertas[['skills', 'description']].fillna('').agg(' '.join, axis=1).str.lower().tolist()
            
            # Create term-document matrix
            vectorizer = CountVectorizer(
                vocabulary=self.habilidades, 
                analyzer='word', 
                ngram_range=(1, 5), 
                lowercase=True
            )
            X = vectorizer.fit_transform(textos)
            matriz_td = pd.DataFrame(X.T.toarray(), index=vectorizer.get_feature_names_out())
            
            # Group by 69 dimensions
            matriz_69d = pd.DataFrame(0, index=self.grupos_bge_ngram.keys(), columns=range(len(textos)))
            for label, terms in self.grupos_bge_ngram.items():
                terms_validos = [t for t in terms if t in matriz_td.index]
                if terms_validos:
                    matriz_69d.loc[label] = matriz_td.loc[terms_validos].sum(axis=0)
            
            # Apply TF-IDF
            tfidf = TfidfTransformer(norm='l2')
            tfidf_69d = tfidf.fit_transform(matriz_69d.values)
            tfidf_69d_array = tfidf_69d.toarray()  # Convert to dense array
            
            # Cache the result
            self._ofertas_cache[csv_path] = (df_ofertas, tfidf_69d_array)
            
            return df_ofertas, tfidf_69d_array
            
        except Exception as e:
            print(f"Error loading offers from {csv_path}: {e}")
            return None
    
    def _expand_offers_to_76d(self, 
                             tfidf_69d_array: np.ndarray,
                             df_ofertas: pd.DataFrame) -> np.ndarray:
        """
        Expand 69D job offer vectors to 76D by adding soft skills
        
        Args:
            tfidf_69d_array: 69D TF-IDF vectors (shape: num_offers × 69)
            df_ofertas: DataFrame with job offer data
            
        Returns:
            76D vectors (shape: num_offers × 76)
        """
        num_offers = len(df_ofertas)
        vectores_76d = np.zeros((num_offers, 76))
        # Asegurarse de que tfidf_69d_array tiene forma (num_offers, 69)
        arr = tfidf_69d_array
        if arr.shape[0] == 69 and arr.shape[1] == num_offers:
            arr = arr.T  # Transponer si está al revés
        if arr.shape[0] != num_offers or arr.shape[1] != 69:
            raise ValueError(f"La matriz TF-IDF de ofertas tiene forma inesperada: {arr.shape}, esperado ({num_offers}, 69)")
        vectores_76d[:, :69] = arr
        
        # Add soft skills (69-75) - search for keywords in EURACE_skills
        soft_skills_keywords = [
            'gestion',
            'comunicacion',
            'liderazgo',
            'equipo',
            'etica',
            'responsabilidad',
            'aprendizaje'
        ]
        
        for idx in range(num_offers):
            eurace_skills = str(df_ofertas.iloc[idx].get('EURACE_skills', '')).lower()
            
            for skill_idx, keyword in enumerate(soft_skills_keywords):
                if keyword in eurace_skills:
                    vectores_76d[idx, 69 + skill_idx] = 1.0
        
        return vectores_76d
    
    def get_recommendations(self, 
                           student_vector_76d: np.ndarray,
                           carrera_académica: str,
                           top_n: int = 5) -> Optional[pd.DataFrame]:
        """
        Get job recommendations for a student
        
        Args:
            student_vector_76d: Student vector (76 dimensions)
            carrera_académica: Academic career name
            top_n: Number of recommendations to return
            
        Returns:
            DataFrame with recommendations or None if error
        """
        # Validate input
        if not isinstance(student_vector_76d, np.ndarray) or len(student_vector_76d) != 76:
            return None
        
        if top_n < 1:
            top_n = 5
        
        # Get CSV path(s) for this career (supports single path or list of paths)
        csv_path = CarreraMapper.get_career_csv(carrera_académica)
        if not csv_path:
            return None

        # Normalize to list of paths
        csv_paths = csv_path if isinstance(csv_path, list) else [csv_path]

        # Make paths absolute (relative to project root)
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        full_paths = [os.path.join(backend_dir, p) for p in csv_paths]

        # Load and vectorize offers from all sources, then merge
        df_list = []
        arr_list = []
        for csv_full_path in full_paths:
            result = self._load_job_offers(csv_full_path)
            if result is None:
                continue
            df, arr = result
            # Ensure shape (num_offers, 69)
            if arr.shape[0] == 69:
                arr = arr.T
            df_list.append(df)
            arr_list.append(arr)

        if not df_list:
            return None

        # Concatenate DataFrames and TF-IDF arrays
        df_ofertas = pd.concat(df_list, ignore_index=True)
        tfidf_69d_array = np.vstack(arr_list)
        
        # Expand to 76D
        vectores_76d = self._expand_offers_to_76d(tfidf_69d_array, df_ofertas)
        
        # Calculate cosine similarity
        similarities = cosine_similarity([student_vector_76d], vectores_76d)[0]
        
        # Sort by similarity (descending)
        indices_ordenados = np.argsort(similarities)[::-1]
        
        # Get top N unique offers (avoid duplicates by job title)
        resultado = []
        cargos_vistas = set()
        
        for idx_oferta in indices_ordenados:
            if len(resultado) >= top_n:
                break
            
            cargo_titulo = str(df_ofertas.iloc[idx_oferta].get('job_title', 'N/A'))
            
            # Avoid duplicates
            if cargo_titulo not in cargos_vistas:
                cargos_vistas.add(cargo_titulo)
                
                descripcion = str(df_ofertas.iloc[idx_oferta].get('description', ''))
                if len(descripcion) > 100:
                    descripcion = descripcion[:100] + '...'
                
                resultado.append({
                    'rank': len(resultado) + 1,
                    'similitud': float(similarities[idx_oferta]),
                    'cargo': cargo_titulo,
                    'descripcion': descripcion,
                    'eurace_skills': str(df_ofertas.iloc[idx_oferta].get('EURACE_skills', 'N/A')),
                    'skills': str(df_ofertas.iloc[idx_oferta].get('skills', 'N/A'))[:100] + '...',
                    'url': str(df_ofertas.iloc[idx_oferta].get('url', '')).strip()
                })
        
        if not resultado:
            return None
        
        return pd.DataFrame(resultado)
    
    def clear_cache(self) -> None:
        """Clear the job offers cache"""
        self._ofertas_cache.clear()
