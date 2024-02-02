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


def build_interactions_file(messages_jsonfile, output_jsonfile):
    with open(os.path.join(ROOT, "logs", "results", messages_jsonfile), "r") as f:
        logs = json.load(f)
        all_rounds = []
        players_data = None  # Initialize players_data outside the loop

        for log in logs:
            if players_data is None and log["event"] == "players":
                players_data = log["data"]  # Update players' data if "players" event occurs

        round_data = {"players": players_data, "turns": []}  # Initialize round_data with players_data
        turn = []
        for log in logs:
            if log["event"] == "round":
                round_data = {"players": players_data, "turns": []}  # Reset round_data for each new round
            elif log["event"] == "turn":
                turn = []  # Reset turn for each new turn event
            elif log["event"] == "clue":
                clue = {"from": log["user_id"], "to": log["receiver_id"], "timestamp": log["date_created"],
                        "action": {"type": log["event"], "content": log["data"]["content"]}}
                turn.append(clue)
            elif log["event"] == "guess":
                guess = {"from": log["user_id"], "to": log["receiver_id"], "timestamp": log["date_created"],
                         "action": {"type": log["event"], "content": log["data"]["content"]}}
                turn.append(guess)
            elif log["event"] in {"invalid format", "invalid clue", "correct guess",
                                  "max turns reached", "grid type"}:
                new_log = {"from": log["user_id"], "to": log["receiver_id"], "timestamp": log["date_created"],
                           "action": {"type": log["event"], "content": log["data"]["content"]}}
                turn.append(new_log)
            elif log["event"] == "target grid":
                grid = {"from": "GM", "to": "GM", "timestamp": log["date_created"],
                        "action": {"type": log["event"], "content": log["data"]["content"]}}
            if log["event"] == "turn":
                turn.append(grid)  # Append target grid in every turn
                round_data["turns"].append(turn)  # Append turn to round_data's turns

            elif log["event"] == "round":
                all_rounds.append(round_data)  # Append round_data to all_rounds
    all_rounds = [_round for _round in all_rounds if _round['turns']]  # Save only rounds with turns (=actually played)
    with open(output_jsonfile, "w") as outfile:
        json.dump(all_rounds, outfile, indent=4)

    # COMPUTE SCORES
    for index, round in enumerate(all_rounds):
        print(f"These are the scores for round {index + 1} out of {len(all_rounds)}")
        print('')
        # for t_index, turn in enumerate(round["turns"]):
            # print(t_index, turn)
        # print(round)
        compute_scores(round)
        print("__________")
        print('')

    return f"Interactions of '{messages_jsonfile}' saved in '{output_jsonfile}'"


print(select_logs(os.path.join(ROOT, "logs", "results/12.jsonl")))
build_interactions_file("12.jsonl_text_messages.json", os.path.join(ROOT, "logs", "results", "interactions.json"))
