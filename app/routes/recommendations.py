"""Recommendations API routes"""
from flask import Blueprint, request, jsonify
import os
import numpy as np
import traceback

from app.models import UserVectorizer, RecommendationEngine, CarreraMapper, DataManager
from app.utils import validate_request_data, ValidationError, success_response, error_response
from app.utils.ai_personalizer import AIPersonalizer

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')


@recommendations_bp.route('/predict', methods=['POST'])
def get_recommendations():
    """
    Get job recommendations for a student
    
    Request JSON:
    {
        "carrera": "Ingenieria En Ciencias De La Computacion",
        "asignaturas": "Python, Machine Learning, Bases de Datos",
        "soft_skills": [4, 5, 3, 4, 4, 3, 4],
        "top_n": 5
    }
    
    Response:
    {
        "success": true,
        "message": "Recomendaciones generadas exitosamente",
        "data": {
            "carrera": "Ingenieria En Ciencias De La Computacion",
            "num_recomendaciones": 5,
            "recomendaciones": [
                {
                    "rank": 1,
                    "similitud": 0.8523,
                    "cargo": "Senior Python Developer",
                    "descripcion": "...",
                    "eurace_skills": "...",
                    "skills": "..."
                },
                ...
            ]
        }
    }
    """
    try:
        # Get JSON data
        data = request.get_json() or {}
        
        # Validate request data
        try:
            carrera_académica, asignaturas, soft_skills, top_n = validate_request_data(data)
        except ValidationError as e:
            return error_response(str(e), status_code=400)
        # Optional: include alternative recommendations (lazy-load for speed)
        include_alt = bool(data.get('include_alt', False))
        
        # Initialize components
        vectorizer = UserVectorizer()
        recommender = RecommendationEngine()
        
        # Create student vector (76d)
        student_vector_76d = vectorizer.create_vector_76d(
            carrera_académica=carrera_académica,
            asignaturas_relevantes=asignaturas,
            soft_skills_1_to_5=soft_skills
        )
        
        if student_vector_76d is None:
            return error_response(
                f"No se pudo crear el vector para la carrera: {carrera_académica}",
                status_code=400
            )
        
        # Get recommendations (current soft skills)
        recomendaciones_df = recommender.get_recommendations(
            student_vector_76d=student_vector_76d,
            carrera_académica=carrera_académica,
            top_n=top_n
        )
        if recomendaciones_df is None:
            return error_response(
                "No se encontraron recomendaciones",
                status_code=200
            )

        # AI personalizer
        ai = AIPersonalizer()
        llm_used = ai.is_enabled()
        require_llm = bool(os.getenv('AI_PERSONALIZER_REQUIRE_LLM','').strip().lower() in {'1','true','yes'})
        # Si se requiere LLM y no está disponible, evitar las plantillas y avisar
        if require_llm and not llm_used:
            return error_response(
                "El personalizador con OpenAI está deshabilitado o no pudo inicializarse en este entorno. Revisa OPENAI_API_KEY/OPENAI_MODEL y conectividad.",
                status_code=503,
                details=ai.status_details()
            )

        # Enrich recommendations using a single AI call (batch) for speed
        recomendaciones = []
        cargos_iniciales = set()
        rec_items = []
        for _, row in recomendaciones_df.iterrows():
            rec = row.to_dict()
            cargos_iniciales.add(str(rec.get('cargo')))
            rec_items.append({
                'cargo': str(rec.get('cargo')),
                'descripcion': str(rec.get('descripcion')),
                'eurace_skills': str(rec.get('eurace_skills')),
                'skills': str(rec.get('skills')),
            })
        explicaciones = ai.personalize_batch(rec_items, carrera_académica, asignaturas, soft_skills)
        for idx, (_, row) in enumerate(recomendaciones_df.iterrows()):
            rec = row.to_dict()
            exp = explicaciones[idx] if idx < len(explicaciones) else ''
            if not exp:
                # Fallback por item si batch vino vacío
                exp = ai.personalize_description(
                    cargo=str(rec.get('cargo')), 
                    descripcion=str(rec.get('descripcion')), 
                    eurace_skills=str(rec.get('eurace_skills')), 
                    skills=str(rec.get('skills')), 
                    carrera=carrera_académica, 
                    asignaturas=asignaturas, 
                    soft_skills=soft_skills
                )
            rec['explicacion_ai'] = exp
            # Parámetros: ángulo y similitud coseno
            sim = float(rec.get('similitud', 0.0))
            ang = float(np.degrees(np.arccos(max(min(sim, 1.0), -1.0))))
            rec['cosine_similarity'] = sim
            rec['cosine_angle_deg'] = ang
            recomendaciones.append(rec)

        # Build an improved vector simulating better soft skills (only indices 69-75)
        improved_vector = student_vector_76d.copy()
        improved_vector[69:] = np.clip(improved_vector[69:] + 0.3, 0.0, 1.0)

        # Fetch alternative recommendations emphasizing improved soft skills
        alt_df = None
        if include_alt:
            alt_df = recommender.get_recommendations(
                student_vector_76d=improved_vector,
                carrera_académica=carrera_académica,
                top_n=top_n * 2
            )

        alt_recomendaciones = []
        if include_alt and alt_df is not None:
            alt_items = []
            alt_rows = []
            # Mapeo de keywords a etiquetas de soft skills
            soft_kw_map = {
                'gestion': 'Gestión',
                'comunicacion': 'Comunicación efectiva',
                'liderazgo': 'Liderazgo',
                'equipo': 'Trabajo en equipo',
                'etica': 'Ética profesional',
                'responsabilidad': 'Responsabilidad social',
                'aprendizaje': 'Aprendizaje autónomo'
            }
            # Obtener labels ordenadas por menor puntuación del usuario
            labels = CarreraMapper.SOFT_SKILLS_LABELS
            pairs = list(zip(labels, soft_skills))
            pairs_sorted = sorted(pairs, key=lambda x: x[1])

            for _, row in alt_df.iterrows():
                rd = row.to_dict()
                cargo = str(rd.get('cargo'))
                if cargo in cargos_iniciales:
                    continue
                eur = str(rd.get('eurace_skills', '')).lower()
                # Detectar habilidades relevantes en EURACE
                relevant = []
                for kw, lab in soft_kw_map.items():
                    if kw in eur:
                        relevant.append(lab)
                # Priorizar sugerir las de menor puntuación del usuario dentro de las relevantes
                suggest = []
                if relevant:
                    for lab, score in pairs_sorted:
                        if lab in relevant and score <= 3:
                            suggest.append(lab)
                        if len(suggest) >= 2:
                            break
                # Si no hay relevantes de baja puntuación, sugerir dos de las más bajas en general
                if not suggest:
                    suggest = [pairs_sorted[0][0]]
                    if len(pairs_sorted) > 1:
                        suggest.append(pairs_sorted[1][0])

                alt_items.append({
                    'cargo': cargo,
                    'descripcion': str(rd.get('descripcion')),
                    'eurace_skills': str(rd.get('eurace_skills')),
                    'skills': str(rd.get('skills')),
                    'suggest_soft': ', '.join(suggest)
                })
                alt_rows.append(rd)
                if len(alt_items) >= top_n:
                    break

            alt_explicaciones = ai.personalize_alt_batch(alt_items, carrera_académica, asignaturas, soft_skills)
            rank_counter = 1
            for i in range(len(alt_rows)):
                rec = alt_rows[i]
                exp = alt_explicaciones[i] if i < len(alt_explicaciones) else ''
                if not exp:
                    exp = ai.personalize_description(
                        cargo=str(rec.get('cargo')),
                        descripcion=str(rec.get('descripcion')),
                        eurace_skills=str(rec.get('eurace_skills')),
                        skills=str(rec.get('skills')),
                        carrera=carrera_académica,
                        asignaturas=asignaturas,
                        soft_skills=soft_skills
                    )
                rec['explicacion_ai'] = exp
                sim = float(rec.get('similitud', 0.0))
                ang = float(np.degrees(np.arccos(max(min(sim, 1.0), -1.0))))
                rec['cosine_similarity'] = sim
                rec['cosine_angle_deg'] = ang
                rec['rank'] = rank_counter
                alt_recomendaciones.append(rec)
                rank_counter += 1

        # Advice message about soft skills improvement
        consejo_mejora = ''
        if include_alt:
            consejo_mejora = ai.soft_skills_advice(
                carrera=carrera_académica,
                asignaturas=asignaturas,
                soft_skills=soft_skills
            )

        # Return combined payload
        payload = {
            'carrera': carrera_académica,
            'num_recomendaciones': len(recomendaciones),
            'recomendaciones': recomendaciones,
            'mejora_soft_skills_mensaje': consejo_mejora,
            'recomendaciones_mejorando_soft_skills': alt_recomendaciones,
            'include_alt': include_alt,
            'llm_used': llm_used
        }

        return success_response(
            data=payload,
            message="Recomendaciones generadas exitosamente"
        )
    
    except Exception as e:
        print(f"Error in get_recommendations: {str(e)}")
        print(traceback.format_exc())
        return error_response(
            "Error interno del servidor",
            status_code=500,
            details=str(e)
        )


