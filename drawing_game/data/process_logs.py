import json
import os

from compute_scores import compute_scores

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SELECT LOGS
def select_logs(file_in):
    text_messages = []
    with open(file_in, "r") as f:
        json_list = list(f)
    for json_str in json_list:
            log = json.loads(json_str)
            if log["event"] in {"round", "turn", "clue", "guess", "invalid format", "invalid clue", "correct guess", "max turns reached"}:
                text_messages.append(log)
    with open('text_messages.json', 'w', encoding ='utf8') as json_file:
        json.dump(text_messages, json_file, indent=4, ensure_ascii = False)

    return "Selected logs saved in text_messages.json"


print(select_logs(os.path.join(ROOT, "taboo", "2_new.jsonl")))

# BUILD DATA like  interactions_json in clembench

with open(os.path.join(ROOT, "taboo", "text_messages.json"), "r") as f:
    logs = json.load(f)

all_rounds = []
round = {}
turns_for_scores = []
turn = []
for log in logs:
    if log["event"] == "round":
        # added 3 lines
        if len(turn) != 0:
            turns_for_scores.append(turn)
        turn = []
        # if len(turns_for_scores["turns"]) != 0:
        round["turns"] = [turn for turn in turns_for_scores]
        # turns_for_scores = []
        if len(round["turns"]) != 0:
            all_rounds.append(round)
        round = {}
        turns_for_scores = []
    elif log["event"] == "turn":
        if len(turn) != 0:
        # if turn not in turns_for_scores and len(turn) != 0:
            turns_for_scores.append(turn)
        turn = []
    # add "max turns reached" but it is not logged yet
    if log["event"] in {"clue", "guess", "invalid format", "invalid clue", "correct guess"}:
        new_log = {"from": log["user_id"], "to": log["receiver_id"] , "timestamp": log["date_created"] ,"action": {"type": log["event"], "content": log["data"]["content"]}}
        turn.append(new_log)

turns_for_scores.append(turn)
round["turns"] = [turn for turn in turns_for_scores]
all_rounds.append(round)

# COMPUTE SCORES
for round in all_rounds:
    print("round")
    compute_scores(round)
    print("__________")

