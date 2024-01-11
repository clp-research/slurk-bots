from collections import defaultdict
from itertools import cycle
import json
import random

import requests

from .config import *


class Dataloader(list):
    def __init__(self, path):
        self.path = path
        self.get_boards()

    def get_instructions_link(self, state_id):
        state_mapping = requests.get(f"{self.base_link}/{state_id}.json")

        # no extra instructions for this state
        if not state_mapping.ok:
            return {"player": [], "wizard": []}

        state_mapping = state_mapping.json()

        return dict(
            player=[f"{self.base_link}/{i}" for i in state_mapping["player"]],
            wizard=[f"{self.base_link}/{i}" for i in state_mapping["wizard"]],
        )

    def read_boards(self):
        all_sequences = list(self.path.iterdir())
        sequences = random.sample(all_sequences, SEQUENCES_PER_ROOM)

        for i, sequence in enumerate(sequences):
            buffer = defaultdict(list)
            with sequence.open(encoding="utf-8") as infile:
                for line in infile:
                    board = json.loads(line)
                    level = int(board["level"])
                    buffer[level].append(board)

                sorted_dict = dict(sorted(buffer.items()))

                for level, boards in sorted_dict.items():
                    board = random.choice(boards)
                    self.append(
                        (board["state"], board["instructions"])
                    )

                    # switch roles ar the end of the sequence except for the last one
                    if i != len(sequences) - 1:
                        self.append("switch")

    def get_boards(self):
        """sample random boards for a room"""
        self.read_boards()
        # random.shuffle(self)
