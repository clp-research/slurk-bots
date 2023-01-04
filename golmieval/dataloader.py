from itertools import cycle
import json
import random


class Dataloader(dict):
    def __init__(self, path, n):
        self._path = path
        self._n = n
        self._images = None

    def _sample_boards(self):
        baords = self._read_board_file()
        images_per_level = self._n // 3
        sample = list()
        for level in cycle(["easy", "medium", "hard"]):
            for index in random.sample(baords[level], images_per_level):
                sample.append(index)

                if len(sample) == self._n:
                    return set(sample)            

    def _read_board_file(self):
        """read boards and divide by level"""
        boards = dict(
            easy=list(),
            medium=list(),
            hard=list()
        )
        with self._path.open('r', encoding="utf-8") as infile:
            for i, line in enumerate(infile):
                board = json.loads(line)
                level = board["board_info"]["difficoulty"]

                boards[level].append(i)

        return boards

    def get_boards(self, room_id):
        """sample random boards for a room"""
        indeces = self._sample_boards()
        room_boards = list()
        with self._path.open('r', encoding="utf-8") as infile:
            for i, line in enumerate(infile):
                if i in indeces:
                    board = json.loads(line)
                    # select target
                    state = board["state"]
                    target_id = str(board["target"])
                    target_obj = state["objs"][target_id]
                    state["targets"][target_id] = target_obj

                    room_boards.append(board)

        random.shuffle(room_boards)
        self[room_id] = room_boards
