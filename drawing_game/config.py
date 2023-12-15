# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

TASK_DESCR_A = Path(f"{ROOT}/data/task_description_player_A.txt")
TASK_DESCR_B = Path(f"{ROOT}/data/task_description_player_B.txt")
TASK_GREETING = Path(f"{ROOT}/data/task_greeting.txt")

TASK_TITLE = "Describe the grid to your partner and see how what they draw matches."

DATA_PATH = Path(f"{ROOT}/data/image_data.tsv")

GAME_INSTANCE = Path(f"{ROOT}/data/instance.json")

N = 1

GAME_MODE = "one_blind"

SEED = None
# Whether to randomly sample images or present them in linear order.
SHUFFLE = True


