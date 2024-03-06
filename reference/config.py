

from pathlib import Path

ROOT = Path(__file__).parent.resolve()
# # with open(os.path.join(ROOT, "taboo", "data", "taboo_words.json"), "r") as f:
# #     words = json.load(f)
# #
# # TABOO_WORDS = {key.lower(): [word.lower() for word in value] for key, value in words.items()}
#
# with open(os.path.join(ROOT, "taboo", "data", "intitial_explainer_prompt.txt"), "r") as my_file:
#     EXPLAINER_PROMPT = my_file.read()
#
# with open(os.path.join(ROOT, "taboo", "data", "initial_guesser_prompt.txt"), "r") as my_f:
#     GUESSER_PROMPT = my_f.read()
#
# LEVEL_WORDS = f"{ROOT}/taboo/data/level_words.json"
# WORDS_PER_ROOM = 6  # -1 to load entire dataset
# with open(Path(f"{ROOT}/data/grid.html")) as html_f:
with open(Path(f"{ROOT}/data/explainer_instr.html")) as html_explainer:
    EXPLAINER_HTML = html_explainer.read()

with open(Path(f"{ROOT}/data/guesser_instr.html")) as html_guesser:
    GUESSER_HTML = html_guesser.read()

with open(Path(f"{ROOT}/data/empty_grid.html")) as html_guesser:
    EMPTY_GRID = html_guesser.read()

# GRIDS = Path(f"{ROOT}/data/instances.json")
GRIDS = Path(f"{ROOT}/data/instances_unique.json")

# GRIDS_PER_ROOM = 4  # -1 to load entire dataset
GRIDS_PER_ROOM = 6  # -1 to load entire dataset

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