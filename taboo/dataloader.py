import json
import random


class Dataloader(list):
    def __init__(self, path, n):
        self._path = path
        self._n = n
        self.get_boards()

    def _sample_boards(self):
        # for this data we can just take 2 random words in each level, right?
        self.clear()
        words_per_level = self._n // 3
        word_instances = self._read_board_file()
        for level in word_instances.keys():
            random_words = random.sample(list(word_instances[level]), words_per_level)
            for word in random_words:
                word['level'] = level
            self.extend(random_words)
        return

    def _read_board_file(self):
        """read boards and divide by level"""
        with open(self._path, "r") as f:
            word_instances = json.load(f)
        return word_instances

    def get_boards(self):
        """sample random boards for a room"""
        self._sample_boards()
        random.shuffle(self)
