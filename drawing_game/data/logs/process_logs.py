import csv
import json
import os
import matplotlib.pyplot as plt

from drawing_game.data.compute_scores import compute_scores

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

directory = os.path.join(ROOT, "logs", "results")

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
    '▢ ▢ N ▢ ▢\n▢ ▢ ▢ ▢ ▢\nN ▢ ▢ ▢ ▢\nN ▢ ▢ ▢ ▢\n▢ ▢ ▢ N N',
    '▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\nA A ▢ A ▢\n▢ ▢ ▢ ▢ A\nA ▢ ▢ ▢ ▢',
    '▢ ▢ X ▢ ▢\nX ▢ ▢ ▢ ▢\n▢ ▢ ▢ X X\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ X ▢',
]
compact = [
    '\nX ▢ ▢ ▢ X\nX X X X X\nX X X X X\nX X X X X\nX ▢ ▢ ▢ X\n',
    '\n▢ ▢ ▢ ▢ ▢\nC C C C C\nC C C C C\nC C C C C\nC C C C C\n',
    '\nN ▢ ▢ ▢ N\nN N ▢ N N\nN ▢ N ▢ N\nN N ▢ N N\nN ▢ ▢ ▢ N\n',
    '\nT ▢ ▢ ▢ T\nT T ▢ T T\nT ▢ T ▢ T\nT ▢ T ▢ T\nT ▢ T ▢ T\n',
    '\nG G G G G\n▢ G ▢ ▢ ▢\n▢ ▢ G ▢ ▢\n▢ ▢ ▢ G ▢\nG G G G G\n',
]


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


def build_interactions_and_return_scores_per_room(messages_jsonfile):
    """
    Build interactions json file per room (=several rounds),
    compute round scores and return all the rounds' scores.
    """
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
            # elif log["event"] == "grid type":
            #     grid_type = {"from": "GM", "to": "GM", "timestamp": log["date_created"],
            #             "action": {"type": log["event"], "content": log["data"]["content"]}}
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

    all_rounds_scores = []
    # COMPUTE SCORES
    for index, round in enumerate(all_rounds):
        print(f"These are the scores for round {index + 1} out of {len(all_rounds)}")
        print('')
        round_f1_scores = compute_scores(round)
        all_rounds_scores.append(round_f1_scores)
        print("__________")
        print('')

    print(f"Interactions of '{messages_jsonfile}' saved in '{output_jsonfile}'")
    print('The main scores for this game are:', all_rounds_scores)
    return all_rounds_scores


def write_to_csv(filename, instruction, grid_type):
    # Define the CSV file name
    csv_file = os.path.join(ROOT, 'instructions_human.csv')
    # csv_file = 'instructions_human.csv'
    # Check if the CSV file exists
    file_exists = os.path.isfile(csv_file)
    # Open the CSV file in append mode
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        # Create a CSV writer object
        writer = csv.writer(file)
        # Write header if file is created newly
        if not file_exists:
            writer.writerow(['Filename', 'Instruction', 'Grid Type'])
        # Write instruction to CSV
        writer.writerow([filename, instruction, grid_type])


def process_interactions(directory_path):
    all_files = [file for file in os.listdir(directory_path) if file.endswith('.jsonl')]
    sorted_file_names = sorted(all_files, key=lambda x: int(x.split('.')[0]))
    all_scores = []
    scores_dict = {}
    for file in sorted_file_names:
        messages_file = select_logs(os.path.join(ROOT, "logs", "results", file))
        room_scores = build_interactions_and_return_scores_per_room(messages_file)
        all_scores.append(room_scores)
        scores_dict[file.split('.')[0]] = room_scores

    print('The scores for all rooms are:', all_scores)
    # Flatten the list of lists
    flattened_scores = [score for instance_scores in all_scores for score in instance_scores if instance_scores]
    # Filter out None values from flattened scores (unfisnished rounds)
    filtered_scores = [score for score in flattened_scores if score is not None]
    return sorted_file_names, filtered_scores, scores_dict


def calculate_average_score(scores_list):
    average_score = sum(scores_list) / len(scores_list)
    print("Average score:", average_score)
    return average_score


