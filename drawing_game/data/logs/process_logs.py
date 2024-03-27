import csv
import json
import os

from drawing_game.data.compute_scores import compute_scores

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

directory = os.path.join(ROOT, "logs", "results")


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
    file_in = file_in.split('.')[0]
    file_in = file_in + '_text_messages.json'
    with open(os.path.join(ROOT, "data", "", file_in), 'w', encoding='utf8') as json_file:
        json.dump(text_messages, json_file, indent=4, ensure_ascii=False)

    print(f"Selected logs saved in '{file_in}'")
    return file_in


def build_interactions_file(messages_jsonfile):
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
    output_jsonfile = messages_jsonfile.split('_t')[0] + '_interactions.json'
    output_jsonfile = os.path.join(ROOT, "logs", "results", output_jsonfile)
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


def write_to_csv(filename, instruction):
    # Define the CSV file name
    csv_file = 'instructions_human.csv'
    # Check if the CSV file exists
    file_exists = os.path.isfile(csv_file)
    # Open the CSV file in append mode
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        # Create a CSV writer object
        writer = csv.writer(file)
        # Write header if file is created newly
        if not file_exists:
            writer.writerow(['Filename', 'Instruction'])
        # Write instruction to CSV
        writer.writerow([filename, instruction])



# print(select_logs(os.path.join(ROOT, "logs", "results", "4026.jsonl")))
# build_interactions_file("4026_text_messages.json")



all_files = [file for file in os.listdir(directory) if file.endswith('.jsonl')]
for file in all_files:
    messages_file = select_logs(os.path.join(ROOT, "logs", "results", file))
    build_interactions_file(messages_file)


all_interactions = [file for file in os.listdir(directory) if 'interactions' in file]
sorted_file_names = sorted(all_interactions, key=lambda x: int(x.split('_')[0]))

played_target_grids = []

for file_name in sorted_file_names:
    file_path = os.path.join(directory,
                             file_name)  # Update path_to_your_directory with your directory path
    print("Reading file:", file_name)

    # Read the file
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Iterate over each item in the JSON data
    for item in data:
        # Keep track of found target grids across dictionaries within each file
        found_target_grids = set()

        # Iterate over each turn in the current item
        for turn in item['turns']:
            # Iterate over each action in the current turn
            for action in turn:
                # Check if the action is of type 'target grid'
                if 'action' in action and action['action']['type'] == 'target grid':
                    target_grid = action['action']['content']

                    # Check if this target grid is not already found across dictionaries within the same file
                    if target_grid not in found_target_grids:
                        print("Found target grid:", target_grid)
                        found_target_grids.add(target_grid)
                        played_target_grids.append(target_grid)

                if 'action' in action and action['action']['type'] == 'clue':
                    clue = action['action']['content']
                    print('INSTRUCTION:', clue)
                    write_to_csv(file_name, clue)


unique_grids = set(played_target_grids)

print(f"The played grids are {len(played_target_grids)}:", played_target_grids)
print(f"The unique grids are {len(unique_grids)}:", unique_grids)

