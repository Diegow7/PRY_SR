"""Data loader module - Manages loading and caching of processed data"""
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional


class DataManager:
    """Manages loading and caching of all processed data"""
    
    _instance = None  # Singleton pattern
    _datos_procesados = None
    _is_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize data manager"""
        if not self._is_loaded:
            self._load_data()
            self._is_loaded = True
    
    def _load_data(self) -> None:
        """Load all processed data from pickle file"""
        try:
            # Get the parent directory of backend
            backend_dir = Path(__file__).parent.parent
            pkl_path = backend_dir / 'datos_procesados.pkl'
            
            if not pkl_path.exists():
                raise FileNotFoundError(f"datos_procesados.pkl not found at {pkl_path}")
            
            with open(pkl_path, 'rb') as f:
                self._datos_procesados = pickle.load(f)
            
            print(f"✓ Datos procesados cargados desde {pkl_path}")
        except Exception as e:
            raise RuntimeError(f"Error cargando datos procesados: {str(e)}")
    
    @property
    def habilidades(self) -> list:
        """Get list of all technical skills"""
        if not self._is_loaded:
            self._load_data()
        return self._datos_procesados.get('habilidades', [])
    
    @property
    def grupos_bge_ngram(self) -> Dict[str, list]:
        """Get skill grouping (69 groups)"""
        if not self._is_loaded:
            self._load_data()
        return self._datos_procesados.get('grupos_bge_ngram', {})
    
    @property
    def tfidf_epn_69d(self) -> pd.DataFrame:
        """Get TF-IDF matrix for academic careers (69 dimensions)"""
        if not self._is_loaded:
            self._load_data()
        return self._datos_procesados.get('tfidf_epn_69d')
    
    @property
    def ofertas_por_carrera(self) -> Dict[str, int]:
        """Get count of job offers by career"""
        if not self._is_loaded:
            self._load_data()
        return self._datos_procesados.get('ofertas_por_carrera', {})
    
    @property
    def tfidf_emb_df(self) -> pd.DataFrame:
        """Get TF-IDF matrix for job market offers"""
        if not self._is_loaded:
            self._load_data()
        return self._datos_procesados.get('tfidf_emb_df')
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all processed data"""
        if not self._is_loaded:
            self._load_data()
        return self._datos_procesados
    
    def is_ready(self) -> bool:
        """Check if data is loaded and ready"""
        return self._is_loaded and self._datos_procesados is not None


