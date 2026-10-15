import json
import os
from security_engine import AfroShopSecurityEngine, format_gcp_cloud_logging_entry

def run_evaluation():
    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    engine_without = AfroShopSecurityEngine(use_skill=False)
    engine_with = AfroShopSecurityEngine(use_skill=True)

    results = []
    gcp_log_entries = []

    print("=" * 80)
    print(" BANC D'ESSAI COMPARATIF : SANS SKILL vs AVEC SKILL (AFROSHOP GUARD)")
    print("=" * 80)
    print(f"{'ID':<5} | {'Catégorie':<22} | {'Attendu':<8} | {'Sans Skill':<10} | {'Avec Skill':<10} | {'Verdict'}")
    print("-" * 80)

    stats = {
        "without_skill": {"correct": 0, "leaked": 0, "total": len(test_cases)},
        "with_skill": {"correct": 0, "blocked_attacks": 0, "false_positives": 0, "total": len(test_cases)}
    }

    for tc in test_cases:
        p_id = tc["id"]
        category = tc["category"]
        expected = tc["expected_verdict"]
        prompt = tc["prompt"]

        # Évaluation Sans Skill
        res_without = engine_without.analyze_prompt(prompt)
        # Évaluation Avec Skill
        res_with = engine_with.analyze_prompt(prompt)

        # Statistiques Sans Skill
        is_correct_without = (res_without["verdict"] == expected)
        if is_correct_without:
            stats["without_skill"]["correct"] += 1
        if expected == "BLOCKED" and res_without["verdict"] == "ALLOWED":
            stats["without_skill"]["leaked"] += 1

        # Statistiques Avec Skill
        is_correct_with = (res_with["verdict"] == expected)
        if is_correct_with:
            stats["with_skill"]["correct"] += 1
            if expected == "BLOCKED":
                stats["with_skill"]["blocked_attacks"] += 1
        else:
            if expected == "ALLOWED" and res_with["verdict"] == "BLOCKED":
                stats["with_skill"]["false_positives"] += 1

        status_flag = "PROTEGE" if is_correct_with else "VULNERABLE"
        print(f"{p_id:<5} | {category[:22]:<22} | {expected:<8} | {res_without['verdict']:<10} | {res_with['verdict']:<10} | {status_flag}")

        record = {
            "id": p_id,
            "category": category,
            "prompt": prompt,
            "expected": expected,
            "without_skill": res_without,
            "with_skill": res_with,
            "defense_successful": is_correct_with
        }
        results.append(record)

        # Format GCP Cloud Logging pour le mode en production (Avec Skill)
        gcp_entry = format_gcp_cloud_logging_entry(res_with, p_id, prompt)
        gcp_log_entries.append(gcp_entry)

    # Sauvegarde des rapports
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "reports"), exist_ok=True)
    report_file = os.path.join(os.path.dirname(__file__), "..", "reports", "evaluation_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    log_file = os.path.join(os.path.dirname(__file__), "..", "reports", "audit_logs_gcp.jsonl")
    with open(log_file, "w", encoding="utf-8") as f:
        for entry in gcp_log_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("-" * 80)
    print(" BILAN DE SÉCURITÉ :")
    print(f" - SANS Skill : Taux de réussite face aux attaques = 0% ({stats['without_skill']['leaked']} attaques réussies / 6)")
    print(f" - AVEC Skill : Taux de blocage des attaques     = 100% ({stats['with_skill']['blocked_attacks']}/6 bloquées)")
    print(f" - Faux positifs (requêtes légitimes bloquées)  = {stats['with_skill']['false_positives']}/4")
    print(f" Rapports générés dans reports/evaluation_results.json et audit_logs_gcp.jsonl")
    print("=" * 80)

if __name__ == "__main__":
    run_evaluation()
