import pandas as pd
import numpy as np
import re
import math
from urllib.parse import urlparse

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report,confusion_matrix
from xgboost import XGBClassifier
import pickle

df = pd.read_csv("final_test (2).csv")

# Label encoding
df['label'] = df['label'].map({
    'malicious': 1,
    'benign': 0
})

def entropy(url):
    prob = [float(url.count(c)) / len(url) for c in set(url)]
    return -sum([p * math.log2(p) for p in prob])

def extract_features(url):
    features = []
    
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path

    # Basic
    features.append(len(url))
    features.append(len(domain))
    features.append(url.count('.'))
    features.append(domain.count('.'))
    features.append(len(re.findall(r'[^\w]', url)))
    features.append(url.count('-'))

    # Security
    features.append(1 if url.startswith("https") else 0)
    features.append(1 if re.match(r'http[s]?://\d+\.\d+\.\d+\.\d+', url) else 0)

    # Suspicious keywords
    keywords = ['login','verify','bank','secure','account','update','free','bonus','win']
    features.append(1 if any(word in url.lower() for word in keywords) else 0)

    # Numbers
    features.append(sum(c.isdigit() for c in url))

    # URL shortener
    features.append(1 if any(s in url for s in ['bit.ly','tinyurl','goo.gl']) else 0)

    # Advanced
    features.append(len(path))
    features.append(domain.count('.') - 1)
    features.append(1 if '@' in url else 0)
    features.append(entropy(url))

    # Extra boost features
    features.append(1 if url.endswith(('.xyz','.tk','.ml','.ga')) else 0)
    features.append(1 if len(url) > 75 else 0)

    return features

df['features'] = df['url'].apply(extract_features)

X = pd.DataFrame(df['features'].tolist())
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
neg = sum(y_train == 0)
pos = sum(y_train == 1)

scale_pos_weight = neg / pos
xgb_model = XGBClassifier(
    n_estimators=500,
    learning_rate=0.03,
    max_depth=5,
    subsample=0.9,
    colsample_bytree=0.9,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)
y_prob = xgb_model.predict_proba(X_test)[:, 1]
threshold = 0.35
y_pred = (y_prob > threshold).astype(int)
pickle.dump(xgb_model, open("model.pkl", "wb"))
print("accuracy:", accuracy_score(y_test, y_pred))
print("pricision, recall, f1-score:\n", classification_report(y_test, y_pred))
print("confusion matrix:\n", confusion_matrix(y_test, y_pred))