def get_played_grids_and_instructions(directory):
    all_interactions = [file for file in os.listdir(directory) if 'interactions' in file]
    all_sorted_interactions = sorted(all_interactions, key=lambda x: int(x.split('_')[0]))
    played_target_grids = []
    # Keep track of found target grids across dictionaries within each file
    found_target_grids = set()
    counter_compact_instr = 0
    counter_random_instr = 0
    counter_compact_grids = 0
    counter_random_grids = 0

    for file_name in all_sorted_interactions:
        file_path = os.path.join(directory,
                                 file_name)
        print("Reading file:", file_name)

        # Read the file
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Iterate over each item in the JSON data
        for item in data:

            # Iterate over each turn in the current item
            for turn in item['turns']:
                target_grid = ''
                grid_type = ''
                clue = ''
                # Iterate over each action in the current turn
                for action in turn:
                    # Check if the action is of type 'target grid'
                    if 'action' in action and action['action']['type'] == 'target grid':
                        target_grid = action['action']['content']
                        if target_grid in compact:
                            grid_type = 'compact'
                        elif target_grid in random:
                            grid_type = 'random'
                        else:
                            grid_type = 'Not found'
                        print(f"Found {grid_type} target grid:\n", target_grid)

                        # Check if this target grid is not already found across dictionaries within the same file
                        if target_grid not in found_target_grids:
                            found_target_grids.add(target_grid)
                            if grid_type == 'compact':
                                counter_compact_grids += 1
                            elif grid_type == 'random':
                                counter_random_grids += 1

                    if 'action' in action and action['action']['type'] == 'clue':
                        clue = action['action']['content']
                        # print('INSTRUCTION:', clue)
                if clue.lower() != 'done':
                    if grid_type == 'compact':
                        counter_compact_instr += 1
                    elif grid_type == 'random':
                        counter_random_instr += 1
                write_to_csv(file_name, clue, grid_type)

            played_target_grids.append(target_grid)
            # print(counter_compact_grids)
            # print(counter_random_grids)

    return played_target_grids, counter_compact_instr, counter_random_instr, counter_compact_grids, counter_random_grids


# print(select_logs(os.path.join(ROOT, "logs", "results", "4026.jsonl")))
# build_interactions_file("4026_text_messages.json")

all_sorted_room_files, all_scores, all_scores_dict = process_interactions(directory)  # All the scores are: [[0, 0, 0], [0, 0], [24.0, 57.0, 75.0], [0], [0, 21.0, 71.0], [100.0, 100.0, 100.0], [], [], [0]]
print("The scores per room are:", all_scores_dict)
average_score = calculate_average_score(all_scores)  # 34.25 with unfinished games, 39.142857142857146 only completed games
all_played_grids, compact_grid_instr_count, random_grid_instr_count, compact_num, random_num = get_played_grids_and_instructions(directory)
unique_grids = set(all_played_grids)

print(f"The played grids are {len(all_played_grids)}")  # 16
print(f"The unique grids are {len(unique_grids)}")  # 13

print("Number of compact grid instructions:", compact_grid_instr_count)  # 19
print("Number of random grid instructions:", random_grid_instr_count)  # 15

# To compute this we don't care if we have full turns or not, we count all given instructions except 'done'
print("Instructions per compact grid on average:", compact_grid_instr_count/compact_num)  # 3.8
print("Instructions per random grid on average:", random_grid_instr_count/random_num)  # 1.875


# All the scores are:
# 4026: [[0, 0, 0],
# 4027: [0, 0],
# 4032: [24.0, 57.0, 75.0],
# 4029: [0],
# 4051: [0, 21.0, 71.0],
# 4030: [100.0, 100.0, 100.0],
# 4050: [],
# 4028: [],
# 4031: [0]]



# Scores per room
scores_per_room = {
    '4026': [0, 0, 0],
    '4027': [0, 0],
    '4028': [],
    '4029': [None],
    '4030': [100.0, 100.0, 100.0],
    '4031': [None],
    '4032': [24.0, 57.0, 75.0],
    '4050': [],
    '4051': [0, 21.0, 71.0]
}

# Plotting the scatter chart
plt.figure(figsize=(12, 6))
colors = ['blue', 'green', 'red', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'lime']
markers = ['o', 's', '^', '*', 'D']  # Define markers for different types of scores

for idx, (room, room_scores) in enumerate(scores_per_room.items(), start=1):
    for round_num, score in enumerate(room_scores, start=1):
        if score is not None:
            plt.scatter(room, score, color=colors[idx-1], marker=markers[round_num-1], label=f"Round {round_num}, Room {room}")
        else:
            plt.scatter(room, 0, color='black', marker='x', label=f"Round {round_num}, Room {room} (None)")

# Setting labels and title
plt.xlabel('Room')
plt.ylabel('Score')
plt.title('Human Performance per Round and Room')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Move legend outside the plot
plt.legend(loc='upper left', bbox_to_anchor=(1.05, 1), title="Legend")

# Show plot
plt.tight_layout()
plt.savefig(os.path.join(ROOT, 'drawing_performance_room_.png'))
# plt.show()


# Generate plot to display average performance (quality score) of all agents for Drawing Game