# The played grids are 16: ['▢ ▢ ▢ ▢ ▢\n▢ ▢ H ▢ H\n▢ ▢ ▢ ▢ H\n▢ ▢ ▢ H ▢\n▢ ▢ ▢ ▢ ▢', '▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\nA A ▢ A ▢\n▢ ▢ ▢ ▢ A\nA ▢ ▢ ▢ ▢', '\nX ▢ ▢ ▢ X\nX X X X X\nX X X X X\nX X X X X\nX ▢ ▢ ▢ X\n', '▢ ▢ ▢ Q ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ Q Q Q', '▢ ▢ X ▢ ▢\nX ▢ ▢ ▢ ▢\n▢ ▢ ▢ X X\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ X ▢', '▢ ▢ ▢ ▢ ▢\nZ Z Z ▢ Z\nZ ▢ Z ▢ Z\nZ ▢ ▢ ▢ ▢\nZ ▢ ▢ ▢ ▢', '▢ ▢ ▢ ▢ P\n▢ ▢ ▢ ▢ ▢\nP ▢ ▢ ▢ P\n▢ ▢ ▢ P ▢\n▢ P ▢ ▢ ▢', '\n▢ ▢ ▢ ▢ ▢\nC C C C C\nC C C C C\nC C C C C\nC C C C C\n', '▢ ▢ ▢ Q ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ Q Q Q', '▢ E ▢ ▢ ▢\n▢ ▢ ▢ ▢ E\n▢ E ▢ E ▢\n▢ ▢ ▢ E E\nE ▢ E ▢ ▢', '\nN ▢ ▢ ▢ N\nN N ▢ N N\nN ▢ N ▢ N\nN N ▢ N N\nN ▢ ▢ ▢ N\n', '▢ ▢ ▢ ▢ ▢\n▢ ▢ H ▢ H\n▢ ▢ ▢ ▢ H\n▢ ▢ ▢ H ▢\n▢ ▢ ▢ ▢ ▢', '\nT ▢ ▢ ▢ T\nT T ▢ T T\nT ▢ T ▢ T\nT ▢ T ▢ T\nT ▢ T ▢ T\n', '\nT ▢ ▢ ▢ T\nT T ▢ T T\nT ▢ T ▢ T\nT ▢ T ▢ T\nT ▢ T ▢ T\n', '\nG G G G G\n▢ G ▢ ▢ ▢\n▢ ▢ G ▢ ▢\n▢ ▢ ▢ G ▢\nG G G G G\n', '▢ ▢ N ▢ ▢\n▢ ▢ ▢ ▢ ▢\nN ▢ ▢ ▢ ▢\nN ▢ ▢ ▢ ▢\n▢ ▢ ▢ N N']
unique = [
    '▢ ▢ ▢ ▢ ▢\n▢ ▢ H ▢ H\n▢ ▢ ▢ ▢ H\n▢ ▢ ▢ H ▢\n▢ ▢ ▢ ▢ ▢',
    '\nN ▢ ▢ ▢ N\nN N ▢ N N\nN ▢ N ▢ N\nN N ▢ N N\nN ▢ ▢ ▢ N\n',
    '▢ ▢ ▢ Q ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ Q Q Q',
    '▢ ▢ ▢ ▢ ▢\nZ Z Z ▢ Z\nZ ▢ Z ▢ Z\nZ ▢ ▢ ▢ ▢\nZ ▢ ▢ ▢ ▢',
    '▢ ▢ X ▢ ▢\nX ▢ ▢ ▢ ▢\n▢ ▢ ▢ X X\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ X ▢',
    '\nX ▢ ▢ ▢ X\nX X X X X\nX X X X X\nX X X X X\nX ▢ ▢ ▢ X\n',
    '▢ ▢ ▢ ▢ P\n▢ ▢ ▢ ▢ ▢\nP ▢ ▢ ▢ P\n▢ ▢ ▢ P ▢\n▢ P ▢ ▢ ▢',
    '▢ E ▢ ▢ ▢\n▢ ▢ ▢ ▢ E\n▢ E ▢ E ▢\n▢ ▢ ▢ E E\nE ▢ E ▢ ▢',
    '▢ ▢ N ▢ ▢\n▢ ▢ ▢ ▢ ▢\nN ▢ ▢ ▢ ▢\nN ▢ ▢ ▢ ▢\n▢ ▢ ▢ N N',
    '▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\nA A ▢ A ▢\n▢ ▢ ▢ ▢ A\nA ▢ ▢ ▢ ▢',
    '\nT ▢ ▢ ▢ T\nT T ▢ T T\nT ▢ T ▢ T\nT ▢ T ▢ T\nT ▢ T ▢ T\n',
    '\nG G G G G\n▢ G ▢ ▢ ▢\n▢ ▢ G ▢ ▢\n▢ ▢ ▢ G ▢\nG G G G G\n',
    '\n▢ ▢ ▢ ▢ ▢\nC C C C C\nC C C C C\nC C C C C\nC C C C C\n'
]

# 6 random and 7 compact
random = [
    '▢ ▢ ▢ ▢ ▢\n▢ ▢ H ▢ H\n▢ ▢ ▢ ▢ H\n▢ ▢ ▢ H ▢\n▢ ▢ ▢ ▢ ▢',
    '▢ ▢ ▢ ▢ ▢\nZ Z Z ▢ Z\nZ ▢ Z ▢ Z\nZ ▢ ▢ ▢ ▢\nZ ▢ ▢ ▢ ▢',
    '▢ ▢ ▢ Q ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ Q Q Q',
    '▢ ▢ ▢ ▢ P\n▢ ▢ ▢ ▢ ▢\nP ▢ ▢ ▢ P\n▢ ▢ ▢ P ▢\n▢ P ▢ ▢ ▢',
    '▢ E ▢ ▢ ▢\n▢ ▢ ▢ ▢ E\n▢ E ▢ E ▢\n▢ ▢ ▢ E E\nE ▢ E ▢ ▢',
    '▢ ▢ N ▢ ▢\n▢ ▢ ▢ ▢ ▢\nN ▢ ▢ ▢ ▢\nN ▢ ▢ ▢ ▢\n▢ ▢ ▢ N N'
]

compact = [
    '▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\nA A ▢ A ▢\n▢ ▢ ▢ ▢ A\nA ▢ ▢ ▢ ▢',
    '\nX ▢ ▢ ▢ X\nX X X X X\nX X X X X\nX X X X X\nX ▢ ▢ ▢ X\n',
    '▢ ▢ X ▢ ▢\nX ▢ ▢ ▢ ▢\n▢ ▢ ▢ X X\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ X ▢',
    '\n▢ ▢ ▢ ▢ ▢\nC C C C C\nC C C C C\nC C C C C\nC C C C C\n',
    '\nN ▢ ▢ ▢ N\nN N ▢ N N\nN ▢ N ▢ N\nN N ▢ N N\nN ▢ ▢ ▢ N\n',
    '\nT ▢ ▢ ▢ T\nT T ▢ T T\nT ▢ T ▢ T\nT ▢ T ▢ T\nT ▢ T ▢ T\n',
    '\nG G G G G\n▢ G ▢ ▢ ▢\n▢ ▢ G ▢ ▢\n▢ ▢ ▢ G ▢\nG G G G G\n',
]

print('28 total instructions for compact, /7 = 4 instructions per grid on average')
print('20 total instructions for random, /6 = 3.33 instructions per grid on average')

