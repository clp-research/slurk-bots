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

    def get_instructions_link(self, level):
        level_mapping = requests.get(
            f"{self.base_link}/{level}.json"
        ).json()

        return dict(
            player=[f"{self.base_link}/{i}" for i in level_mapping["player"]],
            wizard=[f"{self.base_link}/{i}" for i in level_mapping["wizard"]],
        )

    def read_boards(self):
        with self.path.open(encoding="utf-8") as infile:
            for i, line in enumerate(infile):

                instructions = self.get_instructions_link(i)
                self.append(
                    (json.loads(line), instructions)
                )

    def get_boards(self):
        """sample random boards for a room"""
        self.read_boards()
        #random.shuffle(self)
