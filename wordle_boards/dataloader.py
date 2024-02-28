import json
import random


class Dataloader(list):
    def __init__(self, path, high_freq_n, mid_freq_n):
        self.high_freq_num = high_freq_n
        self.mid_freq_num = mid_freq_n
        self._path = path
        self.get_words()


    def _sample_words(self):
        # for this data we can just take 2 random words in each level, right?
        self.clear()
        word_instances = self._read_words_file()['experiments']
        level_instances = []
        for level in word_instances:
            if level["name"] == 'high_frequency_words_no_clue_no_critic':
                level_instances = random.sample(level["game_instances"],  self.high_freq_num)
            elif level["name"] == 'medium_frequency_words_no_clue_no_critic':
                level_instances = random.sample(level["game_instances"], self.mid_freq_num)
            self.extend(level_instances)
        return

    def _read_words_file(self):
        """read words and divide by level"""
        with open(self._path, "r") as f:
            word_instances = json.load(f)
        return word_instances

    def get_words(self):
        """sample random boards for a room"""
        self._sample_words()
        random.shuffle(self)


# if __name__ == "__main__":
#     from pathlib import Path
#     # d = Dataloader(Path("data/wordle_words.json"), n=3)
#     d = Dataloader(Path("data/instances_wordle_kranti.json"), 1, 2)
#     print(d)