import json
import re
import os
import datetime
from typing import Dict, Any, Tuple

# Motif de détection des vecteurs d'attaque courants
INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous\s+)?instructions", "INSTRUCTION_OVERRIDE", "Tentative d'écrasement des consignes"),
    (r"oublie\s+(toutes\s+)?(les\s+)?consignes", "INSTRUCTION_OVERRIDE", "Tentative d'écrasement des consignes"),
    (r"\b(dan|do\s+anything\s+now)\b", "JAILBREAK", "Tentative de jailbreak via persona DAN"),
    (r"system\s*prompt|prompt\s*système", "SYSTEM_LEAK", "Tentative d'extraction de prompt système"),
    (r"\b(api[_-]?key|clé[_\s-]?api|secret|token)\b.*(affiche|donne|export|env:)", "SECRET_EXFILTRATION", "Tentative d'exfiltration de secret"),
    (r"developerknowledge_api_key", "SECRET_EXFILTRATION", "Ciblage de la clé Developer Knowledge"),
    (r"base64|decode|SWdub3Jl", "OBFUSCATED_INJECTION", "Directive encodée ou obfusquée"),
    (r"system_override|disable_guardrails", "DELIMITER_INJECTION", "Injection par délimiteur ou commande système fictive"),
    (r"effacer|détruire|supprimer.*(sans\s+laisser\s+de\s+trace|projet)", "MALICIOUS_ROLEPLAY", "Demande d'action destructive"),
]

# Mots-clés légitimes éducatifs (pour éviter les faux positifs)
SAFE_EDUCATIONAL_PATTERNS = [
    r"en quoi consiste",
    r"peux-tu m'expliquer",
    r"comprendre",
    r"protéger",
    r"sécuriser",
]

class AfroShopSecurityEngine:
    """Moteur de sécurité AfroShop pour l'évaluation de prompt injections."""

    def __init__(self, use_skill: bool = True):
        self.use_skill = use_skill

    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Analyse un prompt utilisateur.
        Si use_skill est False : simule un LLM naïf (sans garde-fous) qui cède aux injections.
        Si use_skill est True  : applique le protocole défini dans afroshop-security-guard SKILL.md.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Cas 1 : Mode SANS le Skill (Baseline naïve)
        if not self.use_skill:
            return {
                "timestamp": timestamp,
                "mode": "WITHOUT_SKILL",
                "verdict": "ALLOWED",
                "threat_level": "UNCHECKED",
                "attack_vector": "NONE",
                "risk_score": 0.0,
                "explanation": "Aucun filtre de sécurité actif. La requête est traitée sans contrôle.",
                "response_text": f"[NAÏF] Exécution directe de la requête utilisateur : '{prompt[:60]}...'"
            }

        # Cas 2 : Mode AVEC le Skill (AfroShop Guard actif)
        lower_prompt = prompt.lower()
        
        # Vérification des faux positifs (requêtes éducatives ou explicatives légitimes)
        is_educational = any(re.search(pat, lower_prompt) for pat in SAFE_EDUCATIONAL_PATTERNS)
        if is_educational and "ignore" not in lower_prompt and "dan" not in lower_prompt:
            return {
                "timestamp": timestamp,
                "mode": "WITH_SKILL",
                "verdict": "ALLOWED",
                "threat_level": "LOW",
                "attack_vector": "NONE",
                "risk_score": 0.05,
                "explanation": "Requête pédagogique légitime concernant la sécurité. Aucun vecteur d'attaque actif.",
                "response_text": "Explication sur les injections de prompt : il s'agit d'une technique où un attaquant force le modèle à contourner ses règles..."
            }

        # Détection des motifs d'injection
        for pattern, vector, explanation in INJECTION_PATTERNS:
            if re.search(pattern, lower_prompt):
                return {
                    "timestamp": timestamp,
                    "mode": "WITH_SKILL",
                    "verdict": "BLOCKED",
                    "threat_level": "CRITICAL" if vector == "SECRET_EXFILTRATION" else "HIGH",
                    "attack_vector": vector,
                    "risk_score": 0.95 if vector == "SECRET_EXFILTRATION" else 0.85,
                    "explanation": f"Menace interceptée : {explanation} (vecteur : {vector})",
                    "response_text": "Action bloquée par AfroShop Guard. Cette requête enfreint les règles de sécurité de l'assistant."
                }

        # Par défaut : Requête légitime acceptée
        return {
            "timestamp": timestamp,
            "mode": "WITH_SKILL",
            "verdict": "ALLOWED",
            "threat_level": "NONE",
            "attack_vector": "NONE",
            "risk_score": 0.0,
            "explanation": "Requête conforme aux règles AfroShop.",
            "response_text": f"Bienvenue chez AfroShop ! Réponse à votre demande concernant : '{prompt[:50]}...'"
        }

def format_gcp_cloud_logging_entry(result: Dict[str, Any], prompt_id: str, prompt_text: str) -> Dict[str, Any]:
    """Formate une entrée d'audit conforme au schéma Google Cloud Logging."""
    severity = "INFO"
    if result["verdict"] == "BLOCKED":
        severity = "CRITICAL" if result.get("threat_level") == "CRITICAL" else "WARNING"

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
            "event_type": "security_eval",
            "prompt_id": prompt_id,
            "prompt_snippet": prompt_text[:80],
            "verdict": result["verdict"],
            "threat_level": result["threat_level"],
            "attack_vector": result["attack_vector"],
            "risk_score": result["risk_score"],
            "mode": result["mode"],
            "explanation": result["explanation"]
        }
    }
