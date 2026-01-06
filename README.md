# Backend - Sistema de Recomendación de Ofertas Laborales

API REST desarrollado con Flask para proporcionar recomendaciones de ofertas laborales basadas en vectores de estudiantes (76 dimensiones).

## 📋 Tabla de Contenidos

- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Inicio Rápido](#inicio-rápido)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Endpoints de la API](#endpoints-de-la-api)
- [Flujo de Procesamiento](#flujo-de-procesamiento)
- [Modelos de Datos](#modelos-de-datos)

## 🏗️ Arquitectura

```
Backend (Flask)
├── app/
│   ├── models/
│   │   ├── data_manager.py       → Carga y gestión de datos procesados
│   │   ├── user_vectorizer.py    → Vectorización de usuarios (76d)
│   │   └── recommender.py        → Motor de recomendaciones
│   ├── routes/
│   │   └── recommendations.py    → Endpoints de la API
│   ├── utils/
│   │   ├── validation.py         → Validación de inputs
│   │   └── responses.py          → Formateo de respuestas
│   └── __init__.py               → Factory de Flask app
├── config.py                     → Configuración de la aplicación
├── run.py                        → Punto de entrada principal
└── requirements.txt              → Dependencias Python
```

## 📦 Requisitos

- Python 3.8+
- Archivo `datos_procesados.pkl` (generado por 01_Carga_Datos.ipynb)
- Carpeta `todas_las_plataformas/` con CSVs de ofertas
- Carpeta `carreras_epn/` con datos académicos

## 🚀 Instalación

### 1. Crear entorno virtual

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Verificar archivos necesarios

Asegúrate de que en el directorio padre (`../`) existan:
- `datos_procesados.pkl`
- `carreras_epn/carreras_epn.csv`
- `todas_las_plataformas/*/Merged.csv`

```bash
# Desde el directorio backend
ls ../datos_procesados.pkl
ls ../carreras_epn/carreras_epn.csv
```

## ⚡ Inicio Rápido

### Ejecutar servidor en desarrollo

```bash
python run.py
```

Servidor disponible en: `http://localhost:5000`

### Ejemplo de request con curl

```bash
curl -X POST http://localhost:5000/api/recommendations/predict \
  -H "Content-Type: application/json" \
  -d '{
    "carrera": "Ingenieria En Ciencias De La Computacion",
    "asignaturas": "Python, Machine Learning, Bases de Datos",
    "soft_skills": [4, 5, 3, 4, 4, 3, 4],
    "top_n": 5
  }'
```

### Ejemplo con Python requests

```python
import requests
import json

url = "http://localhost:5000/api/recommendations/predict"

data = {
    "carrera": "Ingenieria En Ciencias De La Computacion",
    "asignaturas": "Python, Machine Learning, Bases de Datos",
    "soft_skills": [4, 5, 3, 4, 4, 3, 4],
    "top_n": 5
}

response = requests.post(url, json=data)
print(json.dumps(response.json(), indent=2))
```

## 📁 Estructura del Proyecto

### Carpeta `app/models/`

#### `data_manager.py`
- **DataManager**: Singleton que carga y cachea datos procesados
- **CarreraMapper**: Mapea nombres de carreras entre diferentes formatos

```python
from app.models import DataManager, CarreraMapper

# Obtener datos
dm = DataManager()
habilidades = dm.habilidades  # Lista de 180+ habilidades
grupos = dm.grupos_bge_ngram  # 69 grupos de habilidades

# Mapear carrera
carrera_academica = CarreraMapper.map_career("(RRA20) COMPUTACIÓN")
csv_path = CarreraMapper.get_career_csv(carrera_academica)
```

#### `user_vectorizer.py`
- **UserVectorizer**: Transforma datos de usuario en vector 76d

```python
from app.models import UserVectorizer

vectorizer = UserVectorizer()

# Crear vector 76d
vector_76d = vectorizer.create_vector_76d(
    carrera_académica="Ingenieria En Ciencias De La Computacion",
    asignaturas_relevantes="Python, Machine Learning",
    soft_skills_1_to_5=[4, 5, 3, 4, 4, 3, 4]
)

# Info del vector
info = vectorizer.get_vector_info(vector_76d)
print(f"Vector técnico medio: {info['technical_mean']:.3f}")
print(f"Vector soft skills: {info['soft_skills_vector']}")
```

#### `recommender.py`
- **RecommendationEngine**: Genera recomendaciones basadas en similitud coseno

```python
from app.models import RecommendationEngine

engine = RecommendationEngine()

# Obtener recomendaciones
recomendaciones = engine.get_recommendations(
    student_vector_76d=vector_76d,
    carrera_académica="Ingenieria En Ciencias De La Computacion",
    top_n=5
)

# Usar caché para mejorar performance
engine.clear_cache()
```

### Carpeta `app/utils/`

#### `validation.py`
- Validación de inputs
- Mapeo de carreras
- Validación de habilidades blandas

```python
from app.utils import validate_request_data, ValidationError

try:
    carrera, asignaturas, soft_skills, top_n = validate_request_data(data)
except ValidationError as e:
    print(f"Error: {e}")
```

#### `responses.py`
- Formateo de respuestas
- Manejo de errores

```python
from app.utils import success_response, error_response

# Respuesta exitosa
return success_response(
    data={'key': 'value'},
    message="Operación exitosa"
)

# Respuesta de error
return error_response(
    "Error al procesar",
    status_code=400,
    details="Detalles del error"
)
```

## 🔌 Endpoints de la API

### 1. Obtener Recomendaciones (Principal)

**POST** `/api/recommendations/predict`

Calcula recomendaciones de ofertas laborales para un estudiante.

**Request:**
```json
{
  "carrera": "Ingenieria En Ciencias De La Computacion",
  "asignaturas": "Python, Machine Learning, Bases de Datos",
  "soft_skills": [4, 5, 3, 4, 4, 3, 4],
  "top_n": 5
}
```

**Parámetros:**
- `carrera` (requerido): Nombre de la carrera académica
- `asignaturas` (opcional): Asignaturas relevantes separadas por comas
- `soft_skills` (requerido): Array de 7 valores (1-5) para habilidades blandas
- `top_n` (opcional): Número de recomendaciones (1-50, default: 5)

**Response:**
```json
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
        "descripcion": "Buscamos un senior con experiencia en...",
        "eurace_skills": "Programming, Problem solving",
        "skills": "Python, Django, PostgreSQL, Docker..."
      },
      ...
    ]
  }
}
```

### 2. Verificar Salud de la API

**GET** `/api/recommendations/health`

Verifica que los datos estén cargados correctamente.

**Response:**
```json
{
  "success": true,
  "message": "Health check passed",
  "data": {
    "status": "healthy",
    "data_loaded": true
  }
}
```

### 3. Obtener Carreras Disponibles

**GET** `/api/recommendations/careers`

Lista todas las carreras académicas disponibles.

**Response:**
```json
{
  "success": true,
  "message": "Carreras obtenidas exitosamente",
  "data": {
    "total": 22,
    "careers": [
      "Ingenieria Civil",
      "Ingenieria De La Produccion",
      "Ingenieria En Ciencias De La Computacion",
      ...
    ]
  }
}
```

### 4. Obtener Etiquetas de Habilidades Blandas

**GET** `/api/recommendations/soft-skills-labels`

Retorna las 7 etiquetas de habilidades blandas.

**Response:**
```json
{
  "success": true,
  "message": "Soft skills labels obtenidos exitosamente",
  "data": {
    "labels": [
      "Gestión",
      "Comunicación efectiva",
      "Liderazgo",
      "Trabajo en equipo",
      "Ética profesional",
      "Responsabilidad social",
      "Aprendizaje autónomo"
    ],
    "count": 7
  }
}
```

### 5. Información de la API

**GET** `/api/recommendations/info`

Retorna información y características de la API.

**Response:**
```json
{
  "success": true,
  "message": "API info retrieved successfully",
  "data": {
    "version": "1.0.0",
    "name": "Sistema de Recomendación de Ofertas Laborales",
    "technical_skills_dimensions": 69,
    "soft_skills_dimensions": 7,
    "total_dimensions": 76,
    "available_careers_count": 22
  }
}
```

## 🔄 Flujo de Procesamiento

### 1. Recepción de datos

El usuario envía:
- Carrera académica
- Asignaturas relevantes (opcional)
- Auto-evaluación en 7 habilidades blandas (1-5)

### 2. Validación

```
✓ Carrera existe en mapeo
✓ Asignaturas: texto libre (máx 1000 chars)
✓ Soft skills: 7 valores entre 1-5
✓ top_n: entre 1-50
```

### 3. Vectorización

```
Vector Académico Base (69d)
  ↓
Personalización por Asignaturas (boost a 0.99)
  ↓
+ Habilidades Blandas (7d, normalizadas a [0,1])
  ↓
Vector Estudiante Final (76d)
```

### 4. Búsqueda de Recomendaciones

```
Cargar ofertas laborales de la carrera (CSV)
  ↓
Vectorizar ofertas a 76d (69d técnico + 7d soft skills)
  ↓
Calcular similitud coseno
  ↓
Ordenar por similitud descendente
  ↓
Eliminar duplicados por título de cargo
  ↓
Retornar Top N
```

## 📊 Modelos de Datos

### Vector de Estudiante (76 dimensiones)

```
[0-68]   → Habilidades Técnicas (69d)
          - Agrupadas en 69 dimensiones por similitud
          - Valores entre 0-1 (TF-IDF)
          - Boosteadas a 0.99 si se menciona asignatura relevante

[69-75]  → Habilidades Blandas (7d)
          69: Gestión
          70: Comunicación efectiva
          71: Liderazgo
          72: Trabajo en equipo
          73: Ética profesional
          74: Responsabilidad social
          75: Aprendizaje autónomo
          Valores normalizados de 1-5 a 0-1
```

### Recomendación

```python
{
    'rank': int,              # Posición en ranking
    'similitud': float,       # Similitud coseno 0-1
    'cargo': str,             # Título del trabajo
    'descripcion': str,       # Primeros 100 caracteres
    'eurace_skills': str,     # Skills requeridas
    'skills': str             # Detalles técnicos
}
```

## 🔍 Configuración y Variables de Entorno

### Archivo `.env` (opcional)

```
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### Configuración en `config.py`

- `DEBUG`: Habilitar modo debug
- `CORS_ORIGINS`: Orígenes permitidos
- `MAX_RECOMMENDATIONS`: Máximo de recomendaciones
- `DATA_DIR`: Ruta a datos procesados

### Integración con OpenAI (opcional)

Si defines `OPENAI_API_KEY` y `OPENAI_MODEL`, el backend usará la API de OpenAI para:
- Redactar un resumen claro de cada oferta y por qué encaja contigo (usando asignaturas, EURACE y skills).
- Añadir una sección de “Oportunidades si mejoras tus habilidades blandas” con explicaciones.

Si no configuras estas variables, el sistema usa un modo heurístico rápido y determinístico.

## 📈 Performance

- **Carga de datos**: ~5-10 segundos (una vez al iniciar)
- **Vectorización de usuario**: ~200ms
- **Búsqueda de recomendaciones**: ~500ms-1s (primera vez)
- **Búsqueda subsecuentes**: ~100-200ms (caché)

## 🐛 Troubleshooting

### Error: "datos_procesados.pkl not found"

```bash
# Verificar que estás en el directorio correcto
cd backend

# Confirmar que el archivo existe
ls ../datos_procesados.pkl
```

### Error: "Career not found"

```bash
# Obtener carreras disponibles
curl http://localhost:5000/api/recommendations/careers

# Usar exactamente el nombre retornado
```

### Memory Usage Alto

```python
# Limpiar caché de ofertas
from app.models import RecommendationEngine
engine = RecommendationEngine()
engine.clear_cache()
```

## 📚 Referencias

- [Documentación Análisis Completo](../ANALISIS_FLUJO_COMPLETO.md)
- [Notebook 01: Carga y Procesamiento](../01_Carga_Datos.ipynb)
- [Notebook 08: Sistema de Recomendación](../08_Sistema_Recomendacion.ipynb)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Scikit-learn](https://scikit-learn.org/)

---

**Versión**: 1.0.0  
**Último actualizado**: Diciembre 2025
