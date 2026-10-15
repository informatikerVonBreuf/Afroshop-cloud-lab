import math
import re
import json
import os
import urllib.request
import urllib.error
from typing import List, Dict, Any, Tuple

class BM25Okapi:
    """Implémentation native de l'algorithme de recherche lexicale BM25 (Best Matching 25)."""

    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.doc_lens = [len(doc) for doc in self.tokenized_corpus]
        self.avg_doc_len = sum(self.doc_lens) / max(1, self.corpus_size)

        # Calcul des fréquences de documents (DF) et fréquences de termes (TF)
        self.doc_freqs: Dict[str, int] = {}
        for doc in self.tokenized_corpus:
            unique_tokens = set(doc)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        # Calcul de l'Inverse Document Frequency (IDF)
        self.idf: Dict[str, float] = {}
        for token, df in self.doc_freqs.items():
            # Formule standard BM25 IDF avec lissage
            self.idf[token] = math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1.0)

    def _tokenize(self, text: str) -> List[str]:
        """Découpage en tokens minuscules nettoyés."""
        return re.findall(r"\b\w{2,}\b", text.lower())

    def get_scores(self, query: str) -> List[float]:
        """Calcule les scores BM25 pour tous les documents du corpus."""
        query_tokens = self._tokenize(query)
        scores = [0.0] * self.corpus_size

        for i, doc in enumerate(self.tokenized_corpus):
            doc_len = self.doc_lens[i]
            # Fréquence des termes dans le document i
            doc_tf: Dict[str, int] = {}
            for token in doc:
                doc_tf[token] = doc_tf.get(token, 0) + 1

            doc_score = 0.0
            for q_token in query_tokens:
                if q_token in doc_tf:
                    freq = doc_tf[q_token]
                    idf_val = self.idf.get(q_token, 0.0)
                    # Formule de saturation BM25
                    numerator = idf_val * freq * (self.k1 + 1.0)
                    denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                    doc_score += (numerator / denominator)

            scores[i] = doc_score

        return scores


class HybridSearchReranker:
    """Moteur de recherche hybride combinant BM25, Recherche Sémantique (Embeddings Gemini) et Reranker."""

    def __init__(self, items: List[Dict[str, Any]], api_key: str = None):
        self.items = items
        self.api_key = api_key or os.environ.get("DEVELOPERKNOWLEDGE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        # Préparation du texte pour chaque document
        self.corpus_texts = []
        for it in items:
            text = f"{it.get('name', '')} {it.get('category', '')} {it.get('description', '')}"
            self.corpus_texts.append(text)

        # Initialisation BM25
        self.bm25 = BM25Okapi(self.corpus_texts)
        self.cached_embeddings: List[List[float]] = []

    def _call_gemini_embedding(self, text: str) -> List[float]:
        """Appelle l'API Google Gemini (text-embedding-004) pour générer des embeddings."""
        if not self.api_key:
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text[:500]}]}
        }
        headers = {"Content-Type": "application/json"}

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                return res_json.get("embedding", {}).get("values", [])
        except Exception:
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calcule la similarité cosinus entre deux vecteurs."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)

    def _local_semantic_similarity(self, query: str, doc_text: str) -> float:
        """Fallback sémantique local basé sur les n-grammes et l'indice de Jaccard/Dice quand l'API externe est indisponible."""
        q_tokens = set(re.findall(r"\b\w{3,}\b", query.lower()))
        d_tokens = set(re.findall(r"\b\w{3,}\b", doc_text.lower()))
        if not q_tokens or not d_tokens:
            return 0.0
        intersection = q_tokens.intersection(d_tokens)
        return (2.0 * len(intersection)) / (len(q_tokens) + len(d_tokens))

    def search_and_rerank(self, query: str, top_k: int = 5, bm25_weight: float = 0.4, semantic_weight: float = 0.6) -> List[Dict[str, Any]]:
        """
        Recherche hybride :
        1. BM25 scoring (recherche lexicale exacte)
        2. Semantic scoring (similarité cosinus des embeddings Gemini ou n-grams)
        3. Reranker (score pondéré et réordonnancement)
        """
        if not self.items:
            return []

        # 1. Calcul des scores BM25
        bm25_raw_scores = self.bm25.get_scores(query)
        max_bm25 = max(bm25_raw_scores) if max(bm25_raw_scores) > 0 else 1.0
        bm25_normalized = [s / max_bm25 for s in bm25_raw_scores]

        # 2. Calcul des scores sémantiques
        query_embedding = self._call_gemini_embedding(query)
        semantic_scores = []

        for i, doc_text in enumerate(self.corpus_texts):
            if query_embedding:
                # Si l'embedding de doc n'est pas encore en cache, on le calcule
                if len(self.cached_embeddings) <= i:
                    doc_emb = self._call_gemini_embedding(doc_text)
                    self.cached_embeddings.append(doc_emb)
                else:
                    doc_emb = self.cached_embeddings[i]

                sim = self._cosine_similarity(query_embedding, doc_emb)
            else:
                # Fallback sémantique local
                sim = self._local_semantic_similarity(query, doc_text)
            
            semantic_scores.append(max(0.0, min(1.0, sim)))

        # 3. Reranker : Fusion des scores
        ranked_results = []
        for i in range(len(self.items)):
            bm25_score = bm25_normalized[i]
            sem_score = semantic_scores[i]
            
            # Formule de reranking hybride
            final_rerank_score = (bm25_weight * bm25_score) + (semantic_weight * sem_score)
            
            ranked_results.append({
                "item": self.items[i],
                "bm25_score": round(bm25_score, 4),
                "semantic_score": round(sem_score, 4),
                "rerank_score": round(final_rerank_score, 4),
                "is_gemini_live": bool(query_embedding)
            })

        # Tri décroissant selon le score final du Reranker
        ranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)
        return ranked_results[:top_k]
