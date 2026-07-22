# Reporte de Evaluación — Clasificador de Materias STEM (LEXIQA)

Este reporte detalla el proceso de entrenamiento, comparación y evaluación del modelo de clasificación de contexto/materia para optimizar el pipeline de post-procesamiento en la aplicación móvil de LEXIQA.

---

## 1. Comparativa de Modelos (Stratified 5-Fold Cross-Validation)

Comparamos el clasificador probabilístico **Naive Bayes (MultinomialNB)** contra el clasificador lineal discriminativo **Regresión Logística** utilizando validación cruzada estratificada sobre las 864 muestras de entrenamiento:

| Modelo | F1-macro Promedio | Desviación Estándar (std) |
| :--- | :---: | :---: |
| Naive Bayes (MultinomialNB) | 0.9919 | 0.0101 |
| Regresión Logística | 0.9942 | 0.0090 |

**Modelo Ganador Seleccionado:** **Logistic Regression** por su mayor estabilidad y puntuación F1-macro.

---

## 2. Métricas del Modelo Ganador (Test Set: 216 muestras)

Métricas detalladas por clase evaluadas en el conjunto de prueba independiente:

### Tabla de Métricas
| Clase | Precision | Recall | F1-score | Soporte |
| :--- | :---: | :---: | :---: | :---: |
| biologia | 1.0000 | 1.0000 | 1.0000 | 36.0 |
| fisica | 1.0000 | 1.0000 | 1.0000 | 36.0 |
| general | 1.0000 | 1.0000 | 1.0000 | 36.0 |
| matematicas | 1.0000 | 1.0000 | 1.0000 | 36.0 |
| programacion | 1.0000 | 1.0000 | 1.0000 | 36.0 |
| quimica | 1.0000 | 1.0000 | 1.0000 | 36.0 |
| **Macro Average** | 1.0000 | 1.0000 | 1.0000 | 216.0 |
| **Weighted Average** | 1.0000 | 1.0000 | 1.0000 | 216.0 |

---

## 3. Matriz de Confusión y Análisis de Solapamiento

A continuación se muestra la distribución de las predicciones en el conjunto de prueba:

| True \ Pred | biologia | fisica | general | matematicas | programacion | quimica |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **biologia** | 36 | 0 | 0 | 0 | 0 | 0 |
| **fisica** | 0 | 36 | 0 | 0 | 0 | 0 |
| **general** | 0 | 0 | 36 | 0 | 0 | 0 |
| **matematicas** | 0 | 0 | 0 | 36 | 0 | 0 |
| **programacion** | 0 | 0 | 0 | 0 | 36 | 0 |
| **quimica** | 0 | 0 | 0 | 0 | 0 | 36 |


### Foco: Solapamiento Matemáticas - Física
*   **Muestras de Matemáticas clasificadas como Física:** 0
*   **Muestras de Física clasificadas como Matemáticas:** 0

**Análisis de Solapamiento:**
El solapamiento entre Matemáticas y Física es una consecuencia natural de la jerga STEM compartida (por ejemplo, términos como *derivada*, *vector*, *magnitud*, *constante* y variables algebraicas como *x* y *t*). La Regresión Logística mitiga esto asignando pesos negativos a las palabras clave del sentido contrario (por ejemplo, penalizando el uso de variables puras cuando aparecen palabras clave como *fuerza*, *aceleración* o *gravedad*).

---

## 4. Análisis de Casos de Interés (Errores y Límites de Decisión)

A continuación se analizan dos casos de interés (errores reales de predicción o aciertos correctos con el menor margen de confianza) identificados en el conjunto de prueba:

### Caso 1 (CASO FRONTERIZO CORRECTO (Bajo Margen))
*   **Texto de Entrada:** `"calculamos el grafica cruz entre la fuerza en la diapositiva anterior vimos que y la distancia para ver el momento"`
*   **Clase Real (Ground Truth):** `matematicas`
*   **Clase Predicha por el Modelo:** `matematicas`
*   **Margen de Confianza (Prob1 - Prob2):** `0.1160`
*   **Probabilidades del Modelo (Top 3):** `[('matematicas', np.float64(0.34401916806147015)), ('fisica', np.float64(0.22806796910381147)), ('programacion', np.float64(0.12638580853991035))]`
*   **Explicación del Caso:**
    Este caso ilustra el límite de decisión del modelo. Cuando hay vocabulario cruzado o muletillas, la probabilidad asignada a la clase real y a la competidora más cercana se estrechan considerablemente, demostrando la frontera difusa entre los conceptos de cada materia.

### Caso 2 (CASO FRONTERIZO CORRECTO (Bajo Margen))
*   **Texto de Entrada:** `"calculamos el ecuacion diferencial cruz entre la fuerza y la distancia para ver el momento"`
*   **Clase Real (Ground Truth):** `matematicas`
*   **Clase Predicha por el Modelo:** `matematicas`
*   **Margen de Confianza (Prob1 - Prob2):** `0.1589`
*   **Probabilidades del Modelo (Top 3):** `[('matematicas', np.float64(0.4520087027554284)), ('fisica', np.float64(0.2931188378136683)), ('programacion', np.float64(0.06579579113803856))]`
*   **Explicación del Caso:**
    Representa un reto debido al uso coloquial del lenguaje del profesor, donde la introducción de variables sin suficiente contexto técnico (como letras sueltas) o analogías cotidianas desvía los pesos de la regresión lineal hacia clases erróneas o reduce su confianza a márgenes mínimos.

---
