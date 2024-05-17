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
        levels_data = self._read_board_file()
        for level_data in levels_data["experiments"]:
            level_name = level_data["name"]
            game_instances = level_data["game_instances"]
            random_games = random.sample(game_instances, min(len(game_instances), words_per_level))
            for game in random_games:
                target_word = game["target_word"]
                related_words = game["related_word"]
                self.append({"target_word": target_word, "related_word": related_words, "level": level_name})
        return self

    def _read_board_file(self):
        """read boards and divide by level"""
        with open(self._path, "r") as f:
            word_instances = json.load(f)
        return word_instances

    def get_boards(self):
        """sample random boards for a room"""
        self._sample_boards()
        random.shuffle(self)
