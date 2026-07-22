import os
import joblib
import unicodedata
import json

# Define the 10 verification phrases
verification_phrases = [
    "calculamos la derivada parcial de f de x respecto a y",
    "si el objeto parte del reposo su velocidad inicial es cero pero tiene una aceleracion constante",
    "en el enlace covalente los atomos comparten electrones para alcanzar estabilidad",
    "la fotosintesis ocurre en los cloroplastos donde la planta convierte luz solar en glucosa",
    "este ciclo for recorre la lista enlazada y lanza una excepcion",
    "bueno chicos recuerden entregar la tarea en la plataforma antes de las doce de la noche",
    "calculamos el grafica cruz entre la fuerza en la diapositiva anterior vimos que y la distancia para ver el momento",
    "si conectamos las resistencias en paralelo la esto es identico a cuando corriente es la misma pero el amperaje cambia",
    "vamos a compilar el programa para verificar si tiene errores de sintaxis o de enlace",
    "el ph de la disolucion de acido clorhidrico nos dio aproximadamente cinco"
]

dir_path = os.path.dirname(__file__)
vectorizer_path = os.path.join(dir_path, "materia_vectorizer.joblib")
model_path = os.path.join(dir_path, "materia_classifier.joblib")

vectorizer = joblib.load(vectorizer_path)
model = joblib.load(model_path)

def normalize_text(text):
    text = text.lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    return " ".join(text.split())

results = []
classes = model.classes_

for phrase in verification_phrases:
    cleaned = normalize_text(phrase)
    vec = vectorizer.transform([cleaned])
    pred = model.predict(vec)[0]
    probs = model.predict_proba(vec)[0]
    
    prob_dict = {classes[i]: float(probs[i]) for i in range(len(classes))}
    results.append({
        "phrase": phrase,
        "prediction": pred,
        "probabilities": prob_dict
    })

print(json.dumps(results, indent=2, ensure_ascii=False))
