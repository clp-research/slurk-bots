# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROLIFIC_URL = "https://app.prolific.co/submissions/complete?cc="


# Set this seed to make the random process reproducible.
SEED = None



# Whether the bot runs a public version or not
# - This influences the kind of goodbye message
# - Public data collections will not get a token but a tweetable message
# - Set this to False when running data collections with AMT, Prolific, or similar
# - Individual tokens will be generated when this is False
# - PLATFORM influences how the confirmation token will be supplied
# - For Prolific, participants will receive a link
# - For AMT, participants will get a token to copy
PUBLIC = False
PLATFORM = "Prolific"

# All below *TIME_* variables are in minutes.
# They indicate how long a situation has to persist for something to happen.

TIME_LEFT = 5  # how many minutes a user can stay in a room before closing it
TIME_WAITING = 10  # how many minutes a user can wait for a partner
TIME_ROUND = 20  # how many minutes users can play on a single image

# colored messages
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"

TASK_TITLE = "Find the word."

# with open(
#     os.path.join(ROOT, "wordle_boards", "data", "task_description.txt"), "r", encoding="utf-8"
# ) as f:
#     TASK_DESCR =  f.read()

WORD_LIST = os.path.join(ROOT, "wordle_boards", "data", "wordlist.txt")

with open(os.path.join(ROOT, "wordle_boards", "data", "task_greeting.txt"), "r", encoding="utf-8") as f:
    TASK_GREETING = f.read().split("\n\n\n")


WORDLE_WORDS = f"{ROOT}/wordle_boards/data/wordle_words.json"
WORDS_PER_ROOM = 3  # -1 to load entire dataset