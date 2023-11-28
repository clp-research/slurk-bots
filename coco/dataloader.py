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
        sequences = list(self.path.iterdir())
        random.shuffle(sequences)
        for sequence in sequences:
            with sequence.open(encoding="utf-8") as infile:
                for line in infile:
                    board = json.loads(line)
                    self.append(
                        (board["state"],
                        board["instructions"])
                    )
                    self.append("switch")


        if self[-1] == "switch":
            self.pop()

    def get_boards(self):
        """sample random boards for a room"""
        self.read_boards()
        # random.shuffle(self)
