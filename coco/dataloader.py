from collections import defaultdict
from itertools import cycle
import json
import random

import requests

from .config import *


class Dataloader(list):
    def __init__(self, path):
        self.path = path
        self.base_link = INSTRUCTION_BASE_LINK
        self.get_boards()

    def get_instructions_link(self, state_id):
        state_mapping = requests.get(f"{self.base_link}/{state_id}.json")

        # no extra instructions for this state
        if not state_mapping.ok:
            return {"player": [], "wizard": []}

        return dict(
            player=[f"{self.base_link}/{i}" for i in state_mapping["player"]],
            wizard=[f"{self.base_link}/{i}" for i in state_mapping["wizard"]],
        )

    def read_boards(self):
        # group all boards by difficoulty level
        mapping = defaultdict(list)
        with self.path.open(encoding="utf-8") as infile:
            for line in infile:
                level, board = line.strip().split("\t")
                board = json.loads(board)
                mapping[int(level)].append(board)

        # sort levels
        mapping = dict(sorted(mapping.items()))

        # sample boards
        added = 0
        for level in cycle(mapping.keys()):
            sample = random.sample(mapping[level], BOARDS_PER_LEVEL)
            for board in sample:
                state_id = board["state_id"]
                instructions = self.get_instructions_link(state_id)
                self.append((board, instructions))
                added += 1

                if added == BOARDS_PER_ROOM:
                    return

            self.append("switch")

    def get_boards(self):
        """sample random boards for a room"""
        self.read_boards()
        # random.shuffle(self)
