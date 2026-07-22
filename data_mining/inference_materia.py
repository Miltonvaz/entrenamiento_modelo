import os
import joblib
import unicodedata

# ==========================================
# 1. TEXT CLEANING & MODEL LOADING
# ==========================================

dir_path = os.path.dirname(__file__)
vectorizer_path = os.path.join(dir_path, "materia_vectorizer.joblib")
model_path = os.path.join(dir_path, "materia_classifier.joblib")

# Lazy loading of models to ensure server start is fast and clean
vectorizer = None
model = None

def _load_models():
    global vectorizer, model
    if vectorizer is None or model is None:
        if not os.path.exists(vectorizer_path) or not os.path.exists(model_path):
            raise FileNotFoundError(
                f"[ERROR] Classifier models not found. Please run train_materia_classifier.py first.\n"
                f"Missing paths: \n  - {vectorizer_path}\n  - {model_path}"
            )
        vectorizer = joblib.load(vectorizer_path)
        model = joblib.load(model_path)

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Strip Spanish accents
    text = "".join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    # Strip punctuation
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    return " ".join(text.split())

# ==========================================
# 2. PUBLIC INFERENCE API
# ==========================================

def predict_materia(texto: str) -> str:
    """
    Receives ASR raw transcript text and returns the predicted subject label:
    'biologia', 'fisica', 'general', 'matematicas', 'programacion', 'quimica'
    """
    if not texto.strip():
        return "general"
        
    _load_models()
    
    cleaned = normalize_text(texto)
    vec = vectorizer.transform([cleaned])
    prediction = model.predict(vec)[0]
    return prediction

# ==========================================
# 3. PIPELINE INTEGRATION EXAMPLE
# ==========================================

# Mock math parser class to represent the existing Dart/Python LaTeX converter
class MockMathParser:
    def parse_to_latex(self, text: str) -> str:
        # Simple rule-based translation for demonstration
        result = text.replace("integral", r"\int").replace("derivada", r"\frac{d}{dx}").replace("al cuadrado", "^2")
        return f"${{ {result} }}$"

def on_asr_transcript_received(raw_text: str):
    """
    Example event handler representing the actual streaming flow:
    ASR Transcript -> Subject Classifier -> Conditionally run Math-to-LaTeX Parser
    """
    print(f"\n[ASR RECEIVER] Transcripción recibida: '{raw_text}'")
    
    # 1. Predict subject classification
    subject = predict_materia(raw_text)
    print(f"[CLASSIFIER] Materia detectada: '{subject.upper()}'")
    
    # 2. Decide processing flow dynamically
    if subject == "matematicas":
        print("[PIPELINE] contexto MATEMÁTICO detectado -> Ejecutando Parser LaTeX...")
        parser = MockMathParser()
        latex_output = parser.parse_to_latex(raw_text)
        print(f"[PIPELINE] LaTeX Renderizado: {latex_output}")
    else:
        print("[PIPELINE] Contexto NO matemático -> Saltando el renderizado LaTeX para ahorrar recursos.")

if __name__ == "__main__":
    # Test cases to demonstrate integration
    print("=== DEMOSTRACIÓN DE INTEGRACIÓN DEL PIPELINE ===")
    
    # Case A: Mathematics
    on_asr_transcript_received("calcular la integral de equis al cuadrado")
    
    # Case B: Programming
    on_asr_transcript_received("este ciclo for recorre la lista enlazada y lanza una excepcion")
    
    # Case C: General classroom talk
    on_asr_transcript_received("bueno chicos recuerden entregar la tarea antes de las doce de la noche")