# Define model names and their corresponding abbreviations
models = {
    "CodeLlama-34b--CodeLlama-34b": "CL",
    "SUS-Chat-34B--SUS-Chat-34B": "SUS",
    "WizardLM-13b-v1.2--WizardLM-13b-v1.2": "WL",
    "Yi-34B-Chat-t0.0--Yi-34B-Chat-t0.0": "Yi",
    "claude-2.1--claude-2.1": "C2.1",
    "claude-3-haiku--claude-3-haiku": "C3H",
    "claude-3-opus--claude-3-opus": "C3O",
    "claude-3-sonnet--claude-3-sonnet": "C3S",
    "gemma-7b--gemma-7b": "G7",
    "gpt-3.5-turbo--gpt-3.5-turbo": "G3.5",
    "gpt-4-0125--gpt-4-0125": "G4.1",
    "gpt-4-0613--gpt-4-0613": "G4.2",
    "gpt-4-1106--gpt-4-1106": "G4.3",
    "mistral-large--mistral-large": "ML",
    "mistral-medium--mistral-medium": "MM",
    "openchat-3.5-0106--openchat-3.5-0106": "OC1",
    "openchat-3.5-1210--openchat-3.5-1210": "OC2",
    "openchat_3.5--openchat_3.5": "OC3",
    "sheep-duck-llama-2--sheep-duck-llama-2": "SDL",
    "vicuna-13b-v1.5--vicuna-13b-v1.5": "V13",
    "Human-Human": "HUM"
}

# Quality scores for each model
quality_scores = {
    "CodeLlama-34b-Instruct-hf-t0.0--CodeLlama-34b-Instruct-hf-t0.0": 'n/a',
    "SUS-Chat-34B-t0.0--SUS-Chat-34B-t0.0": 29.0,
    "WizardLM-13b-v1.2-t0.0--WizardLM-13b-v1.2-t0.0": 'n/a',
    "Yi-34B-Chat-t0.0--Yi-34B-Chat-t0.0": 9.07,
    "claude-2.1-t0.0--claude-2.1-t0.0": 'n/a',
    "claude-3-haiku-20240307-t0.0--claude-3-haiku-20240307-t0.0": 'n/a',
    "claude-3-opus-20240229-t0.0--claude-3-opus-20240229-t0.0": 'n/a',
    "claude-3-sonnet-20240229-t0.0--claude-3-sonnet-20240229-t0.0": 'n/a',
    "gemma-7b-it-t0.0--gemma-7b-it-t0.0": 'n/a',
    "gpt-3.5-turbo-0125-t0.0--gpt-3.5-turbo-0125-t0.0": 64.18,
    "gpt-4-0125-preview-t0.0--gpt-4-0125-preview-t0.0": 99.6,
    "gpt-4-0613-t0.0--gpt-4-0613-t0.0": 98.19,
    "gpt-4-1106-preview-t0.0--gpt-4-1106-preview-t0.0": 94.34,
    "mistral-large-2402-t0.0--mistral-large-2402-t0.0": 'n/a',
    "mistral-medium-2312-t0.0--mistral-medium-2312-t0.0": 'n/a',
    "openchat-3.5-0106-t0.0--openchat-3.5-0106-t0.0": 0.86,
    "openchat-3.5-1210-t0.0--openchat-3.5-1210-t0.0": 3.17,
    "openchat_3.5-t0.0--openchat_3.5-t0.0": 8.31,
    "sheep-duck-llama-2-13b-t0.0--sheep-duck-llama-2-13b-t0.0": 'n/a',
    "vicuna-13b-v1.5-t0.0--vicuna-13b-v1.5-t0.0": 'n/a',
    "Human-Human": 39.14
}

# Define colors for each model
colors = ['lightblue', 'lightgreen', 'yellow', 'red', 'purple', 'lightcoral', 'pink', 'gray', 'cyan', 'magenta', 'orange', 'blue', 'green', 'brown', 'lightskyblue', 'lightseagreen', 'blueviolet', 'gray', 'lime', 'olive', 'black']

# Plotting the scatter plot
plt.figure(figsize=(12, 10))
for model, score, color in zip(models.keys(), quality_scores.values(), colors):
    if score != 'n/a':
        plt.scatter(score, model, color=color, s=100)
        plt.text(score + 1.5, model, models[model], fontsize=8, ha='left', va='center', color='black')
    else:
        plt.scatter(score, model, color='black', marker='x', s=100)

plt.axvline(x=39.14, color='r', linestyle='--')  # Human average line
plt.xlabel('Quality Score')
plt.ylabel('Model')
# plt.title('Quality Scores Achieved by Different Agents')
plt.gca().invert_yaxis()  # Invert y-axis to have the highest score at the top

# Set ticks for x-axis with interval of 10 and show them
plt.xticks(range(0, 109, 10), [str(x) for x in range(0, 109, 10)], fontsize=8)

# Remove ticklines
plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=True)

# Add padding to the right side of the plot
plt.xlim(right=110)

plt.tight_layout()  # Adjust layout to prevent clipping of labels
plt.savefig(os.path.join(ROOT, 'drawing_quality_scores_plot.png'))
# plt.show()


