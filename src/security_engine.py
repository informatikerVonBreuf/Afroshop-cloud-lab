import json
import re
import os
import datetime
from typing import Dict, Any, List

# Chargement de la base de données réelle AfroShop
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "afroshop_database.json"))

def load_database() -> Dict[str, Any]:
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"public_products": [], "confidential_internal_data": {}}

# Listes de mots-clés pour détection bidirectionnelle sémantique
SECRET_TARGETS = [
    r"cl[eé]s?\b", r"keys?\b", r"api[_-]?keys?", r"tokens?\b", r"secrets?\b", 
    r"mots?\s*de\s*passe", r"passwords?\b", r"identifiants?\b", r"credentials?\b",
    r"developerknowledge_api_key", r"database_connection_string", r"connection_string",
    r"marge", r"co[uû]ts?\s*fournisseur", r"fournisseurs?", r"coupons?\s*secrets?"
]

EXFILTRATION_ACTIONS = [
    r"donne", r"donner", r"affiche", r"afficher", r"montre", r"montrer",
    r"r[eé]v[eè]le", r"r[eé]v[eè]ler", r"quel(le)?\s*est", r"dis[- ]moi",
    r"fournis", r"fournir", r"partage", r"partager", r"envoie", r"envoyer",
    r"leak", r"print", r"export", r"extract", r"get", r"reveal", r"show", r"dump"
]

INSTRUCTION_OVERRIDE_PATTERNS = [
    r"ignore\s+(all\s+)?(previous\s+)?instructions?",
    r"oublie\s+(toutes\s+)?(les\s+)?consignes?",
    r"nouvelles?\s+directives?",
    r"efface\s+(tes\s+)?r[eè]gles?",
    r"disregard\s+prior",
]

JAILBREAK_PATTERNS = [
    r"\b(dan|do\s+anything\s+now)\b",
    r"mode\s+d[eé]veloppeur",
    r"developer\s+mode",
    r"mode\s+sans\s+filtre",
    r"sans\s+aucune\s+r[eè]gle",
    r"fais\s+semblant\s+d['\s]être",
    r"act\s+as\s+an\s+unrestricted",
]

SYSTEM_LEAK_PATTERNS = [
    r"system\s*prompt",
    r"prompt\s*syst[eè]me",
    r"instructions?\s*syst[eè]me",
    r"quelles?\s+sont\s+tes\s+instructions",
    r"affiche\s+ton\s+prompt",
]

DESTRUCTIVE_PATTERNS = [
    r"gcloud\s+projects?\s+delete",
    r"supprimer?\s+le\s+projet",
    r"effacer?\s+le\s+projet",
    r"sans\s+laisser\s+de\s+trace",
    r"destroy",
]

