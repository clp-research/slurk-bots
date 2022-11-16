# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

from pathlib import Path

ROOT = Path().resolve() #os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


TASK_GREETING = Path(f"{ROOT}/golmieval/data/task_greeting.txt").read_text().strip().split("\n\n")
TASK_INSTR = Path(f"{ROOT}/golmieval/data/instruction.txt").read_text().strip()


BOARDS = Path(f"{ROOT}/golmieval/data/boards.jsonl")
BOARDS_PER_ROOM = 9


COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"


TYPES = "https://raw.githubusercontent.com/clp-research/golmi/exp-descrimage/app/descrimage/static/types.png"
