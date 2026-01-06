"""Input validation utilities"""
from typing import List, Tuple, Optional
from app.models.data_manager import CarreraMapper


class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_carrera(carrera: str) -> str:
    """
    Validate and map career input
    
    Args:
        carrera: Career name or ID
        
    Returns:
        Validated career name in tfidf_epn_69d format
        
    Raises:
        ValidationError: If career is invalid
    """
    if not isinstance(carrera, str) or not carrera.strip():
        raise ValidationError("Carrera must be a non-empty string")
    
    carrera = carrera.strip()
    
    # Try direct mapping first
    mapped_carrera = CarreraMapper.map_career(carrera)
    if mapped_carrera:
        return mapped_carrera
    
    # Try case-insensitive matching with available careers
    available = CarreraMapper.get_available_careers()
    carrera_lower = carrera.lower()
    
    for available_carrera in available:
        if available_carrera.lower() == carrera_lower:
            return available_carrera
    
    raise ValidationError(
        f"Carrera '{carrera}' no válida. Carreras disponibles: {', '.join(available[:5])}..."
    )


def validate_asignaturas(asignaturas: str) -> str:
    """
    Validate asignaturas input
    
    Args:
        asignaturas: Comma-separated list of subjects
        
    Returns:
        Validated asignaturas string
        
    Raises:
        ValidationError: If input is invalid
    """
    if not isinstance(asignaturas, str):
        raise ValidationError("Asignaturas must be a string")
    
    asignaturas = asignaturas.strip()
    
    # Asignaturas can be empty (optional personalization)
    if not asignaturas:
        return ""
    
    # Just check that it's not too long
    if len(asignaturas) > 1000:
        raise ValidationError("Asignaturas text is too long (max 1000 characters)")
    
    return asignaturas


def validate_soft_skills(soft_skills: List[int]) -> List[int]:
    """
    Validate soft skills ratings
    
    Args:
        soft_skills: List of 7 ratings (1-5)
        
    Returns:
        Validated list of soft skills
        
    Raises:
        ValidationError: If input is invalid
    """
    if not isinstance(soft_skills, list):
        raise ValidationError("Soft skills must be a list")
    
    if len(soft_skills) != 7:
        raise ValidationError(f"Soft skills must have exactly 7 values, got {len(soft_skills)}")
    
    # Validate each rating
    for i, rating in enumerate(soft_skills):
        if not isinstance(rating, (int, float)):
            raise ValidationError(f"Soft skill {i} must be a number, got {type(rating)}")
        
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            raise ValidationError(f"Soft skill {i} must be between 1 and 5, got {rating_int}")
        
        soft_skills[i] = rating_int
    
    return soft_skills


def validate_top_n(top_n: Optional[int]) -> int:
    """
    Validate number of recommendations
    
    Args:
        top_n: Number of recommendations
        
    Returns:
        Validated top_n value
        
    Raises:
        ValidationError: If input is invalid
    """
    if top_n is None:
        return 5
    
    if not isinstance(top_n, int):
        raise ValidationError("top_n must be an integer")
    
    if top_n < 1 or top_n > 50:
        raise ValidationError("top_n must be between 1 and 50")
    
    return top_n


def validate_request_data(data: dict) -> Tuple[str, str, List[int], int]:
    """
    Validate complete request data
    
    Args:
        data: Dictionary with keys: carrera, asignaturas, soft_skills, top_n (optional)
        
    Returns:
        Tuple of (carrera, asignaturas, soft_skills, top_n)
        
    Raises:
        ValidationError: If any field is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Request data must be a dictionary")
    
    # Validate required fields
    if 'carrera' not in data:
        raise ValidationError("Missing required field: carrera")
    
    if 'soft_skills' not in data:
        raise ValidationError("Missing required field: soft_skills")
    
    # Validate carrera
    carrera = validate_carrera(data['carrera'])
    
    # Validate asignaturas (optional, default to empty string)
    asignaturas = validate_asignaturas(data.get('asignaturas', ''))
    
    # Validate soft_skills
    soft_skills = validate_soft_skills(data['soft_skills'])
    
    # Validate top_n (optional)
    top_n = validate_top_n(data.get('top_n'))
    
    return carrera, asignaturas, soft_skills, top_n