class CarreraMapper:
    """Maps career names from various sources"""
    
    # Mapping from Excel survey to tfidf_epn_69d column names
    MAPEO_CARRERAS = {
        '(RRA20) COMPUTACIÓN': 'Ingenieria En Ciencias De La Computacion',
        '(RRA20) AGROINDUSTRIA': 'Ingenieria Agroindustria',
        '(RRA20) ADMINISTRACIÓN DE EMPRESAS': 'Licenciatura Administracion De Empresas',
        '(RRA20) INGENIERÍA AMBIENTAL': 'Ingenieria Ambiental',
        '(RRA20) ECONOMÍA': 'Economia',
        'INGENIERIA EN CIENCIAS ECONOMICAS Y FINANCIERAS': 'Economia',
        '(RRA20) ELECTRICIDAD': 'Ingenieria En Electricidad',
        '(RRA20) ELECTRÓNICA Y AUTOMATIZACIÓN': 'Ingenieria En Electronica Y Automatizacion',
        '(RRA20) FÍSICA': 'Fisica',
        'FISICA': 'Fisica',
        '(RRA20) GEOLOGÍA': 'Ingenieria En Geologia',
        'INGENIERIA GEOLOGICA': 'Ingenieria En Geologia',
        '(RRA20) INGENIERÍA DE LA PRODUCCIÓN': 'Ingenieria De La Produccion',
        '(RRA20) MATEMÁTICA': 'Matematica',
        '(RRA20) MECÁNICA': 'Ingenieria En Mecanica',
        'INGENIERIA MECANICA': 'Ingenieria En Mecanica',
        '(RRA20) PETRÓLEOS': 'Ingenieria En Petroleos',
        '(RRA20) INGENIERÍA QUÍMICA': 'Ingenieria Quimica',
        '(RRA20) DESARROLLO DE SOFTWARE': 'Ingenieria En Software',
        '(RRA20) SOFTWARE': 'Ingenieria En Software',
        '(RRA20) TELECOMUNICACIONES': 'Ingenieria En Telecomunicaciones',
        '(RRA20) INGENIERÍA CIVIL': 'Ingenieria Civil'
    }
    
    # Mapping from academic career to job offers CSV
    CARRERA_TO_CSV = {
        'Ingenieria En Ciencias De La Computacion': 'todas_las_plataformas/Computación/Computación_Merged.csv',
        'Ingenieria Agroindustria': 'todas_las_plataformas/Agroindustria/Agroindustria_Merged.csv',
        'Licenciatura Administracion De Empresas': 'todas_las_plataformas/Administración_de_Empresas/Administración_de_Empresas_Merged.csv',
        'Ingenieria Ambiental': 'todas_las_plataformas/Ingeniería_Ambiental/Ingeniería_Ambiental_Merged.csv',
        'Economia': 'todas_las_plataformas/Economía/Economía_Merged.csv',
        'Ingenieria En Electricidad': 'todas_las_plataformas/Electricidad/Electricidad_Merged.csv',
        'Ingenieria En Electronica Y Automatizacion': 'todas_las_plataformas/Electrónica_y_Automatización/Electrónica_y_Automatización_Merged.csv',
        'Fisica': 'todas_las_plataformas/Física/Física_Merged.csv',
        'Ingenieria En Geologia': 'todas_las_plataformas/Geología/Geología_Merged.csv',
        'Ingenieria De La Produccion': 'todas_las_plataformas/Ingeniería_de_la_Producción/Ingeniería_de_la_Producción_Merged.csv',
        'Ingenieria En Materiales': 'todas_las_plataformas/Materiales/Materiales_Merged.csv',
        'Ingenieria En Mecanica': 'todas_las_plataformas/Mecánica/Mecánica_Merged.csv',
        'Ingenieria En Mecatronica': 'todas_las_plataformas/Mecatrónica/Mecatrónica_Merged.csv',
        'Ingenieria En Petroleos': 'todas_las_plataformas/Petróleos/Petróleos_Merged.csv',
        'Ingenieria Quimica': 'todas_las_plataformas/Ingeniería_Química/Ingeniería_Química_Merged.csv',
        'Ingenieria En Telecomunicaciones': 'todas_las_plataformas/Telecomunicaciones/Telecomunicaciones_Merged.csv',
        'Ingenieria Civil': 'todas_las_plataformas/Ingeniería_Civil/Ingeniería_Civil_Merged.csv',
        'Matematica': 'todas_las_plataformas/Matemática/Matemática_Merged.csv',
        'Matematica Aplicada': 'todas_las_plataformas/Matemática_Aplicada/Matemática_Aplicada_Merged.csv',
        'Ingenieria En Software': 'todas_las_plataformas/Software/Software_Merged.csv',
        'Ingenieria En Ciencias De Datos': 'todas_las_plataformas/Ciencia_de_Datos/Ciencia_de_Datos_Merged.csv',
        # Unificación: Ciencias De Datos E Inteligencia Artificial abarca dos fuentes
        'Ciencias De Datos E Inteligencia Artificial': [
            'todas_las_plataformas/Inteligencia_Artificial/Inteligencia_Artificial_Merged.csv',
            'todas_las_plataformas/Ciencia_de_Datos/Ciencia_de_Datos_Merged.csv'
        ],
        'Ingenieria En Sistemas De Informacion': 'todas_las_plataformas/Sistemas_de_Información/Sistemas_de_Información_Merged.csv',
    }
    
    # Soft skills labels (7 dimensions)
    SOFT_SKILLS_LABELS = [
        'Gestión',
        'Comunicación efectiva',
        'Liderazgo',
        'Trabajo en equipo',
        'Ética profesional',
        'Responsabilidad social',
        'Aprendizaje autónomo'
    ]
    
    @classmethod
    def map_career(cls, carrera_input: str) -> Optional[str]:
        """Map career from any format to tfidf_epn_69d format"""
        return cls.MAPEO_CARRERAS.get(carrera_input.strip())
    
    @classmethod
    def get_career_csv(cls, carrera_académica: str) -> Optional[str]:
        """Get CSV file path for job offers of a career"""
        return cls.CARRERA_TO_CSV.get(carrera_académica)
    
    @classmethod
    def get_available_careers(cls) -> list:
        """Get list of available academic careers"""
        return list(cls.CARRERA_TO_CSV.keys())
    
    @classmethod
    def get_available_careers_from_excel(cls) -> list:
        """Get list of career names as they appear in Excel"""
        return list(cls.MAPEO_CARRERAS.keys())
