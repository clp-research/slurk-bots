import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


with open(os.path.join(ROOT, "wordle_words", "data", "initial_guesser_prompt.txt"), "r") as my_f:
    GUESSER_PROMPT = my_f.read()

WORDLE_WORDS = f"{ROOT}/wordle_words/data/wordle_words.json"
WORDS_PER_ROOM = 3  # -1 to load entire dataset