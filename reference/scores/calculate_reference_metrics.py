import os
import json
import numpy as np

from scores.process_logs import build_interactions, select_logs
from scores.compute_scores import compute_scores


def get_human_expressions(in_folder, output_file):
    references_per_grids = {}
    files = [
        f
        for f in os.listdir(in_folder)
        if os.path.isfile(in_folder + os.sep + f) and f.endswith(".json")
    ]
    for file in files:
        with open(os.path.join(f"{in_folder}/{file}"), "r") as f:
            logs = json.load(f)
            interactions = build_interactions(logs)
            for episode in interactions[0]:
                type = episode["turns"][0][0]["action"]["content"]
                id = episode["turns"][0][2]["action"]["content"]
                clue = episode["turns"][0][3]["action"]["content"]
                if type in references_per_grids:
                    if id not in references_per_grids[type]:
                        references_per_grids[type][id] = [clue]
                    else:
                        references_per_grids[type][id].append(clue)
                else:
                    references_per_grids[type] = {}
                    references_per_grids[type][id] = [clue]

    with open(output_file, "w", encoding="utf8") as json_file:
        json.dump(references_per_grids, json_file, indent=4, ensure_ascii=False)


def calculate_human_scores(folder, results_file):
    room_scores = {}
    files = [
        f
        for f in os.listdir(folder)
        if os.path.isfile(folder + os.sep + f) and f.endswith(".json")
    ]
    for file in files:
        room = file[:4]
        with open(os.path.join(f"{folder}/{file}"), "r") as f:
            logs = json.load(f)
            interactions = build_interactions(logs)
            room_scores[room] = {}
            for episode in interactions[0]:
                scores = compute_scores(episode)
                grid_type = scores["grid type"]
                inst_id = scores["instance id"]
                scores_only = {
                    key: val
                    for key, val in scores.items()
                    if key != "grid type" and key != "instance id"
                }
                if grid_type in room_scores[room]:
                    room_scores[room][grid_type][inst_id] = scores_only
                else:
                    room_scores[room][grid_type] = {}
                    room_scores[room][grid_type][inst_id] = scores_only

    with open(results_file, "w", encoding="utf8") as json_file:
        json.dump(room_scores, json_file, indent=4, ensure_ascii=False)

    return room_scores


def compute_average_scores(raw_scores, score_name, per_grid_type=True):
    if per_grid_type:
        scores_per_grid = {}
        for room, grid_types in raw_scores.items():
            for grid, instances in grid_types.items():
                if grid in scores_per_grid:
                    scores_per_grid[grid].extend(
                        [
                            inst_id["episode_scores"][score_name]
                            for inst_id in instances.values()
                        ]
                    )
                else:
                    scores_per_grid[grid] = [
                        inst_id["episode_scores"][score_name]
                        for inst_id in instances.values()
                    ]
        return {
            key: round(np.mean(values), 2) for key, values in scores_per_grid.items()
        }

    else:
        scores_per_room = {}
        for room, grid_types in raw_scores.items():
            room_scores = [[
                value["episode_scores"][score_name]
                for inst_id in grid_types.values()
                for value in inst_id.values()
            ]]
            scores_per_room[room] = round(np.mean(room_scores), 2)
        return f"{score_name}: {scores_per_room}"


def get_instances(scores):
    episode_instances = {}
    for room, grid_types in scores.items():
        for grid, instances in grid_types.items():
            if grid in episode_instances:
                new_inst = [
                    inst for inst in instances if inst not in episode_instances[grid]
                ]
                episode_instances[grid].extend(new_inst)
            else:
                episode_instances[grid] = [inst for inst in instances]
    return episode_instances


def get_model_scores(episodes, folder, output_file):
    model_scores = {key: {} for key in episodes}
    for path, directories, files in os.walk(folder):
        files = [os.path.join(path, file) for file in files if "scores.json" in file]
        for f in files:
            info = f.split("/")
            frequency_type = info[-3][2:]
            instance = str(int(info[-2].split("_")[-1]))
            if instance in episodes[frequency_type]:
                with open(f, "r") as file:
                    scores = json.load(file)
                    model_scores[frequency_type][instance] = scores
    with open(output_file, "w", encoding="utf8") as json_file:
        json.dump(model_scores, json_file, indent=4, ensure_ascii=False)
    return model_scores


def compute_model_average_scores(raw_scores, score_name):
    scores_per_grid = {}
    for grid, instances in raw_scores.items():
        if grid in scores_per_grid:
            scores_per_grid[grid].extend(
                [
                    inst_id["episode scores"][score_name]
                    for inst_id in instances.values()
                ]
            )
        else:
            scores_per_grid[grid] = [
                inst_id["episode scores"][score_name] for inst_id in instances.values()
            ]
    return {key: round(np.mean(values), 2) for key, values in scores_per_grid.items()}


def compute_main_score(raw_scores, human=True):
    scores = []
    if human:
        for room, grid_types in raw_scores.items():
            scores.extend(
                [
                    value["episode_scores"]["Main Score"]
                    for inst_id in grid_types.values()
                    for value in inst_id.values()
                ]
            )
    else:
        for grid_types, instances in raw_scores.items():
            scores.extend(
                [value["episode scores"]["Main Score"] for value in instances.values()]
            )
    return f"Main Score {round(np.mean(scores), 2)}"


if __name__ == "__main__":
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # root = ".../slurk-bots/reference"

    logs_folder = f"{ROOT}/selected_logs/reference"
    model_folder = f"{ROOT}/scores/gpt-4-0613-t0.0--gpt-4-0613-t0.0/referencegame"

    get_human_expressions(logs_folder, "human_expressions.json")

    # calculate scores
    human_scores = calculate_human_scores(logs_folder, "human_scores.json")
    instances = get_instances(human_scores)
    model_scores = get_model_scores(instances, model_folder, "model_scores.json")

    # calculate Main Score on average
    print(compute_main_score(human_scores, human=True))
    print(compute_main_score(model_scores, human=False))

    # calculate metrics per room
    print(compute_average_scores(human_scores, "Main Score", per_grid_type=False))
    print(
        compute_average_scores(
            human_scores, "Average Generated Expression Length", per_grid_type=False
        )
    )
    # print(compute_average_scores(human_scores, "Average Generated Expression Number of Tokens", per_grid_type=False))
