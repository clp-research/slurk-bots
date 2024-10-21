import json
import logging
import os
import random
from pathlib import Path

LOG = logging.getLogger(__name__)


# class GridManager:
#     def __init__(self, root_path):
#         self.root_path = Path(root_path)
#         self.json_files = self._get_json_files()
#         self.all_grids = self._load_all_grids()
#
#     def _get_json_files(self):
#         return [file for file in os.listdir(self.root_path) if file.endswith('.json')]
#
#     def _load_all_grids(self):
#         all_grids = []
#         for json_file in self.json_files:
#             file_path = self.root_path / json_file
#             with open(file_path, 'r') as file:
#                 json_content = json.load(file)
#                 target_grid = json_content.get('target_grid')
#                 if target_grid:
#                     all_grids.append(target_grid)
#         return all_grids
#
#     def get_random_grid(self):
#         if self.all_grids:
#             random_grid = random.choice(self.all_grids)
#             index = self.all_grids.index(random_grid)
#             random_file = self.json_files[index]
#             LOG.debug(f"Randomly Chosen File: {random_file}, randomly Chosen Grid: {random_grid}")
#             return random_grid
#         else:
#             LOG.debug("No JSON files found in the directory.")
#             return None
#
#     def remove_grid(self, grid):
#         if grid in self.all_grids:
#             index = self.all_grids.index(grid)
#             random_file = self.json_files[index]
#             LOG.debug(f"File {random_file} has been removed.")
#             # Remove the chosen grid from the list
#             self.all_grids.pop(index)
#         else:
#             LOG.debug("Grid not found in the list.")


class GridManager:
    def __init__(self, file_path, experiment_name):
        self.file_path = file_path
        self.experiment_name = experiment_name
        self.all_grids = self._load_all_grids()

    def _load_all_grids(self):
        all_grids = []
        with open(self.file_path, 'r') as file:
            data = json.load(file)
            for experiment in data['experiments']:
                if experiment['name'] == self.experiment_name:
                    game_instances = experiment['game_instances']
                    for instance in game_instances:
                        target_grid = instance.get('target_grid')
                        if target_grid:
                            all_grids.append(target_grid)
        return all_grids

    def get_random_grid(self):
        if self.all_grids:
            random_grid = random.choice(self.all_grids)
            logging.debug(f"Randomly Chosen Grid: {random_grid}")
            return random_grid
        else:
            logging.debug("No grids found for the specified experiment.")
            return None

    def remove_grid(self, grid):
        if grid in self.all_grids:
            self.all_grids.remove(grid)
            logging.debug("Grid has been removed.")
        else:
            logging.debug("Grid not found in the list.")


