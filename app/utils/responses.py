"""Error handling and response formatting"""
from flask import jsonify
from typing import Dict, Any


class APIError(Exception):
    """Base API error"""
    def __init__(self, message: str, status_code: int = 400, details: str = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error"""
    def __init__(self, message: str, details: str = None):
        super().__init__(message, status_code=400, details=details)


class NotFoundError(APIError):
    """Resource not found error"""
    def __init__(self, message: str, details: str = None):
        super().__init__(message, status_code=404, details=details)


class ServerError(APIError):
    """Server error"""
    def __init__(self, message: str, details: str = None):
        super().__init__(message, status_code=500, details=details)


def success_response(data: Any, message: str = "Success", status_code: int = 200) -> tuple:
    """
    Create a success response
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    return jsonify({
        'success': True,
        'message': message,
        'data': data
    }), status_code


def error_response(message: str, status_code: int = 400, details: str = None) -> tuple:
    """
    Create an error response
    
    Args:
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'success': False,
        'message': message
    }
    
    if details:
        response['details'] = details
    
    return jsonify(response), status_code


def handle_api_error(error: APIError) -> tuple:
    """
    Handle API error and return appropriate response
    
    Args:
        error: APIError instance
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    return error_response(
        message=error.message,
        status_code=error.status_code,
        details=error.details
    )


def format_recommendation(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a single recommendation for response
    
    Args:
        rec: Raw recommendation dictionary
        
    Returns:
        Formatted recommendation
    """
    return {
        'rank': rec.get('rank'),
        'similitud': round(rec.get('similitud', 0), 4),
        'cargo': rec.get('cargo'),
        'descripcion': rec.get('descripcion'),
        'eurace_skills': rec.get('eurace_skills'),
        'skills': rec.get('skills')
    }


def format_recommendations_response(recommendations_df, carrera: str) -> Dict[str, Any]:
    """
    Format recommendations DataFrame for API response
    
    Args:
        recommendations_df: Pandas DataFrame with recommendations
        carrera: Career name
        
    Returns:
        Formatted response dictionary
    """
    if recommendations_df is None or recommendations_df.empty:
        return {
            'carrera': carrera,
            'num_recomendaciones': 0,
            'recomendaciones': [],
            'mensaje': 'No hay ofertas disponibles para esta carrera'
        }
    
    recomendaciones = [format_recommendation(row.to_dict()) for _, row in recommendations_df.iterrows()]
    
    return {
        'carrera': carrera,
        'num_recomendaciones': len(recomendaciones),
        'recomendaciones': recomendaciones
    }
