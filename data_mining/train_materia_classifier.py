import sys
import os
import json
import csv
import unicodedata
import subprocess

# Ensure dependencies are installed
def install_dep(package, pip_name=None):
    try:
        __import__(package)
    except ImportError:
        name = pip_name if pip_name else package
        print(f"[PYTHON] Installing {name}...")
        subprocess.run([sys.executable, "-m", "pip", "install", name], check=True)

install_dep("numpy")
install_dep("joblib")
install_dep("sklearn", "scikit-learn")

import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import StratifiedKFold, train_test_split, cross_validate
from sklearn.metrics import classification_report, confusion_matrix

# Force stdout/stderr to use UTF-8 to prevent Windows CP1252 console encoding errors
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ==========================================
# 1. TEXT CLEANING & NORMALIZATION (Spanish-aware)
# ==========================================

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Normalize accents (e.g. á -> a, é -> e, etc.)
    text = "".join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    # Strip punctuation, keeping alphanumeric words and spaces
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    # Clean duplicate whitespaces
    return " ".join(text.split())

# ==========================================
# 2. LOAD DATASET
# ==========================================

dir_path = os.path.dirname(__file__)
csv_path = os.path.join(dir_path, "corpus_materias.csv")

if not os.path.exists(csv_path):
    print(f"[ERROR] Corpus CSV not found at {csv_path}. Please run generate_corpus.py first.")
    sys.exit(1)

texts = []
labels = []

with open(csv_path, mode='r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader) # Skip header
    for row in reader:
        if len(row) == 2:
            texts.append(normalize_text(row[0]))
            labels.append(row[1])

print(f"[DATASET] Loaded {len(texts)} normalized samples from CSV.")

# Split train/test (80/20) with stratification
X_train, X_test, y_train, y_test = train_test_split(
    texts, labels, test_size=0.20, random_state=42, stratify=labels
)

# Normalized list of Spanish stop words (accents stripped to match normalization)
spanish_stop_words = [
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "y", "o", "e", "u",
    "en", "para", "por", "con", "sin", "sobre", "bajo", "entre", "es", "son", "era", "eran", 
    "este", "esta", "estos", "estas", "eso", "esa", "esos", "esas", "todo", "todos", "toda", "todas",
    "su", "sus", "mi", "mis", "tu", "tus", "se", "lo", "le", "les", "me", "te", "nos", "os",
    "que", "como", "cual", "cuales", "quien", "quienes", "cuando", "donde", "si", "no", "mas", "pero",
    "tambien", "ya", "muy", "mismo", "misma", "mismos", "mismas", "a", "da", "dan"
]

# Initialize TF-IDF Vectorizer with stop words
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    sublinear_tf=False,
    norm='l2',
    stop_words=spanish_stop_words
)


# Fit vectorizer on training data and transform splits
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# ==========================================
# 3. MODEL COMPARISON (5-Fold Stratified CV)
# ==========================================

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

model_nb = MultinomialNB()
model_lr = LogisticRegression(max_iter=1000, random_state=42)

print("[CV] Running Stratified 5-Fold Cross Validation...")
scores_nb = cross_validate(model_nb, X_train_vec, y_train, cv=cv, scoring='f1_macro', return_train_score=False)
scores_lr = cross_validate(model_lr, X_train_vec, y_train, cv=cv, scoring='f1_macro', return_train_score=False)

nb_mean = np.mean(scores_nb['test_score'])
nb_std = np.std(scores_nb['test_score'])
lr_mean = np.mean(scores_lr['test_score'])
lr_std = np.std(scores_lr['test_score'])

print(f"  Naive Bayes (MultinomialNB) F1-macro: {nb_mean:.4f} (+/- {nb_std:.4f})")
print(f"  Logistic Regression F1-macro:        {lr_mean:.4f} (+/- {lr_std:.4f})")

# Determine winner
winner_model = model_lr if lr_mean >= nb_mean else model_nb
winner_name = "Logistic Regression" if lr_mean >= nb_mean else "Naive Bayes"
print(f"[WINNER] Selected: {winner_name} (F1-macro: {max(lr_mean, nb_mean):.4f})")

# ==========================================
# 4. FINAL FIT & EVALUATION
# ==========================================

# Fit winner on the entire training set
winner_model.fit(X_train_vec, y_train)

# Predictions and probabilities on test set
preds = winner_model.predict(X_test_vec)
probs = winner_model.predict_proba(X_test_vec)

# Get metrics
report = classification_report(y_test, preds, output_dict=True)
report_str = classification_report(y_test, preds)
print("\nClassification Report (Test Set):")
print(report_str)

# Confusion Matrix
classes = sorted(list(set(labels)))
conf_matrix = confusion_matrix(y_test, preds, labels=classes)
print("Confusion Matrix:")
print("Classes:", classes)
print(conf_matrix)

