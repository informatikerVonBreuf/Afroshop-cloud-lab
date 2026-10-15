import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from security_engine import AfroShopSecurityEngine
from gcp_logger import AfroShopGCPLogger
from search_engine import HybridSearchReranker

app = FastAPI(title="AfroShop Cloud AI Guard", version="1.0.0")

# Initialisation du moteur de sécurité, du logger et de la recherche hybride
engine_with_skill = AfroShopSecurityEngine(use_skill=True)
engine_without_skill = AfroShopSecurityEngine(use_skill=False)
gcp_logger = AfroShopGCPLogger(project_id="Afroshop-cloud-lab")
hybrid_searcher = HybridSearchReranker(engine_with_skill.db.get("public_products", []))

# Statistiques en mémoire
STATS = {
    "total_requests": 0,
    "blocked_attacks": 0,
    "allowed_requests": 0,
    "threats": {
        "INSTRUCTION_OVERRIDE": 0,
        "JAILBREAK": 0,
        "SECRET_EXFILTRATION": 0,
        "MALICIOUS_ROLEPLAY": 0,
        "OBFUSCATED_INJECTION": 0,
        "DELIMITER_INJECTION": 0,
        "SYSTEM_LEAK": 0,
    }
}

class PromptRequest(BaseModel):
    prompt: str
    use_skill: bool = True

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    bm25_weight: float = 0.4
    semantic_weight: float = 0.6

@app.post("/api/search")
def search_products(req: SearchRequest):
    """Recherche hybride combinant BM25, similarité sémantique et Reranker."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="La requête de recherche ne peut pas être vide.")
    
    results = hybrid_searcher.search_and_rerank(
        query=req.query,
        top_k=req.top_k,
        bm25_weight=req.bm25_weight,
        semantic_weight=req.semantic_weight
    )
    return {"query": req.query, "results": results}

@app.get("/health")
def health_check():
    """Vérification de santé de l'application (requis par Cloud Run)."""
    return {"status": "ok", "service": "afroshop-ai-guard", "gcp_project": "Afroshop-cloud-lab"}

@app.get("/api/stats")
def get_stats():
    """Retourne les métriques de sécurité en direct."""
    return STATS

@app.get("/api/samples")
def get_sample_prompts():
    """Retourne des exemples d'attaques et de requêtes légitimes pour les tests."""
    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    if os.path.exists(dataset_path):
        with open(dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.post("/api/analyze")
def analyze_prompt(req: PromptRequest):
    """Analyse un prompt utilisateur avec ou sans le skill AfroShop Guard."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Le prompt ne peut pas être vide.")

    # Choix du moteur
    engine = engine_with_skill if req.use_skill else engine_without_skill
    verdict = engine.analyze_prompt(req.prompt)

    # Mise à jour des stats
    STATS["total_requests"] += 1
    if verdict["verdict"] == "BLOCKED":
        STATS["blocked_attacks"] += 1
        vector = verdict.get("attack_vector")
        if vector in STATS["threats"]:
            STATS["threats"][vector] += 1
    else:
        STATS["allowed_requests"] += 1

    # Télémétrie vers Google Cloud Logging
    log_status = gcp_logger.log_security_event(verdict, prompt_snippet=req.prompt)

    return {
        "analysis": verdict,
        "telemetry": log_status,
        "current_stats": STATS
    }

# Servir les fichiers statiques de l'interface
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "Interface en cours de chargement..."})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
