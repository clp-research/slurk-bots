import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(ROOT, "taboo", "data", "intitial_explainer_prompt.txt"), "r") as my_file:
    EXPLAINER_PROMPT = my_file.read()

with open(os.path.join(ROOT, "taboo", "data", "initial_guesser_prompt.txt"), "r") as my_f:
    GUESSER_PROMPT = my_f.read()

LEVEL_WORDS = f"{ROOT}/taboo/data/instances.json"
WORDS_PER_ROOM = 6  # -1 to load entire dataset
STARTING_POINTS = 0

TIMEOUT_TIMER = 5  # 5 minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 3  # 3 minutes if a user is alone in a room
WAITING_PARTNER_TIMER = 10  # 10 minutes a user waits for a partner

# base html messages with common colors
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"