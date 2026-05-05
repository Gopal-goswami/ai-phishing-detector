from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

import pickle
import re
from urllib.parse import urlparse
import math

app = FastAPI()

# Suppress unnecessary logging
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.INFO)

# Get the current directory
BASE_DIR = Path(__file__).resolve().parent

# Static files (CSS, Images)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# =========================
# LOAD MODEL
# =========================
try:
    model_path = BASE_DIR / "model.pkl"
    with open(model_path, "rb") as f:
        my_model = pickle.load(f)
except FileNotFoundError:
    print(f"❌ Error: model.pkl not found at {BASE_DIR / 'model.pkl'}")
    print(f"Current directory: {BASE_DIR}")
    exit(1)
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit(1)

def entropy(url):
    prob = [float(url.count(c)) / len(url) for c in set(url)]
    return -sum([p * math.log2(p) for p in prob])

# =========================
# FEATURE EXTRACTION
# =========================
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

# =========================
# HOME PAGE
# =========================
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
    request=request, 
    name="index.html",
    context={"result": None, "color": None}
)

# =========================
# PREDICTION
# =========================
@app.post("/predict", response_class=HTMLResponse)
def predict(request: Request, url: str = Form(...)):
    
    features = extract_features(url)

    result = my_model.predict([features])[0]

    try:
        prob = my_model.predict_proba([features])[0][1]
    except:
        prob = None

    if result == 1:
        output = "⚠️ Website is unsafe"
        color = "red"
    else:
        output = "✅ Website is safe"
        color = "lightgreen"

    if prob is not None:
        output += f" (Confidence: {round(prob*100,2)}%)"

    return templates.TemplateResponse(
    request=request,  
    name="index.html",
    context={"result": output, "color": color,"url": url}
)


# =========================
# CATCH-ALL ROUTE (404)
# =========================
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(path_name: str):
    """Handle all undefined routes gracefully"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"}
    )


