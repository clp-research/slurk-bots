# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to a comma separated (csv) file with two columns.
# Each column containing the url to one image file.
DATA_PATH = os.path.join(ROOT, "data", "image_data.tsv")
WORD_LIST = os.path.join(ROOT, "data", "wordlist.txt")

# This many game rounds will be played per room and player pair.
N = 3
# Set this seed to make the random process reproducible.
SEED = None
# Whether to randomly sample images or present them in linear order.
SHUFFLE = True
# What mode the game uses for showing images. one of "same", "different", "one_blind"
GAME_MODE = "one_blind"

# All below *TIME_* variables are in minutes.
# They indicate how long a situation has to persist for something to happen.

TIME_LEFT = 5  # how many minutes a user can stay in a room before closing it
TIME_ROUND = 15  # how many minutes users can play on a single image

# colored messages
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"

TASK_TITLE = "Find the word."

with open(
    os.path.join(ROOT, "data", "task_description.txt"), "r", encoding="utf-8"
) as f:
    TASK_DESCR = f.read()

with open(os.path.join(ROOT, "data", "task_greeting.txt"), "r", encoding="utf-8") as f:
    TASK_GREETING = f.read().split("\n\n\n")
