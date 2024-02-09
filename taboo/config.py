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
STARTING_POINTS = 0

TIMEOUT_TIMER = 1  # 5 minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 0.5  # 3 minutes if a user is alone in a room
WAITING_PARTNER_TIMER = 1.5  # 10 minutes a user waits for a partner

# base html messages with common colors
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"