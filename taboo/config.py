from pathlib import Path

ROOT = Path(__file__).parent.resolve()

wordlist = Path(f"{ROOT}/data/taboo_words.json")
all_words = Path(f"{ROOT}/data/instances.json")

guesser_task_description = Path(f"{ROOT}/data/guesser_task_description.txt")
explainer_task_description = Path(f"{ROOT}/data/explainer_task_description.txt")

TASK_TITLE = "Guess or explain the taboo word."
TASK_INSTRUCTIONS = "YOU GET THE SAME INSTRUCTIONS."