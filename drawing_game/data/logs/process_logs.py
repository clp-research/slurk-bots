import json
import os

from drawing_game.data.compute_scores import compute_scores

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# SELECT LOGS
def select_logs(file_in):
    text_messages = []
    with open(file_in, "r") as f:
        json_list = list(f)
    for json_str in json_list:
        log = json.loads(json_str)
        # print(log)
        if log["event"] in {
            "round", "turn", "clue", "guess", "invalid format", "invalid clue", "players",
            "correct guess", "max turns reached", "target grid", "command", "grid type"}:
            # print(log)
            text_messages.append(log)
    # print(text_messages)
    with open(os.path.join(ROOT, "data", "", f'{file_in}_text_messages.json'), 'w', encoding='utf8') as json_file:
        json.dump(text_messages, json_file, indent=4, ensure_ascii=False)

    return f"Selected logs saved in {file_in}'text_messages.json'"


print(select_logs(os.path.join(ROOT, "logs", "results/2a.jsonl")))


# BUILD DATA like  interactions_json in clembench

def build_interactions_file(messages_jsonfile):
    # Need to build a dict for each instance (=round) with 'players': {} and 'turns': []
    with open(os.path.join(ROOT, "logs", "results", messages_jsonfile), "r") as f:
        logs = json.load(f)
        all_rounds = []
        round = {"players": dict(), "turns": []}
        turns_for_scores = []
        turn = []
        for log in logs:
            # print(log)
            if log["event"] == "round":

            #     # added 3 lines
            #     if len(turn) != 0:
            #         turns_for_scores.append(turn)
            #     turn = []
            #     # if len(turns_for_scores["turns"]) != 0:
            #     round["turns"] = [turn for turn in turns_for_scores]
            #     # turns_for_scores = []
            #     if len(round["turns"]) != 0:
            #         all_rounds.append(round)
            #     round = {}
            #     turns_for_scores = []
            # elif log["event"] == "turn":
            #     if len(turn) != 0:
            #         # if turn not in turns_for_scores and len(turn) != 0:
            #         turns_for_scores.append(turn)
            #     turn = []
            # if log["event"] == "players":
            #     round["players"] = log["data"]
            # # add "max turns reached" and "command",but it is not logged yet
            # if log["event"] in {"clue", "guess", "invalid format", "invalid clue", "correct guess", "target grid",
            #                     "max turns reached", "grid type"}:
            #     new_log = {"from": log["user_id"], "to": log["receiver_id"], "timestamp": log["date_created"],
            #                "action": {"type": log["event"], "content": log["data"]["content"]}}
            #     turn.append(new_log)
            #     # print(new_log)
            # elif log["event"] in {"command"}:
            #     if "guess" in log["data"]["command"]:
            #         content = log["data"]["command"]["guess"]
            #         new_log = {"from": log["user_id"], "to": log["receiver_id"], "timestamp": log["date_created"],
            #                    "action": {"type": "guess", "content": content}}
            #         turn.append(new_log)
            #         # print(new_log)
            #     else:
            #         pass

        turns_for_scores.append(turn)
        round["turns"] = [turn for turn in turns_for_scores]
        all_rounds.append(round)
        print(all_rounds)
        # COMPUTE SCORES
        for round in all_rounds:
            print("round")
            compute_scores(round)
            print("__________")
        return all_rounds


interactions_file = build_interactions_file("10.jsonl_text_messages.json")