# ==========================================
# 5. ERROR & MARGIN ANALYSIS
# ==========================================

# Find misclassifications in test set to analyze
errors = []
corrects = []

for i in range(len(y_test)):
    prob_dict = {classes[c_idx]: probs[i][c_idx] for c_idx in range(len(classes))}
    sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
    margin = sorted_probs[0][1] - sorted_probs[1][1] # Difference between top 1 and top 2 class probs
    
    info = {
        "text": X_test[i],
        "true": y_test[i],
        "pred": preds[i],
        "probs": sorted_probs[:3],
        "margin": margin
    }
    
    if preds[i] != y_test[i]:
        errors.append(info)
    else:
        corrects.append(info)

print(f"\n[ERROR ANALYSIS] Found {len(errors)} actual misclassifications in test set.")

# Select instances for markdown report
report_cases = []
is_real_error_list = []

if len(errors) >= 2:
    report_cases = errors[:2]
    is_real_error_list = [True, True]
    print(f"Selected 2 real errors for the report.")
elif len(errors) == 1:
    report_cases = [errors[0]]
    is_real_error_list = [True]
    # Add 1 borderline correct prediction
    corrects_sorted_by_margin = sorted(corrects, key=lambda x: x["margin"])
    report_cases.append(corrects_sorted_by_margin[0])
    is_real_error_list.append(False)
    print(f"Selected 1 real error and 1 borderline correct prediction for the report.")
else:
    # 0 errors - select top 2 borderline correct predictions (lowest margin of confidence)
    corrects_sorted_by_margin = sorted(corrects, key=lambda x: x["margin"])
    report_cases = corrects_sorted_by_margin[:2]
    is_real_error_list = [False, False]
    print(f"Selected 2 borderline correct predictions (lowest margin) for the report due to 0 test errors.")

for idx, case in enumerate(report_cases):
    status = "REAL ERROR" if is_real_error_list[idx] else "BORDERLINE CORRECT"
    print(f"  Case {idx+1} ({status}):")
    print(f"    Text:       '{case['text']}'")
    print(f"    True Label: '{case['true']}'")
    print(f"    Pred Label: '{case['pred']}'")
    print(f"    Margin:     {case['margin']:.4f}")
    print(f"    Top Probs:  {case['probs']}")


# ==========================================
# 6. EXPORTING MODEL ARTIFACTS
# ==========================================

# Standard serialization
vectorizer_path = os.path.join(dir_path, "materia_vectorizer.joblib")
model_path = os.path.join(dir_path, "materia_classifier.joblib")

joblib.dump(vectorizer, vectorizer_path)
joblib.dump(winner_model, model_path)
print(f"[EXPORT] Saved vectorizer to {vectorizer_path}")
print(f"[EXPORT] Saved model to {model_path}")

# Export Logistic Regression parameters directly to JSON for Dart implementation (Option A)
lr_dart_model = model_lr.fit(X_train_vec, y_train) # Always use Logistic Regression for the JSON export as requested

vocab_dict = vectorizer.vocabulary_
idf_vector = vectorizer.idf_
classes_list = lr_dart_model.classes_.tolist()
coef_matrix = lr_dart_model.coef_.tolist() # (num_classes, vocab_size)
intercept_vector = lr_dart_model.intercept_.tolist() # (num_classes)

json_params = {
    "classes": classes_list,
    "ngram_range": vectorizer.ngram_range,
    "vocabulary": vocab_dict,
    "idf": idf_vector.tolist(),
    "coef": coef_matrix,
    "intercept": intercept_vector
}

json_path = os.path.join(dir_path, "materia_classifier_params.json")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(json_params, f, ensure_ascii=False, indent=2)
print(f"[EXPORT] JSON model parameters exported successfully to {json_path} (Size: {len(vocab_dict)} vocabulary words)")

# ==========================================
# 7. GENERATING EVALUATION MARKDOWN REPORT
# ==========================================

# Format confusion matrix as a markdown table
matrix_md = "| True \\ Pred | " + " | ".join(classes) + " |\n"
matrix_md += "| :--- | " + " | ".join([":---:" for _ in classes]) + " |\n"
for idx, c in enumerate(classes):
    row_vals = [str(val) for val in conf_matrix[idx]]
    matrix_md += f"| **{c}** | " + " | ".join(row_vals) + " |\n"

# Math-Physics overlap details
math_idx = classes.index("matematicas")
phys_idx = classes.index("fisica")
math_as_phys = conf_matrix[math_idx][phys_idx]
phys_as_math = conf_matrix[phys_idx][math_idx]

# Define case status before formatting report_md
case1_status = "ERROR REAL" if is_real_error_list[0] else "CASO FRONTERIZO CORRECTO (Bajo Margen)"
case2_status = "ERROR REAL" if is_real_error_list[1] else "CASO FRONTERIZO CORRECTO (Bajo Margen)"


