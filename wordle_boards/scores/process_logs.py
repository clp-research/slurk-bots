import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Root = '....slurk-bots/wordle_boards"


LOGS_FOR_SCORES = [
    "GUESS",
    "INVALID_LENGTH",
    "INVALID_WORD",
    "NOT_VALID_ENGLISH_WORD",
    "EMPTY_GUESS",
    "CORRECT_GUESS",
    "FALSE_GUESS",
    "PROPOSAL",
    "CRITIC_AGREEMENT",
    "CRITIC_RATIONALE",
    "TARGET_WORD",
    "CLUE",
    "LETTER_FEEDBACK",
    "WORD_FREQUENCY",
    "instance id",
]

SELECTED_LOGS = LOGS_FOR_SCORES + [
    "bot_version",
    "player",
    "confirmation_log",
    "round",
    "turn",
]


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
    # return filtered_logs


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

        if log["event"] in ["player", "bot_version", "confirmation_log"]:
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
    # empty round is NOT added in this case, s. code in def?
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
    elif event == "bot_version":
        round_info[event] = info

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


# to process_logs

# Standard
# select_logs(ROOT, "raw_logs/logs_wo_st_503", "selected_logs/standard")

# Clue
# select_logs(ROOT, "raw_logs/logs_wo_clue_504", "selected_logs/clue")
# select_logs(ROOT, "raw_logs/logs_wo_clue_520", "selected_logs/clue")

# Critic
# select_logs(ROOT, "raw_logs/logs_wo_cr_505", "selected_logs/critic")
