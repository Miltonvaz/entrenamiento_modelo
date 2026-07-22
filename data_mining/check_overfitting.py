import os
import csv
import json
import unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = "".join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    return " ".join(text.split())

dir_path = os.path.dirname(__file__)
csv_path = os.path.join(dir_path, "corpus_materias.csv")

# 1. Load data
texts = []
labels = []
with open(csv_path, mode='r', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)
    for row in reader:
        if len(row) == 2:
            texts.append(normalize_text(row[0]))
            labels.append(row[1])

X_train, X_test, y_train, y_test = train_test_split(
    texts, labels, test_size=0.20, random_state=42, stratify=labels
)

print(f"Total samples: {len(texts)}")
print(f"Train size: {len(X_train)}")
print(f"Test size: {len(X_test)}")

# 2. Similarity analysis between Test and Train
print("\n--- SIMILARITY ANALYSIS (JACCARD OVERLAP) ---")
high_similarity_count = 0
duplicates_count = 0

for i, test_phrase in enumerate(X_test):
    test_words = set(test_phrase.split())
    best_similarity = 0.0
    best_match = ""
    
    for train_phrase in X_train:
        train_words = set(train_phrase.split())
        intersection = test_words.intersection(train_words)
        union = test_words.union(train_words)
        similarity = len(intersection) / len(union) if len(union) > 0 else 0.0
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = train_phrase
            
    if best_similarity >= 0.85:
        high_similarity_count += 1
        if best_similarity == 1.0:
            duplicates_count += 1
        # Print a few examples
        if high_similarity_count <= 5:
            print(f"Test Sentence:  '{test_phrase}'")
            print(f"Train Match:    '{best_match}'")
            print(f"Jaccard Sim:    {best_similarity:.2%}\n")

print(f"Test sentences with Jaccard Similarity >= 85% with Train: {high_similarity_count} ({high_similarity_count/len(X_test):.2%})")
print(f"Exact duplicates across Train and Test: {duplicates_count} ({duplicates_count/len(X_test):.2%})")

# 3. Fit TF-IDF and Logistic Regression to analyze coefficients
spanish_stop_words = [
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "y", "o", "e", "u",
    "en", "para", "por", "con", "sin", "sobre", "bajo", "entre", "es", "son", "era", "eran", 
    "este", "esta", "estos", "estas", "eso", "esa", "esos", "esas", "todo", "todos", "toda", "todas",
    "su", "sus", "mi", "mis", "tu", "tus", "se", "lo", "le", "les", "me", "te", "nos", "os",
    "que", "como", "cual", "cuales", "quien", "quienes", "cuando", "donde", "si", "no", "mas", "pero",
    "tambien", "ya", "muy", "mismo", "misma", "mismos", "mismas", "a", "da", "dan"
]
vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words=spanish_stop_words)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)


lr = LogisticRegression(max_iter=1000, random_state=42)
lr.fit(X_train_vec, y_train)

feature_names = vectorizer.get_feature_names_out()
classes = lr.classes_
import numpy as np


print("\n--- TOP 10 COEFFICIENTS BY CLASS ---")
for c_idx, class_name in enumerate(classes):
    coefs = lr.coef_[c_idx]
    # Get top 10 indices of highest positive weights
    top_indices = np.argsort(coefs)[-10:][::-1]
    
    print(f"\nClass: {class_name.upper()}")
    for idx in top_indices:
        print(f"  - '{feature_names[idx]}': {coefs[idx]:.4f}")
