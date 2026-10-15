import os
import json
import datetime
from typing import Dict, Any

try:
    from google.cloud import logging as cloud_logging
    GCP_SDK_AVAILABLE = True
except ImportError:
    GCP_SDK_AVAILABLE = False

class AfroShopGCPLogger:
    """Gestionnaire de télémétrie et d'envoi vers Google Cloud Logging."""

    def __init__(self, project_id: str = "Afroshop-cloud-lab", log_name: str = "afroshop-security-audit"):
        self.project_id = project_id
        self.log_name = log_name
        self.client = None
        self.logger = None

        if GCP_SDK_AVAILABLE:
            try:
                self.client = cloud_logging.Client(project=self.project_id)
                self.logger = self.client.logger(self.log_name)
            except Exception:
                # Si pas d'identifiants ADC configurés localement, bascule sur le mode fichier d'audit
                self.client = None

    def log_security_event(self, event_data: Dict[str, Any], prompt_snippet: str = "") -> Dict[str, Any]:
        """Écrit un log de sécurité structuré vers GCP ou en local."""
        severity = "INFO"
        if event_data.get("verdict") == "BLOCKED":
            severity = "CRITICAL" if event_data.get("threat_level") == "CRITICAL" else "WARNING"

        payload = {
            "service": "afroshop-ai-guard",
            "timestamp": event_data.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            "verdict": event_data.get("verdict"),
            "threat_level": event_data.get("threat_level"),
            "attack_vector": event_data.get("attack_vector"),
            "risk_score": event_data.get("risk_score"),
            "prompt_snippet": prompt_snippet[:100],
            "explanation": event_data.get("explanation"),
        }

        # Envoi via l'API GCP si connectée
        if self.logger:
            try:
                self.logger.log_struct(payload, severity=severity)
                return {"status": "SENT_TO_GCP", "payload": payload}
            except Exception as e:
                pass

        # Fallback local : enregistrement dans le journal d'audit JSONL
        local_log_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(local_log_dir, exist_ok=True)
        local_log_path = os.path.join(local_log_dir, "live_audit_logs.jsonl")
        
        full_entry = {
            "logName": f"projects/{self.project_id}/logs/{self.log_name}",
            "severity": severity,
            "timestamp": payload["timestamp"],
            "jsonPayload": payload
        }
        
        with open(local_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(full_entry, ensure_ascii=False) + "\n")

        return {"status": "LOCAL_SAVED", "payload": full_entry}
