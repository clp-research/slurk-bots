from pathlib import Path

ROOT = Path(__file__).parent.resolve()

wordlist = Path(f"{ROOT}/data/taboo_words.json")
all_words = Path(f"{ROOT}/data/instances.json")