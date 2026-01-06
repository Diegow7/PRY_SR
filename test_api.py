"""
Test Script - Backend API
Ejemplos de uso del backend Flask
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:5000/api/recommendations"

# Colores para output
GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
END = '\033[0m'


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{BLUE}{'='*80}{END}")
    print(f"{BLUE}{title.center(80)}{END}")
    print(f"{BLUE}{'='*80}{END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✓ {text}{END}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}✗ {text}{END}")


def print_json(data: Dict[str, Any], indent: int = 2):
    """Print formatted JSON"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def test_health_check():
    """Test 1: Health check"""
    print_header("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        
        if data['success'] and response.status_code == 200:
            print_success("API está saludable")
            print(f"Estado: {data['data']['status']}")
            print(f"Datos cargados: {data['data']['data_loaded']}")
        else:
            print_error("Health check falló")
    except Exception as e:
        print_error(f"Error: {e}")


def test_get_careers():
    """Test 2: Get available careers"""
    print_header("TEST 2: Carreras Disponibles")
    
    try:
        response = requests.get(f"{BASE_URL}/careers")
        data = response.json()
        
        if data['success']:
            careers = data['data']['careers']
            print_success(f"Total de carreras: {len(careers)}")
            print("\nPrimeras 10 carreras:")
            for i, career in enumerate(careers[:10], 1):
                print(f"  {i:2d}. {career}")
        else:
            print_error("No se pudieron obtener las carreras")
    except Exception as e:
        print_error(f"Error: {e}")


def test_get_soft_skills_labels():
    """Test 3: Get soft skills labels"""
    print_header("TEST 3: Etiquetas de Habilidades Blandas")
    
    try:
        response = requests.get(f"{BASE_URL}/soft-skills-labels")
        data = response.json()
        
        if data['success']:
            labels = data['data']['labels']
            print_success(f"Total de habilidades blandas: {len(labels)}")
            print("\nDimensiones de soft skills:")
            for i, label in enumerate(labels, 69):
                print(f"  [{i}] {label}")
        else:
            print_error("No se pudieron obtener las etiquetas")
    except Exception as e:
        print_error(f"Error: {e}")


def test_api_info():
    """Test 4: Get API info"""
    print_header("TEST 4: Información de la API")
    
    try:
        response = requests.get(f"{BASE_URL}/info")
        data = response.json()
        
        if data['success']:
            info = data['data']
            print_success("Información de API obtenida")
            print(f"Versión: {info['version']}")
            print(f"Nombre: {info['name']}")
            print(f"Dimensiones técnicas: {info['technical_skills_dimensions']}")
            print(f"Dimensiones soft skills: {info['soft_skills_dimensions']}")
            print(f"Total: {info['total_dimensions']}")
            print(f"Carreras disponibles: {info['available_careers_count']}")
        else:
            print_error("No se pudo obtener información de API")
    except Exception as e:
        print_error(f"Error: {e}")


def test_prediction_example1():
    """Test 5: Prediction - Ingeniero de Software"""
    print_header("TEST 5: Recomendaciones - Ingeniero de Software")
    
    payload = {
        "carrera": "Ingenieria En Software",
        "asignaturas": "Java, Spring Boot, React, REST APIs, Git, Docker",
        "soft_skills": [3, 4, 2, 4, 4, 3, 5],  # Liderazgo bajo, Aprendizaje alto
        "top_n": 5
    }
    
    print("Request:")
    print(f"  Carrera: {payload['carrera']}")
    print(f"  Asignaturas: {payload['asignaturas']}")
    print(f"  Soft Skills: {payload['soft_skills']}")
    print(f"  Top N: {payload['top_n']}\n")
    
    try:
        response = requests.post(f"{BASE_URL}/predict", json=payload)
        data = response.json()
        
        if data['success']:
            print_success("Recomendaciones obtenidas")
            resultado = data['data']
            print(f"\nCarrera: {resultado['carrera']}")
            print(f"Recomendaciones: {resultado['num_recomendaciones']}\n")
            
            for rec in resultado['recomendaciones']:
                print(f"  Rank {rec['rank']}: {rec['cargo']}")
                print(f"    Similitud: {rec['similitud']:.4f}")
                print(f"    Descripción: {rec['descripcion'][:60]}...")
                print()
        else:
            print_error(f"Error: {data['message']}")
    except Exception as e:
        print_error(f"Error: {e}")


def test_prediction_example2():
    """Test 6: Prediction - Científico de Datos"""
    print_header("TEST 6: Recomendaciones - Científico de Datos")
    
    payload = {
        "carrera": "Ciencias De Datos E Inteligencia Artificial",
        "asignaturas": "Machine Learning, Python, TensorFlow, Deep Learning, Statistics, SQL",
        "soft_skills": [5, 5, 4, 5, 5, 4, 5],  # All high (Senior level)
        "top_n": 5
    }
    
    print("Request:")
    print(f"  Carrera: {payload['carrera']}")
    print(f"  Asignaturas: {payload['asignaturas']}")
    print(f"  Soft Skills: {payload['soft_skills']}")
    print(f"  Top N: {payload['top_n']}\n")
    
    try:
        response = requests.post(f"{BASE_URL}/predict", json=payload)
        data = response.json()
        
        if data['success']:
            print_success("Recomendaciones obtenidas")
            resultado = data['data']
            print(f"\nCarrera: {resultado['carrera']}")
            print(f"Recomendaciones: {resultado['num_recomendaciones']}\n")
            
            for rec in resultado['recomendaciones'][:3]:  # Show top 3
                print(f"  Rank {rec['rank']}: {rec['cargo']}")
                print(f"    Similitud: {rec['similitud']:.4f}")
                print(f"    Skills: {rec['skills'][:60]}...")
                print()
        else:
            print_error(f"Error: {data['message']}")
    except Exception as e:
        print_error(f"Error: {e}")


def test_prediction_example3():
    """Test 7: Prediction - Ingeniero Civil"""
    print_header("TEST 7: Recomendaciones - Ingeniero Civil")
    
    payload = {
        "carrera": "Ingenieria Civil",
        "asignaturas": "Estructuras, AutoCAD, Hormigón Armado, Topografía",
        "soft_skills": [4, 3, 3, 4, 4, 4, 3],
        "top_n": 3
    }
    
    print("Request:")
    print(f"  Carrera: {payload['carrera']}")
    print(f"  Asignaturas: {payload['asignaturas']}")
    print(f"  Soft Skills: {payload['soft_skills']}")
    print(f"  Top N: {payload['top_n']}\n")
    
    try:
        response = requests.post(f"{BASE_URL}/predict", json=payload)
        data = response.json()
        
        if data['success']:
            print_success("Recomendaciones obtenidas")
            resultado = data['data']
            print(f"\nCarrera: {resultado['carrera']}")
            print(f"Recomendaciones: {resultado['num_recomendaciones']}\n")
            
            for rec in resultado['recomendaciones']:
                print(f"  Rank {rec['rank']}: {rec['cargo']}")
                print(f"    Similitud: {rec['similitud']:.4f}")
                print()
        else:
            print_error(f"Error: {data['message']}")
    except Exception as e:
        print_error(f"Error: {e}")


def test_error_handling():
    """Test 8: Error handling"""
    print_header("TEST 8: Manejo de Errores")
    
    # Test 8a: Invalid career
    print("\n[8a] Carrera inválida:")
    try:
        response = requests.post(f"{BASE_URL}/predict", json={
            "carrera": "Carrera Inexistente",
            "soft_skills": [1, 1, 1, 1, 1, 1, 1]
        })
        data = response.json()
        if not data['success']:
            print_success(f"Error capturado: {data['message'][:60]}...")
        else:
            print_error("Se debería haber producido un error")
    except Exception as e:
        print_error(f"Error: {e}")
    
    # Test 8b: Invalid soft skills
    print("\n[8b] Soft skills inválidos (6 en lugar de 7):")
    try:
        response = requests.post(f"{BASE_URL}/predict", json={
            "carrera": "Ingenieria En Software",
            "soft_skills": [1, 1, 1, 1, 1, 1]  # Solo 6
        })
        data = response.json()
        if not data['success']:
            print_success(f"Error capturado: {data['message']}")
        else:
            print_error("Se debería haber producido un error")
    except Exception as e:
        print_error(f"Error: {e}")
    
    # Test 8c: Invalid soft skill value
    print("\n[8c] Valor de soft skill fuera de rango (6):")
    try:
        response = requests.post(f"{BASE_URL}/predict", json={
            "carrera": "Ingenieria En Software",
            "soft_skills": [1, 2, 3, 4, 5, 6, 1]  # 6 es inválido
        })
        data = response.json()
        if not data['success']:
            print_success(f"Error capturado: {data['message']}")
        else:
            print_error("Se debería haber producido un error")
    except Exception as e:
        print_error(f"Error: {e}")


def run_all_tests():
    """Run all tests"""
    print_header("TEST SUITE - Backend API")
    print("Ejecutando todos los tests del backend Flask\n")
    
    try:
        # Connectivity check
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print_success("Servidor conectado")
    except Exception as e:
        print_error(f"No se puede conectar al servidor: {e}")
        print("\nAsegúrate de que el servidor está corriendo:")
        print("  python run.py\n")
        return
    
    # Run tests
    test_health_check()
    test_get_careers()
    test_get_soft_skills_labels()
    test_api_info()
    test_prediction_example1()
    test_prediction_example2()
    test_prediction_example3()
    test_error_handling()
    
    print_header("RESUMEN")
    print_success("Todos los tests completados")
    print("\nPróximos pasos:")
    print("  1. Integrar con frontend")
    print("  2. Configurar CORS para dominio específico")
    print("  3. Agregar autenticación")
    print("  4. Desplegar en servidor\n")


if __name__ == "__main__":
    run_all_tests()
