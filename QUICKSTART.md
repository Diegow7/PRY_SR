# 🚀 Guía de Inicio Rápido - Backend Flask

## Paso 1: Preparar el Entorno

### 1.1 Verificar archivos necesarios

El backend requiere que estos archivos existan en el directorio padre:

```
d:\Uni\RI\TIC_Pry1\
├── datos_procesados.pkl               ← REQUERIDO (desde 01_Carga_Datos.ipynb)
├── carreras_epn/
│   └── carreras_epn.csv               ← REQUERIDO
├── todas_las_plataformas/
│   ├── Computación/Computación_Merged.csv
│   ├── Software/Software_Merged.csv
│   ├── ... (otras carreras)
└── backend/                           ← TÚ ESTÁS AQUÍ
    ├── run.py
    ├── requirements.txt
    └── ...
```

**Acción requerida**: Ejecuta primero los notebooks en este orden:
1. `01_Carga_Datos.ipynb` - Genera `datos_procesados.pkl`
2. Luego puedes usar el backend

### 1.2 Crear entorno virtual

```bash
# Ir a la carpeta backend
cd d:\Uni\RI\TIC_Pry1\backend

# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Activar (Mac/Linux)
source venv/bin/activate
```

### 1.3 Instalar dependencias

```bash
pip install -r requirements.txt
```

**Tiempo estimado**: 3-5 minutos (depende de internet)

## Paso 2: Verificar Configuración

### 2.1 Verificar que los datos existen

```bash
# Desde carpeta backend
python -c "from app.models import DataManager; dm = DataManager(); print('✓ Datos cargados!' if dm.is_ready() else '✗ Error')"
```

### 2.2 Crear archivo `.env` (opcional)

```bash
# Copiar ejemplo
copy .env.example .env

# O en Linux/Mac
cp .env.example .env
```

## Paso 3: Ejecutar el Servidor

```bash
python run.py
```

**Esperado en consola**:
```
✓ Datos procesados cargados desde ...
Starting Flask app in development mode...
Server running on http://localhost:5000
API documentation available at /api/recommendations/info
 * Running on http://0.0.0.0:5000
```

## Paso 4: Probar la API

### 4.1 Verificar salud (en navegador o terminal)

```bash
curl http://localhost:5000/api/recommendations/health
```

**Respuesta esperada**:
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

### 4.2 Obtener carreras disponibles

```bash
curl http://localhost:5000/api/recommendations/careers
```

### 4.3 Obtener etiquetas de soft skills

```bash
curl http://localhost:5000/api/recommendations/soft-skills-labels
```

### 4.4 Generar Recomendaciones (Endpoint Principal)

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

**Respuesta esperada**: Array con 5 ofertas recomendadas ordenadas por similitud

## Paso 5: Usar desde Aplicación Frontend (Opcional)

### Con Python

```python
import requests
import json

# Solicitar recomendaciones
response = requests.post('http://localhost:5000/api/recommendations/predict', json={
    'carrera': 'Ingenieria En Ciencias De La Computacion',
    'asignaturas': 'Python, Machine Learning',
    'soft_skills': [4, 5, 3, 4, 4, 3, 4]
})

print(response.json())
```

### Con JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:5000/api/recommendations/predict', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    carrera: 'Ingenieria En Ciencias De La Computacion',
    asignaturas: 'Python, Machine Learning',
    soft_skills: [4, 5, 3, 4, 4, 3, 4]
  })
});

const data = await response.json();
console.log(data);
```

### Con Node.js/Axios

```javascript
const axios = require('axios');

axios.post('http://localhost:5000/api/recommendations/predict', {
  carrera: 'Ingenieria En Ciencias De La Computacion',
  asignaturas: 'Python, Machine Learning',
  soft_skills: [4, 5, 3, 4, 4, 3, 4]
})
.then(res => console.log(res.data))
.catch(err => console.error(err));
```

## 📋 Estructura de Request/Response

### Request JSON

```json
{
  "carrera": "string (requerido)",
  "asignaturas": "string (opcional, separadas por comas)",
  "soft_skills": [1-5, 1-5, 1-5, 1-5, 1-5, 1-5, 1-5],
  "top_n": "integer (opcional, 1-50, default: 5)"
}
```

### Response JSON (Exitoso)

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
        "similitud": 0.8234,
        "cargo": "Senior Python Developer",
        "descripcion": "Buscamos un senior con experiencia en...",
        "eurace_skills": "Programming, Leadership",
        "skills": "Python, Django, PostgreSQL, Docker, Kubernetes..."
      },
      ...
    ]
  }
}
```

### Response JSON (Error)

```json
{
  "success": false,
  "message": "Carrera 'InvalidoName' no válida. Carreras disponibles: ...",
  "status_code": 400
}
```

## 🎯 Parámetros Detallados

### carrera (Requerido)

Nombre de la carrera académica. Valores válidos:

```
- Ingenieria En Ciencias De La Computacion
- Ingenieria En Software
- Ciencias De Datos E Inteligencia Artificial
- Ingenieria Civil
- Ingenieria En Electricidad
- ... (y más)
```

