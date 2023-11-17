from pathlib import Path

ROOT = Path(__file__).parent.resolve()

wordlist = Path(f"{ROOT}/data/taboo_words.json")
all_words = Path(f"{ROOT}/data/instances.json")

task_description = Path(f"{ROOT}/data/task_description.txt")

TASK_TITLE = "Guess the taboo word."
TASK_INSTRUCTIONS = "YOU GET THE SAME INSTRUCTIONS."