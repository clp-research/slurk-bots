from pathlib import Path

ROOT = Path(__file__).parent.resolve()

with open(Path(f"{ROOT}/data/explainer_instr.html")) as html_explainer:
    EXPLAINER_HTML = html_explainer.read()

with open(Path(f"{ROOT}/data/guesser_instr.html")) as html_guesser:
    GUESSER_HTML = html_guesser.read()

with open(Path(f"{ROOT}/data/empty_grid.html")) as html_guesser:
    EMPTY_GRID = html_guesser.read()

GRIDS = Path(f"{ROOT}/data/instances_unique.json")

GRIDS_PER_ROOM = 6

COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"

with open(Path(f"{ROOT}/data/task_greeting.txt"), "r", encoding="utf-8") as f:
    TASK_GREETING = f.read().split("\n\n\n")

TIMEOUT_TIMER = 5  # minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 3  # minutes if a user is alone in a room/both users left
WAITING_ROOM_TIMER = 5 # minutes if a user is waiting for the other player


INPUT_FIELD_UNRESP_GUESSER = "You can't send messages, you can only get them"
INPUT_FIELD_UNRESP_EXPLAINER = "Wait for your partner's choice"