**Acción**: Usa `/api/recommendations/careers` para ver la lista completa

### asignaturas (Opcional)

Asignaturas más relevantes del estudiante, separadas por comas:

```
"Python, Algoritmos, Bases de Datos"
"Machine Learning, Deep Learning, Statistics"
```

**Efecto**: Incrementa la ponderación (a 0.99) de habilidades técnicas relacionadas

### soft_skills (Requerido)

Auto-evaluación en 7 dimensiones (escala 1-5):

```json
[
  4,  // Gestión
  5,  // Comunicación efectiva
  3,  // Liderazgo
  4,  // Trabajo en equipo
  4,  // Ética profesional
  3,  // Responsabilidad social
  4   // Aprendizaje autónomo
]
```

**Rango**: Cada valor debe estar entre 1 (mínimo) y 5 (máximo)

### top_n (Opcional, default: 5)

Número de recomendaciones a retornar

```
"top_n": 5   // Rango: 1-50
```

## 🔍 Ejemplos de Uso

### Ejemplo 1: Ingeniero de Software Junior

```bash
curl -X POST http://localhost:5000/api/recommendations/predict \
  -H "Content-Type: application/json" \
  -d '{
    "carrera": "Ingenieria En Software",
    "asignaturas": "Java, Spring Boot, React, Git",
    "soft_skills": [3, 4, 2, 4, 4, 3, 5],
    "top_n": 5
  }'
```

### Ejemplo 2: Científico de Datos Senior

```bash
curl -X POST http://localhost:5000/api/recommendations/predict \
  -H "Content-Type: application/json" \
  -d '{
    "carrera": "Ciencias De Datos E Inteligencia Artificial",
    "asignaturas": "Machine Learning, Python, TensorFlow, Deep Learning, Statistics",
    "soft_skills": [5, 5, 4, 5, 5, 4, 5],
    "top_n": 10
  }'
```

### Ejemplo 3: Ingeniero Civil

```bash
curl -X POST http://localhost:5000/api/recommendations/predict \
  -H "Content-Type: application/json" \
  -d '{
    "carrera": "Ingenieria Civil",
    "asignaturas": "Estructuras, AutoCAD, Hormigón Armado",
    "soft_skills": [4, 3, 3, 4, 4, 4, 3],
    "top_n": 5
  }'
```

## 🐛 Troubleshooting

### Error 1: "ModuleNotFoundError: No module named 'app'"

```bash
# Solución: Asegúrate de estar en la carpeta backend
pwd  # Verificar ubicación
cd d:\Uni\RI\TIC_Pry1\backend
python run.py
```

### Error 2: "datos_procesados.pkl not found"

```bash
# Solución: El archivo debe estar en el padre de backend
# Primero ejecuta: 01_Carga_Datos.ipynb
# Luego verifica:
ls ../datos_procesados.pkl
```

### Error 3: "Carrera no válida"

```bash
# Solución: Obtén la lista de carreras válidas
curl http://localhost:5000/api/recommendations/careers

# Usa el nombre exacto de la respuesta
```

### Error 4: "Port 5000 already in use"

```bash
# Solución 1: Usar otro puerto
FLASK_PORT=5001 python run.py

# Solución 2: Matar el proceso en el puerto
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

## 📊 Monitoreo y Debugging

### Ver logs detallados

```bash
# Activar debug en consola
export FLASK_DEBUG=1  # Linux/Mac
set FLASK_DEBUG=1     # Windows
python run.py
```

### Verificar carga de datos

```python
from app.models import DataManager, CarreraMapper

dm = DataManager()
print("Habilidades:", len(dm.habilidades))
print("Grupos:", len(dm.grupos_bge_ngram))
print("Carreras disponibles:", len(CarreraMapper.get_available_careers()))
```

### Profiler de performance

```python
import time
from app.models import UserVectorizer, RecommendationEngine

start = time.time()

vectorizer = UserVectorizer()
vector = vectorizer.create_vector_76d(...)

end = time.time()
print(f"Vectorización: {(end-start)*1000:.2f}ms")
```

## ✅ Checklist de Configuración

- [ ] Archivo `datos_procesados.pkl` existe
- [ ] Carpeta `todas_las_plataformas` existe con CSVs
- [ ] Carpeta `carreras_epn` existe con CSV
- [ ] Virtual environment activado
- [ ] Dependencias instaladas (`pip list`)
- [ ] Servidor ejecutándose (`http://localhost:5000`)
- [ ] Health check responde (`/api/recommendations/health`)
- [ ] CORS configurado correctamente para frontend
- [ ] `.env` file creado (opcional)

## 📚 Documentación Completa

- [README.md](./README.md) - Documentación técnica completa
- [Análisis Flujo](../ANALISIS_FLUJO_COMPLETO.md) - Explicación del procesamiento

---

**¡Listo para usar!** 🎉

Si tienes problemas, revisa la sección Troubleshooting o consulta la documentación técnica.
