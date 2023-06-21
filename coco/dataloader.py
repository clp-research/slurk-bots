from collections import defaultdict
from itertools import cycle
import json
import random


class Dataloader(list):
    def __init__(self, path, n, boards_per_level):
        self._path = path
        self._n = n
        self.boards_per_level = boards_per_level
        self.get_boards()

    def _read_board_file(self):
        """read boards and divide by level"""
        boards = defaultdict(list)
        with self._path.open('r', encoding="utf-8") as infile:
            for index, line in enumerate(infile, start=1):
                diff_level, link = line.strip().split("\t")
                boards[diff_level].append(link)

        return dict(sorted(boards.items()))

    def _sample_boards(self):
        self.clear()
        boards = self._read_board_file()

        for board_links in boards.values():
            for board in random.sample(board_links, self.boards_per_level):
                self.append(board)
                if len(self) == self._n:
                    return

    def get_boards(self):
        """sample random boards for a room"""
        self._sample_boards()
        random.shuffle(self)
