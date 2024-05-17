from itertools import cycle
import json
import random


class Dataloader(list):
    def __init__(self, path, n):
        self._path = path
        self._n = n
        self.get_boards()

    def _sample_boards(self):
        self.clear()
        board_ids = set()
        board_ids = set()
        boards = self._read_board_file()
        images_per_level = self._n // 3

        for level in cycle(["easy", "medium", "hard"]):
            if boards.get(level):
                for board in random.sample(boards[level], images_per_level):
                    state_id = board["state"]["state_id"]

                    if state_id not in board_ids:
                        self.append(board)
                        board_ids.add(state_id)
                    state_id = board["state"]["state_id"]

                    if state_id not in board_ids:
                        self.append(board)
                        board_ids.add(state_id)

                    if len(self) == self._n:
                        return

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

        # load entire dataset
        # load entire dataset
        if self._n == -1:
            self._n = index        

        return boards

    def get_boards(self):
        """sample random boards for a room"""
        self._sample_boards()
        random.shuffle(self)


if __name__ == "__main__":
    from pathlib import Path
    d = Dataloader(Path("data/boards.jsonl"), 29)