@recommendations_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        data_manager = DataManager()
        is_ready = data_manager.is_ready()
        
        return success_response(
            data={
                'status': 'healthy' if is_ready else 'not_ready',
                'data_loaded': is_ready
            },
            message="Health check passed"
        )
    except Exception as e:
        return error_response(
            "Health check failed",
            status_code=503,
            details=str(e)
        )


@recommendations_bp.route('/careers', methods=['GET'])
def get_available_careers():
    """
    Get list of available careers
    
    Response:
    {
        "success": true,
        "message": "Success",
        "data": {
            "total": 22,
            "careers": [
                "Ingenieria En Ciencias De La Computacion",
                "Ingenieria En Software",
                ...
            ]
        }
    }
    """
    try:
        careers = CarreraMapper.get_available_careers()
        
        return success_response(
            data={
                'total': len(careers),
                'careers': sorted(careers)
            },
            message="Carreras obtenidas exitosamente"
        )
    except Exception as e:
        return error_response(
            "Error obteniendo carreras",
            status_code=500,
            details=str(e)
        )


@recommendations_bp.route('/soft-skills-labels', methods=['GET'])
def get_soft_skills_labels():
    """
    Get labels for soft skills dimensions
    
    Response:
    {
        "success": true,
        "message": "Success",
        "data": {
            "labels": ["Gestión", "Comunicación efectiva", ...]
        }
    }
    """
    try:
        labels = CarreraMapper.SOFT_SKILLS_LABELS
        
        return success_response(
            data={
                'labels': labels,
                'count': len(labels)
            },
            message="Soft skills labels obtenidos exitosamente"
        )
    except Exception as e:
        return error_response(
            "Error obteniendo soft skills labels",
            status_code=500,
            details=str(e)
        )


