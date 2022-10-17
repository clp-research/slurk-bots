# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

from pathlib import Path

ROOT = Path().resolve() #os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


TASK_GREETING = Path(f"{ROOT}/ccbts/data/task_greeting.txt").read_text().strip().split("\n\n")

INSTRUCTIONS = dict(
    player=Path(f"{ROOT}/ccbts/data/instruction_player.txt").read_text().strip(),
    wizard=Path(f"{ROOT}/ccbts/data/instruction_wizard.txt").read_text().strip()
)

IMGS = [image for image in Path(f"{ROOT}/ccbts/data/images").iterdir()]
