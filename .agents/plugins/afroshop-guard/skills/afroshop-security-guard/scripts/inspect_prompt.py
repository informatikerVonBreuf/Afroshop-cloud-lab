#!/usr/bin/env python3
"""
Script d'inspection rapide d'un prompt utilisateur pour le skill AfroShop Security Guard.
Usage : python inspect_prompt.py "mon prompt"
"""
import sys
import os
import json

# Résolution des imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src")))
from security_engine import AfroShopSecurityEngine

def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_prompt.py <PROMPT>")
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    engine = AfroShopSecurityEngine(use_skill=True)
    verdict = engine.analyze_prompt(prompt)

    print(json.dumps(verdict, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
