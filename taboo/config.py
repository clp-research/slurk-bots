import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# with open(os.path.join(ROOT, "taboo", "data", "taboo_words.json"), "r") as f:
#     words = json.load(f)
#
# TABOO_WORDS = {key.lower(): [word.lower() for word in value] for key, value in words.items()}

with open(os.path.join(ROOT, "taboo", "data", "intitial_explainer_prompt.txt"), "r") as my_file:
    EXPLAINER_PROMPT = my_file.read()

with open(os.path.join(ROOT, "taboo", "data", "initial_guesser_prompt.txt"), "r") as my_f:
    GUESSER_PROMPT = my_f.read()

LEVEL_WORDS = f"{ROOT}/taboo/data/level_words.json"
WORDS_PER_ROOM = 6  # -1 to load entire dataset