@recommendations_bp.route('/info', methods=['GET'])
def get_api_info():
    """
    Get API information
    
    Response:
    {
        "success": true,
        "message": "Success",
        "data": {
            "version": "1.0.0",
            "endpoints": [...],
            "features": [...]
        }
    }
    """
    try:
        # LLM status
        try:
            ai = AIPersonalizer()
            ai_status = ai.is_enabled()
            ai_diag = ai.status_details()
        except Exception:
            ai_status = False
            ai_diag = {'enabled': False}
        info = {
            'version': '1.0.0',
            'name': 'Sistema de Recomendación de Ofertas Laborales',
            'description': 'API que proporciona recomendaciones de ofertas laborales basadas en vectores de estudiantes',
            'features': [
                'Vectorización de usuarios (76 dimensiones)',
                'Personalización por asignaturas relevantes',
                'Evaluación de habilidades blandas',
                'Cálculo de similitud coseno con ofertas laborales',
                'Ranking de recomendaciones'
            ],
            'technical_skills_dimensions': 69,
            'soft_skills_dimensions': 7,
            'total_dimensions': 76,
            'available_careers_count': len(CarreraMapper.get_available_careers()),
            'llm_enabled': ai_status,
            'llm_required': bool(os.getenv('AI_PERSONALIZER_REQUIRE_LLM','').strip().lower() in {'1','true','yes'}),
            'openai_model': os.getenv('OPENAI_MODEL', ''),
            'llm_status_details': ai_diag
        }
        
        return success_response(data=info, message="API info retrieved successfully")
    except Exception as e:
        return error_response(
            "Error obteniendo información de API",
            status_code=500,
            details=str(e)
        )