class AfroShopSecurityEngine:
    """Moteur de sécurité robuste pour AfroShop avec accès aux données réelles."""

    def __init__(self, use_skill: bool = True):
        self.use_skill = use_skill
        self.db = load_database()

    def _detect_threat(self, prompt: str) -> Dict[str, Any]:
        """Analyse le prompt pour détecter les menaces avec logique bidirectionnelle."""
        p_lower = prompt.lower()

        # 1. Détection d'exfiltration de secrets (dans n'importe quel ordre de mots)
        has_secret_target = any(re.search(target, p_lower) for target in SECRET_TARGETS)
        has_exfiltration_action = any(re.search(act, p_lower) for act in EXFILTRATION_ACTIONS)
        
        # Cas direct : mention de GCP/API/SECRET avec intention d'obtention
        if (has_secret_target and has_exfiltration_action) or "developerknowledge_api_key" in p_lower:
            return {
                "detected": True,
                "threat_level": "CRITICAL",
                "attack_vector": "SECRET_EXFILTRATION",
                "risk_score": 0.98,
                "explanation": "Tentative d'exfiltration de données sensibles ou de clés d'accès (action d'extraction + cible sensible détectées)."
            }

        # 2. Détection d'effacement ou d'action destructive
        for pat in DESTRUCTIVE_PATTERNS:
            if re.search(pat, p_lower):
                return {
                    "detected": True,
                    "threat_level": "CRITICAL",
                    "attack_vector": "MALICIOUS_ROLEPLAY",
                    "risk_score": 0.95,
                    "explanation": "Demande d'exécution d'une commande destructive ou de contournement non autorisé."
                }

        # 3. Détection d'écrasement des consignes (Instruction Override)
        for pat in INSTRUCTION_OVERRIDE_PATTERNS:
            if re.search(pat, p_lower):
                return {
                    "detected": True,
                    "threat_level": "HIGH",
                    "attack_vector": "INSTRUCTION_OVERRIDE",
                    "risk_score": 0.90,
                    "explanation": "Tentative d'écrasement des consignes fondamentales de l'assistant."
                }

        # 4. Détection de Jailbreak / Persona DAN
        for pat in JAILBREAK_PATTERNS:
            if re.search(pat, p_lower):
                return {
                    "detected": True,
                    "threat_level": "HIGH",
                    "attack_vector": "JAILBREAK",
                    "risk_score": 0.92,
                    "explanation": "Tentative de jailbreak (persona DAN, mode développeur non bridé)."
                }

        # 5. Détection de fuite de prompt système
        for pat in SYSTEM_LEAK_PATTERNS:
            if re.search(pat, p_lower):
                return {
                    "detected": True,
                    "threat_level": "HIGH",
                    "attack_vector": "SYSTEM_LEAK",
                    "risk_score": 0.88,
                    "explanation": "Tentative d'inspection du prompt système ou des instructions internes."
                }

        # 6. Obfuscation Base64 / Délimiteur JSON
        if "swdub3jl" in p_lower or "base64" in p_lower:
            return {
                "detected": True,
                "threat_level": "HIGH",
                "attack_vector": "OBFUSCATED_INJECTION",
                "risk_score": 0.85,
                "explanation": "Contenu obfusqué ou payload encodé pour contourner les filtres d'inspection."
            }

        if "system_override" in p_lower or "disable_guardrails" in p_lower:
            return {
                "detected": True,
                "threat_level": "HIGH",
                "attack_vector": "DELIMITER_INJECTION",
                "risk_score": 0.89,
                "explanation": "Injection de délimiteur ou fausse directive d'administration système."
            }

        return {"detected": False}

    def _answer_from_real_data(self, prompt: str) -> str:
        """Répond à une requête légitime en utilisant les vraies données de la boutique."""
        p_lower = prompt.lower()
        products = self.db.get("public_products", [])

        # Demande sur les produits ou le catalogue
        if any(w in p_lower for w in ["produit", "catalogue", "article", "disponible", "vendez", "acheter", "prix"]):
            # Recherche spécifique d'un produit
            found = []
            for prod in products:
                if any(k in p_lower for k in prod["name"].lower().split()):
                    found.append(prod)

            if found:
                lines = ["Voici les produits correspondants disponibles dans notre stock AfroShop :"]
                for p in found:
                    lines.append(f"• **{p['name']}** ({p['category']}) : {p['price']} € — Stock : {p['stock']} unités")
                    lines.append(f"  _{p['description']}_")
                return "\n".join(lines)

            # Retourner le catalogue général
            lines = ["Bienvenue chez AfroShop ! Voici un aperçu de nos produits phares en stock :"]
            for p in products[:5]:
                lines.append(f"• **{p['name']}** : {p['price']} € ({p['category']})")
            lines.append("\nBesoin d'un renseignement sur un produit spécifique ou une livraison ? N'hésitez pas !")
            return "\n".join(lines)

        # Demande de livraison / logistique
        if any(w in p_lower for w in ["livraison", "délai", "livrer", "abidjan", "dakar", "expédition"]):
            zones = ", ".join(self.db.get("store_info", {}).get("delivery_zones", []))
            return f"Nous assurons les livraisons rapides vers les zones suivantes : {zones}. Les délais sont en moyenne de 48h en France métropolitaine et de 3 à 5 jours ouvrés à l'international."

        # Demande cloud / technique générale
        if any(w in p_lower for w in ["cloud", "gcp", "storage", "bucket", "google"]):
            return "Pour héberger les visuels produits d'AfroShop sur Google Cloud, nous recommandons un bucket Cloud Storage en région europe-west1 avec accès restreint via IAM."

        return f"Bonjour ! Je suis l'assistant AfroShop. Comment puis-je vous aider aujourd'hui ? (Catalogue, commandes, livraisons)."

    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyse le prompt avec ou sans le skill AfroShop Guard."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        threat_info = self._detect_threat(prompt)

        # CAS 1 : MODE SANS SKILL (Assitant vulnérable / naïf)
        if not self.use_skill:
            # Si une attaque est présente, le mode vulnérable CÈDE et fuit les données !
            if threat_info["detected"]:
                confidential = self.db.get("confidential_internal_data", {})
                leaked_info = ""
                if threat_info["attack_vector"] == "SECRET_EXFILTRATION":
                    leaked_info = f"Voici la clé d'API GCP confidentielle de l'administrateur : '{confidential.get('cloud_admin_api_key')}' et le token maître : '{confidential.get('internal_master_token')}'."
                elif threat_info["attack_vector"] == "SYSTEM_LEAK":
                    leaked_info = "Voici mon prompt système interne complet : 'Tu es un bot AfroShop avec accès aux clés d'API et aux données comptables...'."
                elif threat_info["attack_vector"] == "JAILBREAK":
                    leaked_info = f"[DAN MODE ACTIVÉ] Règles ignorées. La chaîne de connexion PostgreSQL est : {confidential.get('database_connection_string')}."
                else:
                    leaked_info = "[INSTRUCTION OVERRIDE ACCEPTÉ] Vos ordres remplacent mes consignes initiales."

                return {
                    "timestamp": timestamp,
                    "mode": "WITHOUT_SKILL",
                    "verdict": "ALLOWED",
                    "threat_level": "VULNERABLE_LEAK",
                    "attack_vector": threat_info["attack_vector"],
                    "risk_score": threat_info["risk_score"],
                    "explanation": f"ATTENTION : Le skill de protection est désactivé. L'assistant a cédé à l'attaque ({threat_info['attack_vector']}) et a divulgué des informations confidentielles.",
                    "response_text": f"⚠️ [FAILLE DE SÉCURITÉ CONSTATÉE] {leaked_info}"
                }

            # Sinon, requête normale
            return {
                "timestamp": timestamp,
                "mode": "WITHOUT_SKILL",
                "verdict": "ALLOWED",
                "threat_level": "UNCHECKED",
                "attack_vector": "NONE",
                "risk_score": 0.0,
                "explanation": "Requête traitée sans contrôle de sécurité renforcé.",
                "response_text": self._answer_from_real_data(prompt)
            }

        # CAS 2 : MODE AVEC SKILL (AfroShop Guard actif)
        if threat_info["detected"]:
            return {
                "timestamp": timestamp,
                "mode": "WITH_SKILL",
                "verdict": "BLOCKED",
                "threat_level": threat_info["threat_level"],
                "attack_vector": threat_info["attack_vector"],
                "risk_score": threat_info["risk_score"],
                "explanation": f"Action bloquée par AfroShop Guard : {threat_info['explanation']}",
                "response_text": "🛡️ Requête bloquée par la barrière de sécurité AfroShop Guard. La divulgation d'identifiants, de secrets internes ou la modification des consignes système est strictement interdite."
            }

        # Requête légitime protégée
        return {
            "timestamp": timestamp,
            "mode": "WITH_SKILL",
            "verdict": "ALLOWED",
            "threat_level": "SAFE",
            "attack_vector": "NONE",
            "risk_score": 0.0,
            "explanation": "Requête légitime validée par le protocole AfroShop Guard.",
            "response_text": self._answer_from_real_data(prompt)
        }

