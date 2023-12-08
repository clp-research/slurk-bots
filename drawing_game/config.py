# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

TASK_DESCR_A = Path(f"{ROOT}/data/task_description_player_A.txt").read_text()
TASK_DESCR_B = Path(f"{ROOT}/data/task_description_player_B.txt").read_text()
TASK_GREETING = Path(f"{ROOT}/data/task_greeting.txt")

TASK_TITLE = "Describe the grid to your partner and see how what they draw matches."



