# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

from pathlib import Path

ROOT = Path().resolve() #os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


TASK_GREETING = Path(f"{ROOT}/ccbts/data/task_greeting.txt").read_text().strip().split("\n\n")

INSTRUCTIONS = dict(
    player=Path(f"{ROOT}/ccbts/data/instruction_player.txt").read_text().strip(),
    wizard=Path(f"{ROOT}/ccbts/data/instruction_wizard.txt").read_text().strip()
)

# IMGS = [image for image in Path(f"{ROOT}/ccbts/data/images").iterdir()]
IMGS = [
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/parallel_bridges.jpg",
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/square_bridges.jpg",
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/stack_bridges_nuts.jpg",
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/stack_nuts_screws.jpg",
    "https://raw.githubusercontent.com/sebag90/ccbts_imgs/main/stack_nuts_washers_screws.jpg"
]


COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"


TIME_LEFT = 5  # how many minutes a user can stay in a room before closing it