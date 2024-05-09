import json
import os

LOGS_FOR_SCORES = [
    "clue",
    "guess",
    "correct guess",
    "false guess",
    "grid type",
    "target grid",
    "instance id",
]

SELECTED_LOGS = LOGS_FOR_SCORES + ["round", "turn", "confirmation_log", "player"]


def select_logs(root, in_folder, out_folder):
    for filename in os.listdir(f"{root}/{in_folder}"):
        filtered_logs = []
        if filename.endswith("jsonl"):
            file = os.path.join(f"{root}/{in_folder}", filename)
            with open(file, "r") as f:
                json_list = list(f)
                for json_str in json_list:
                    log = json.loads(json_str)
                    if log["event"] in SELECTED_LOGS:
                        filtered_logs.append(log)
                new_logs_file = f"{root}/{out_folder}/{filename[:-1]}"
                with open(new_logs_file, "w", encoding="utf8") as json_file:
                    json.dump(filtered_logs, json_file, indent=4, ensure_ascii=False)
                print(f"Filtered logs saved in {new_logs_file}")
    return


def build_interactions(logs):
    turn, turns_for_scores, current_round, all_rounds = [], [], {}, []
    game_info = {}

    for log in logs:
        if log["event"] == "round":
            current_round = update_round(turn, turns_for_scores, current_round)
            all_rounds = update_all_rounds(current_round, all_rounds)
            turn, turns_for_scores, current_round = [], [], {}

        elif log["event"] == "turn":
            turns_for_scores = update_turns(turn, turns_for_scores)
            turn = []

        if log["event"] in ["player", "confirmation_log"]:
            game_info = add_info(game_info, log["event"], log["data"])

        elif log["event"] in LOGS_FOR_SCORES:
            if "date_created" in log:
                new_log = {
                    "from": log["user_id"],
                    "to": log["receiver_id"],
                    "timestamp": log["date_created"],
                    "action": {"type": log["event"], "content": log["data"]["content"]},
                }
            else:
                new_log = {
                    "from": log["user_id"],
                    "to": log["receiver_id"],
                    "action": {"type": log["event"], "content": log["data"]["content"]},
                }

            turn.append(new_log)

    current_round = update_round(turn, turns_for_scores, current_round)
    all_rounds = update_all_rounds(current_round, all_rounds)
    return all_rounds, game_info


def add_info(round_info, event, info):
    if event == "player":
        round_info[info["role"]] = {
            key: value for key, value in info.items() if key != "role"
        }
    elif event == "confirmation_log":
        if event in round_info:
            round_info[event].append(info)
        else:
            round_info[event] = [info]

    return round_info


def update_round(turn, turns, round):
    turns = update_turns(turn, turns)
    round["turns"] = turns
    return round


def update_turns(curr_turn, all_turns):
    if curr_turn:
        all_turns.append(curr_turn)
    return all_turns


def update_all_rounds(curr_round, all_rounds):
    if len(curr_round["turns"]) != 0:
        all_rounds.append(curr_round)
    return all_rounds
