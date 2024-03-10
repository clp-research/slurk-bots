# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

from pathlib import Path

ROOT = Path(__file__).parent.resolve()

TIME_WAITING_ROOM = 5  # how many minutes a user can wait for a partner
TIMEOUT_TIMER = 5  # minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 3  # minutes if a user is alone in a room/both users left

# colored messages
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"

with open(Path(f"{ROOT}/data/task_description.txt")) as f:
    TASK_DESCR = f.read().split("\n\n\n")

ALL_WORDS = Path(f"{ROOT}/data/wordlist.txt")
with open(ALL_WORDS) as infile:
    VALID_WORDS = set((line.strip()) for line in infile)

with open(Path(f"{ROOT}/data/task_greeting.txt")) as f:
    TASK_GREETING = f.read().split("\n\n\n")

WORDLE_WORDS = Path(f"{ROOT}/data/instances.json")

WORDS_HIGH_N, WORDS_MED_N = 1, 2  # -1 to load entire dataset

with open(Path(f"{ROOT}/data/guesser_instr.html")) as html_f:
    GUESSER_HTML = html_f.read()

with open(Path(f"{ROOT}/data/critic_instr.html")) as html_f1:
    CRITIC_HTML = html_f1.read()

with open(Path(f"{ROOT}/data/clue_mode.txt")) as f3:
    CLUE_MODE = f3.read()

with open(Path(f"{ROOT}/data/critic_mode.txt")) as f4:
    CRITIC_MODE = f4.read()

INPUT_FIELD_UNRESP_CRITIC = "Wait for the guess proposal"
INPUT_FIELD_UNRESP_GUESSER = "You can't send messages, you can only get them"