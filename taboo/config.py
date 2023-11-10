import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "taboo", "data", "taboo_words.json"), "r") as f:
    TABOO_WORDS = json.load(f)