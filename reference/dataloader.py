import json
import random


class Dataloader(list):
    def __init__(self, path, n):
        self._path = path
        self._n = n
        self.get_grids()

    def _sample_grids(self):
        # for this data we can just take 3 random grids in each level, right?
        self.clear()
        grids_per_level = self._n // 2
        grids_instances = self._read_grids_file()
        for dif_level in grids_instances["experiments"]:
            level_grids = random.sample(dif_level['game_instances'], grids_per_level)
            for grid in level_grids:
                filtered_grid = [(key, preprocess(value)) for key, value in grid.items() if "grid" in key]
                filtered_grid.append(("level", dif_level["name"]))
                self.append(filtered_grid)
        return

    def _read_grids_file(self):
        """read boards and divide by level"""
        with open(self._path, "r") as f:
            grid_instances = json.load(f)
        return grid_instances

    def get_grids(self):
        """sample random grids for a room"""
        self._sample_grids()
        random.shuffle(self)


def preprocess(grid):
    if grid in ["first", "second", "third"]:
        # it is not a grid, but the answer which grid is the target
        return grid
    preprocessed_grid = grid.split("\n")
    return [row.split(" ") for row in preprocessed_grid]



# if __name__ == "__main__":
#     from pathlib import Path
#     d = Dataloader(Path("data/instances.json"), n=4)
#     print(d[0][-1][1])