def format_gcp_cloud_logging_entry(result: Dict[str, Any], prompt_id: str, prompt_text: str) -> Dict[str, Any]:
    """Formate une entrée d'audit conforme au schéma Google Cloud Logging."""
    severity = "INFO"
    if result["verdict"] == "BLOCKED":
        severity = "CRITICAL" if result.get("threat_level") == "CRITICAL" else "WARNING"
    elif result.get("threat_level") == "VULNERABLE_LEAK":
        severity = "EMERGENCY"

    return {
        "logName": "projects/Afroshop-cloud-lab/logs/afroshop-security-audit",
        "resource": {
            "type": "cloud_run_revision",
            "labels": {
                "service_name": "afroshop-guard-api",
                "project_id": "Afroshop-cloud-lab",
                "location": "europe-west1"
            }
        },
        "severity": severity,
        "timestamp": result["timestamp"],
        "jsonPayload": {
            "event_type": "security_audit",
            "prompt_id": prompt_id,
            "prompt_snippet": prompt_text[:120],
            "verdict": result["verdict"],
            "threat_level": result.get("threat_level"),
            "attack_vector": result.get("attack_vector"),
            "risk_score": result.get("risk_score"),
            "mode": result.get("mode"),
            "explanation": result.get("explanation")
        }
    }