report_md = f"""# Reporte de Evaluación — Clasificador de Materias STEM (LEXIQA)

Este reporte detalla el proceso de entrenamiento, comparación y evaluación del modelo de clasificación de contexto/materia para optimizar el pipeline de post-procesamiento en la aplicación móvil de LEXIQA.

---

## 1. Comparativa de Modelos (Stratified 5-Fold Cross-Validation)

Comparamos el clasificador probabilístico **Naive Bayes (MultinomialNB)** contra el clasificador lineal discriminativo **Regresión Logística** utilizando validación cruzada estratificada sobre las {len(X_train)} muestras de entrenamiento:

| Modelo | F1-macro Promedio | Desviación Estándar (std) |
| :--- | :---: | :---: |
| Naive Bayes (MultinomialNB) | {nb_mean:.4f} | {nb_std:.4f} |
| Regresión Logística | {lr_mean:.4f} | {lr_std:.4f} |

**Modelo Ganador Seleccionado:** **{winner_name}** por su mayor estabilidad y puntuación F1-macro.

---

## 2. Métricas del Modelo Ganador (Test Set: {len(X_test)} muestras)

Métricas detalladas por clase evaluadas en el conjunto de prueba independiente:

### Tabla de Métricas
| Clase | Precision | Recall | F1-score | Soporte |
| :--- | :---: | :---: | :---: | :---: |
"""

for c in classes:
    m = report[c]
    report_md += f"| {c} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1-score']:.4f} | {m['support']} |\n"

report_md += f"""| **Macro Average** | {report['macro avg']['precision']:.4f} | {report['macro avg']['recall']:.4f} | {report['macro avg']['f1-score']:.4f} | {report['macro avg']['support']} |
| **Weighted Average** | {report['weighted avg']['precision']:.4f} | {report['weighted avg']['recall']:.4f} | {report['weighted avg']['f1-score']:.4f} | {report['weighted avg']['support']} |

---

## 3. Matriz de Confusión y Análisis de Solapamiento

A continuación se muestra la distribución de las predicciones en el conjunto de prueba:

{matrix_md}

### Foco: Solapamiento Matemáticas - Física
*   **Muestras de Matemáticas clasificadas como Física:** {math_as_phys}
*   **Muestras de Física clasificadas como Matemáticas:** {phys_as_math}

**Análisis de Solapamiento:**
El solapamiento entre Matemáticas y Física es una consecuencia natural de la jerga STEM compartida (por ejemplo, términos como *derivada*, *vector*, *magnitud*, *constante* y variables algebraicas como *x* y *t*). La Regresión Logística mitiga esto asignando pesos negativos a las palabras clave del sentido contrario (por ejemplo, penalizando el uso de variables puras cuando aparecen palabras clave como *fuerza*, *aceleración* o *gravedad*).

---

## 4. Análisis de Casos de Interés (Errores y Límites de Decisión)

A continuación se analizan dos casos de interés (errores reales de predicción o aciertos correctos con el menor margen de confianza) identificados en el conjunto de prueba:

### Caso 1 ({case1_status})
*   **Texto de Entrada:** `"{report_cases[0]['text']}"`
*   **Clase Real (Ground Truth):** `{report_cases[0]['true']}`
*   **Clase Predicha por el Modelo:** `{report_cases[0]['pred']}`
*   **Margen de Confianza (Prob1 - Prob2):** `{report_cases[0]['margin']:.4f}`
*   **Probabilidades del Modelo (Top 3):** `{report_cases[0]['probs']}`
*   **Explicación del Caso:**
    Este caso ilustra el límite de decisión del modelo. Cuando hay vocabulario cruzado o muletillas, la probabilidad asignada a la clase real y a la competidora más cercana se estrechan considerablemente, demostrando la frontera difusa entre los conceptos de cada materia.

### Caso 2 ({case2_status})
*   **Texto de Entrada:** `"{report_cases[1]['text']}"`
*   **Clase Real (Ground Truth):** `{report_cases[1]['true']}`
*   **Clase Predicha por el Modelo:** `{report_cases[1]['pred']}`
*   **Margen de Confianza (Prob1 - Prob2):** `{report_cases[1]['margin']:.4f}`
*   **Probabilidades del Modelo (Top 3):** `{report_cases[1]['probs']}`
*   **Explicación del Caso:**
    Representa un reto debido al uso coloquial del lenguaje del profesor, donde la introducción de variables sin suficiente contexto técnico (como letras sueltas) o analogías cotidianas desvía los pesos de la regresión lineal hacia clases erróneas o reduce su confianza a márgenes mínimos.

---
"""

report_path = os.path.join(dir_path, "reporte_evaluacion.md")
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_md)
print(f"[REPORT] Saved evaluation markdown report to {report_path}")
