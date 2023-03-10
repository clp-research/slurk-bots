from itertools import cycle
import json
import random


class Dataloader(dict):
    def __init__(self, path, n):
        self._path = path
        self._n = n

    def _sample_boards(self):
        baords = self._read_board_file()
        images_per_level = self._n // 3
        sample = list()
        for level in cycle(["easy", "medium", "hard"]):
            for board in random.sample(baords[level], images_per_level):
                sample.append(board)

                if len(sample) == self._n:
                    return sample

    def _read_board_file(self):
        """read boards and divide by level"""
        boards = dict(
            easy=list(),
            medium=list(),
            hard=list()
        )
        with self._path.open('r', encoding="utf-8") as infile:
            for index, line in enumerate(infile, start=1):
                board = json.loads(line)
                level = board["board_info"]["difficoulty"]

                # select target
                state = board["state"]
                target_id = str(board["target"])
                target_obj = state["objs"][target_id]
                state["targets"][target_id] = target_obj

                boards[level].append(board)

        if self._n == -1:
            self._n = index        
        
        return boards

    def get_boards(self, room_id):
        """sample random boards for a room"""
        room_boards = self._sample_boards()
        random.shuffle(room_boards)
        self[room_id] = room_boards
