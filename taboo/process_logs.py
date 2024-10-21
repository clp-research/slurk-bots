import json
import string
import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from itertools import cycle

# from taboo.compute_scores import compute_scores
from compute_scores import compute_scores

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
directory = os.path.join(ROOT, "taboo", "data", "logs", "results", "first_round")
WINNING_CLUES = os.path.join(ROOT, 'taboo', 'data', 'winning_clues.csv')


# SELECT LOGS
def select_logs(file_in):
    text_messages = []
    with open(file_in, "r") as f:
        json_list = list(f)
    for json_str in json_list:
        log = json.loads(json_str)
        if log["event"] in {
            "round", "turn", "clue", "guess", "invalid format",
            "invalid clue", "correct guess", "max turns reached",
            text_messages.append(log)

    file_in = file_in.split('.')[0]
    file_in = file_in + '_text_messages.json'
    with open(os.path.join(ROOT, "data", "logs", file_in), 'w', encoding='utf8') as json_file:
        json.dump(text_messages, json_file, indent=4, ensure_ascii=False)

    print(f"Selected logs saved in {file_in}_text_messages.json")
    return file_in


# BUILD DATA like  interactions_json in clembench

def build_interactions_file(messages_jsonfile):
    with open(os.path.join(ROOT, "taboo", "data", "logs", "results", messages_jsonfile), "r") as f:
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
            elif log["event"] == "target word":
                target_word = {"from": "GM", "to": "GM", "timestamp": log["date_created"],
                        "action": {"type": log["event"], "content": log["data"]["content"]}}
            if log["event"] == "turn":
                turn.append(target_word)  # Append target grid in every turn
                round_data["turns"].append(turn)  # Append turn to round_data's turns

            elif log["event"] == "round":
                all_rounds.append(round_data)  # Append round_data to all_rounds
    all_rounds = [_round for _round in all_rounds if _round['turns']]  # Save only rounds with turns (=actually played)
    output_jsonfile = messages_jsonfile.split('_t')[0] + '_interactions.json'
    output_jsonfile = os.path.join(ROOT, "logs", "results", output_jsonfile)
    with open(output_jsonfile, "w") as outfile:
        json.dump(all_rounds, outfile, indent=4)

    # COMPUTE SCORES
    all_rounds_scores = []
    all_rounds_utterance_lengths = []
    all_rounds_token_lengths = []
    all_rounds_words = []
    all_rounds_winning_clues = []

    for index, round in enumerate(all_rounds):
        print(f"These are the scores for round {index + 1} out of {len(all_rounds)}")
        print('')
        # for t_index, turn in enumerate(round["turns"]):
            # print(t_index, turn)
        # print(round)
        round_score, average_utt_length, average_token_length, unique_words_round, winning_clues = compute_scores(round)
        all_rounds_scores.append(round_score)
        all_rounds_utterance_lengths.append(average_utt_length)
        all_rounds_token_lengths.append(average_token_length)
        all_rounds_words.append(unique_words_round)
        all_rounds_winning_clues.append(winning_clues)
        # print(all_rounds_words)
        print("__________")
        print('')

    print(f"Interactions of '{messages_jsonfile}' saved in '{output_jsonfile}'")
    print('The main scores for this game are:', all_rounds_scores)
    average_utterance_length = sum(all_rounds_utterance_lengths)/len(all_rounds_utterance_lengths)
    average_token_length = sum(all_rounds_token_lengths)/len(all_rounds_token_lengths)
    return all_rounds_scores, average_utterance_length, average_token_length, all_rounds_words, all_rounds_winning_clues


def write_to_csv(filename, clue, target_word):
    # Define the CSV file name
    csv_file = os.path.join(ROOT, 'taboo', 'data', 'clues_human.csv')
    # Check if the CSV file exists
    file_exists = os.path.isfile(csv_file)
    # Open the CSV file in append mode
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        # Create a CSV writer object
        writer = csv.writer(file)
        # Write header if file is created newly
        if not file_exists:
            writer.writerow(['Filename', 'Clue', 'Target Word'])
        # Write instruction to CSV
        writer.writerow([filename, clue, target_word])


def process_interactions(directory_path):
    all_files = [file for file in os.listdir(directory_path) if file.endswith('.jsonl')]
    sorted_file_names = sorted(all_files, key=lambda x: int(x.split('.')[0]))
    all_files_scores = []
    all_files_utterance_length = []
    all_files_token_length = []
    all_files_words = []
    all_files_winning_clues = {}
    scores_dict = {}

    for file in sorted_file_names:
        messages_file = select_logs(os.path.join(ROOT, "taboo", "data", "logs", "results", "first_round", file))
        room_scores, room_utterance_length, room_token_length, room_words, room_winning_clues = build_interactions_file(messages_file)
        # print(room_words)
        all_files_scores.append(room_scores)
        all_files_utterance_length.append(room_utterance_length)
        all_files_token_length.append(room_token_length)
        all_files_words.append(room_words)
        scores_dict[file.split('.')[0]] = room_scores
        all_files_winning_clues[file.split('.')[0]] = room_winning_clues

    print('The scores for all rooms are:', all_files_scores)
    # Flatten the list of lists
    flattened_scores = [score for instance_scores in all_files_scores for score in instance_scores if instance_scores]
    # Filter out None values from flattened scores
    filtered_scores = [score for score in flattened_scores if score is not None]
    return sorted_file_names, filtered_scores, scores_dict, all_files_utterance_length, all_files_token_length, all_files_words, all_files_winning_clues


def calculate_average_score(scores_list):
    flattened_list = []
    [flattened_list.append(sublist) for sublist in scores_list]
    valid_scores_list = [score for score in flattened_list if score is not None]
    # print(valid_scores_list)
    winning_scores= [score for score in valid_scores_list if score > 0]
    print(winning_scores)
    average_score = round(sum(valid_scores_list) / len(valid_scores_list), 2)  # Average score: 36.67
    print("Average score:", average_score)
    return average_score


def get_played_words_and_clues(directory):
    all_interactions = [file for file in os.listdir(directory) if 'interactions' in file]
    all_sorted_interactions = sorted(all_interactions, key=lambda x: int(x.split('_')[0]))
    played_target_words = []

    for file_name in all_sorted_interactions:
        file_path = os.path.join(directory,
                                 file_name)

        # Read the file
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Iterate over each item in the JSON data
        for item in data:
            # Keep track of found target words across dictionaries within each file
            found_target_words = set()

            # Iterate over each turn in the current item
            for turn in item['turns']:
                target_word = ''
                # Iterate over each action in the current turn
                for action in turn:
                    # Check if the action is of type 'target word'
                    if 'action' in action and action['action']['type'] == 'target word':
                        target_word = action['action']['content']

                        # Check if this target word is not already found across dictionaries within the same file
                        if target_word not in found_target_words:
                            found_target_words.add(target_word)
                            played_target_words.append(target_word)

                    if 'action' in action and action['action']['type'] == 'clue':
                        clue = action['action']['content']
                        write_to_csv(file_name, clue, target_word)

    return played_target_words


def flatten_list(lst):
    flattened = []
    for item in lst:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            flattened.append(item)
    return flattened


def calculate_lexical_diversity(unique_words, all_words):
    number_unique_words = len(unique_words)
    number_all_words = len(all_words)
    lexical_diversity = round(number_unique_words / number_all_words, 2)
    return lexical_diversity


def print_winning_clues_from_dict(csv_file, clues_dict):
    all_clues_sum = 0
    utterance_length_sum = 0
    token_number_sum = 0
    csv_file = WINNING_CLUES
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        # Create a CSV writer object
        writer = csv.writer(file)
        # Write header if file is created newly
        if not file_exists:
            writer.writerow(['Room', 'Winning Clue'])
            
        for room in clues_dict:
            if flatten_list(winning_clues_dict[room]):
                print(room + ':')
                for clue in flatten_list(winning_clues_dict[room]):
                    print(clue)
                    all_clues_sum += 1
                    utterance_length_sum += len(clue.strip())
                    token_number_sum += len(clue.strip().split())
                    # Write instruction to CSV
                    writer.writerow([room, clue])

    print("Average winning clue length:", utterance_length_sum/all_clues_sum)
    print("Average token number in winning clue:", token_number_sum/all_clues_sum)
    return utterance_length_sum, token_number_sum, all_clues_sum


average_score = calculate_average_score(all_scores)  # 36.67
print("All scores:", len(all_scores))
number_episodes_played = len(all_scores)
print("Number of episodes played:", number_episodes_played )  # 35
average_utterance_length = round(sum(all_utterances_lengths)/len(all_utterances_lengths), 2)
print("Average clue length:", average_utterance_length)  # 47.09
average_token_length = round(sum(all_tokens_lengths)/len(all_tokens_lengths), 2)
print("Average number of tokens in clue:", average_token_length)  # 9.52
all_words = list(flatten_list(all_words))
print("Number of all words used:", len(all_words))  # 490
all_unique_words = list(set(flatten_list(all_words)))
print("Number of unique words used:", len(all_unique_words))  # 262
# print("All unique words used:", sorted([word for word in all_unique_words if word]))
lexical_diversity = round(calculate_lexical_diversity(all_unique_words, all_words), 2)
print("Lexical diversity score:", lexical_diversity)  # 0.53


all_words = ['cabinet', 'array', 'independently', 'sear',
'anymore', 'sear', 'array', 'obvious', 'seize', 'provide',
'designation', 'stimulate', 'clear', 'contributor', 'none', 'embroidery',
'quarterly', 'rate', 'assure', 'regret', 'responsibility', 'sear',
'bypass', 'fighter', 'transplant', 'obvious', 'responsibility',
'resume', 'anymore', 'regret', 'orient', 'transplant', 'career',
'designation', 'induce', 'seize', 'plaza', 'provide', 'resume']


words_and_levels = {'high': ['responsibility', 'rate', 'resume', 'clear', 'provide', 'array', 'none', 'career'],
                    'medium': ['assure', 'induce', 'stimulate', 'fighter', 'obvious', 'contributor', 'quarterly', 'cabinet', 'orient',  'anymore'],
                   'low': ['transplant', 'sear', 'embroidery', 'independently', 'plaza', 'bypass', 'designation', 'seize', 'regret']}

# PLOT 1: ALL HUMAN ROUNDS

scores_per_room = {
    '4052': [33.33, 0, 0, 0],
    '4054': [0, 0, 0, 0, 0, 0],
    '4055': [None, 33.33, 100.0, 0, 0, None],
    '4056': [100.0, 100.0, 33.33, 100.0, 100.0, 100.0],
    '4057': [0, 50.0, 100.0, 100.0, None],
    '4058': [33.33, 0, 0, 50.0, 100.0, 100.0],
    '4059': [0, 50.0, 0, None, 0, 0]
}

# Define colors and markers
colors = ['blue', 'green', 'red', 'orange', 'purple', 'cyan', 'magenta']
markers = ['o', 's', '^', '*', 'D', 'P']

# Plotting the scatter chart
plt.figure(figsize=(10, 10))

for idx, (room, room_scores) in enumerate(scores_per_room.items(), start=1):
    for round_num, score in enumerate(room_scores, start=1):
        if score is not None:
            color = colors[(idx - 1) % len(colors)]  # Assign color for each room
            marker = markers[(idx + round_num - 2) % len(markers)]  # Cycle through markers
            plt.scatter(room, score, color=color, marker=marker, label=f"Round {round_num}, Room {room}")
        else:
            plt.scatter(room, 0, color='black', marker='x', label=f"Round {round_num}, Room {room} (None)")

# Setting labels and title
plt.xlabel('Room')
plt.ylabel('Score')
plt.title('Human Performance per Round and Room')
plt.xticks(rotation=45)
plt.yticks([0, 20, 40, 60, 80, 100])  # Set specific y-axis ticks
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Move legend outside the plot
plt.legend(loc='upper left', bbox_to_anchor=(1.05, 1), title="Legend")

# Show plot
plt.tight_layout()
plt.savefig(os.path.join(ROOT, 'taboo', 'data', 'taboo_performance_room_.png'))
# plt.show()

# PLOT 2: ALL HUMAN SCORERS AVERAGED

# Calculate average scores per room
averaged_scores_per_room = {}
for room, room_scores in scores_per_room.items():
    valid_scores = [score for score in room_scores if score is not None]  # Exclude None values
    if valid_scores:
        averaged_score = round(np.mean(valid_scores), 2)
        averaged_scores_per_room[room] = averaged_score
    else:
        averaged_scores_per_room[room] = None  # Assign None if no valid scores

print('Averaged scores per room:', averaged_scores_per_room)

# Plotting the scatter chart
plt.figure(figsize=(12, 6))
colors = ['blue', 'green', 'red', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'lime']
markers = ['o', 's', '^', '*', 'D']  # Define markers for different types of scores

for idx, (room, room_scores) in enumerate(scores_per_room.items(), start=1):
    averaged_score = averaged_scores_per_room.get(room)  # Get averaged score for the room
    if room_scores:  # Check if scores list is not empty
        if averaged_score is not None:  # Check if averaged score is not None
            plt.scatter(room, averaged_score, color=colors[idx-1], marker='o', label=f"Room {room} (Avg)")
        else:
            plt.scatter(room, 0, color='black', marker='x', label=f"Room {room} (None)")
    else:
        plt.scatter(room, 0, color='black', marker='', label=f"Room {room} (Empty)")

# Setting labels and title
plt.xlabel('Room')
plt.ylabel('Average Score')
plt.title('Average Human Performance per Room')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Move legend outside the plot
plt.legend(loc='upper left', bbox_to_anchor=(1.05, 1), title="Legend")

# Show plot
plt.tight_layout()
plt.savefig(os.path.join(ROOT, 'taboo', 'data', 'taboo_average_performance_room.png'))


# PLOT 3: ALL MODELS SCORES (NO HUMANS)

# Generate plot to display average performance (quality score) of all agents for Taboo

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

quality_scores = {
    "CodeLlama-34b-Instruct-hf-t0.0--CodeLlama-34b-Instruct-hf-t0.0": 35.37,
    "SUS-Chat-34B-t0.0--SUS-Chat-34B-t0.0": 69.23,
    "WizardLM-13b-v1.2-t0.0--WizardLM-13b-v1.2-t0.0": 64.29,
    "Yi-34B-Chat-t0.0--Yi-34B-Chat-t0.0": 41.46,
    "claude-2.1-t0.0--claude-2.1-t0.0": 0.0,
    "claude-3-haiku-20240307-t0.0--claude-3-haiku-20240307-t0.0": 0.0,
    "claude-3-opus-20240229-t0.0--claude-3-opus-20240229-t0.0": 0.0,
    "claude-3-sonnet-20240229-t0.0--claude-3-sonnet-20240229-t0.0": 0.0,
    "gemma-7b-it-t0.0--gemma-7b-it-t0.0": 'n/a',
    "gpt-3.5-turbo-0125-t0.0--gpt-3.5-turbo-0125-t0.0": 73.17,
    "gpt-4-0125-preview-t0.0--gpt-4-0125-preview-t0.0": 93.33,
    "gpt-4-0613-t0.0--gpt-4-0613-t0.0": 79.81,
    "gpt-4-1106-preview-t0.0--gpt-4-1106-preview-t0.0": 83.94,
    "mistral-large-2402-t0.0--mistral-large-2402-t0.0": 88.89,
    "mistral-medium-2312-t0.0--mistral-medium-2312-t0.0": 88.89,
    "openchat-3.5-0106-t0.0--openchat-3.5-0106-t0.0": 64.1,
    "openchat-3.5-1210-t0.0--openchat-3.5-1210-t0.0": 66.67,
    "openchat_3.5-t0.0--openchat_3.5-t0.0": 72.97,
    "sheep-duck-llama-2-13b-t0.0--sheep-duck-llama-2-13b-t0.0": 7.84,
    "vicuna-13b-v1.5-t0.0--vicuna-13b-v1.5-t0.0": 60.71,
    "Human-Human": 36.66
}

# Define colors for each model
# colors = [
#     'lightblue', 'lightgreen', 'yellow', 'red', 'purple',
#     'lightcoral', 'pink', 'gray', 'cyan', 'magenta', 'orange',
#     'blue', 'green', 'brown', 'lightskyblue', 'lightseagreen',
#     'blueviolet', 'gray', 'lime', 'olive', 'black'
# ]


# Plotting the scatter plot
plt.figure(figsize=(12, 10))  # Adjusted figure size for better visibility

scores_list = []

for model, score, color in zip(models.keys(), quality_scores.values(), colors):
    if score != 'n/a':
        scores_list.append(score)
        plt.scatter(score, model, color=color, s=100)
    else:
        plt.scatter(score, model, color='black', marker='x', s=100)


plt.axvline(x=36.66, color='r', linestyle='--')  # Human average line
plt.xlabel('Quality Score')
plt.ylabel('Model')
# plt.title('Quality Scores Achieved by Different Agents')
plt.gca().invert_yaxis()  # Invert y-axis to have the highest score at the top

# Set y-axis ticks and limits
plt.yticks(range(len(models)), models.keys())
# plt.ylim(-1, len(models))  # Adjust the y-axis limits  # Comment so model order is not reversed
plt.ylim(top=-1)  # Add paddint on the top
plt.xlim(right=101)  # Add padding to the right


# Set ticks for x-axis with interval of 10 and show them
plt.xticks(range(0, 109, 10), [str(x) for x in range(0, 109, 10)], fontsize=8)

# Remove ticklines
plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=True)

# Add padding to the right side of the plot
# plt.ylim(- 1, + 1)

plt.tight_layout()  # Adjust layout to prevent clipping of labels
plt.savefig(os.path.join(ROOT, 'taboo', 'data', 'taboo_all_quality_scores.png'))
# plt.show()



# PLOT 4: MODELS' AND HUMANS' SCORES

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
    "Human-Human Room 4052": "4052",
    "Human-Human Room 4054": "4054",
    "Human-Human Room 4055": "4055",
    "Human-Human Room 4056": "4056",
    "Human-Human Room 4057": "4057",
    "Human-Human Room 4058": "4058",
    "Human-Human Room 4059": "4059"
}

# Quality scores for each model
quality_scores = {
    "CodeLlama-34b-Instruct-hf-t0.0--CodeLlama-34b-Instruct-hf-t0.0": 35.37,
    "SUS-Chat-34B-t0.0--SUS-Chat-34B-t0.0": 69.23,
    "WizardLM-13b-v1.2-t0.0--WizardLM-13b-v1.2-t0.0": 64.29,
    "Yi-34B-Chat-t0.0--Yi-34B-Chat-t0.0": 41.46,
    "claude-2.1-t0.0--claude-2.1-t0.0": 0.0,
    "claude-3-haiku-20240307-t0.0--claude-3-haiku-20240307-t0.0": 0.0,
    "claude-3-opus-20240229-t0.0--claude-3-opus-20240229-t0.0": 0.0,
    "claude-3-sonnet-20240229-t0.0--claude-3-sonnet-20240229-t0.0": 0.0,
    "gemma-7b-it-t0.0--gemma-7b-it-t0.0": 'n/a',
    "gpt-3.5-turbo-0125-t0.0--gpt-3.5-turbo-0125-t0.0": 73.17,
    "gpt-4-0125-preview-t0.0--gpt-4-0125-preview-t0.0": 93.33,
    "gpt-4-0613-t0.0--gpt-4-0613-t0.0": 79.81,
    "gpt-4-1106-preview-t0.0--gpt-4-1106-preview-t0.0": 83.94,
    "mistral-large-2402-t0.0--mistral-large-2402-t0.0": 88.89,
    "mistral-medium-2312-t0.0--mistral-medium-2312-t0.0": 88.89,
    "openchat-3.5-0106-t0.0--openchat-3.5-0106-t0.0": 64.1,
    "openchat-3.5-1210-t0.0--openchat-3.5-1210-t0.0": 66.67,
    "openchat_3.5-t0.0--openchat_3.5-t0.0": 72.97,
    "sheep-duck-llama-2-13b-t0.0--sheep-duck-llama-2-13b-t0.0": 7.84,
    "vicuna-13b-v1.5-t0.0--vicuna-13b-v1.5-t0.0": 60.71,
    "4052": 8.33,
    "4054": 0.0,
    "4055": 33.33,
    "4056": 88.89,
    "4057": 62.5,
    "4058": 47.22,
    "4059": 10.0
}

# Plotting the scatter plot
plt.figure(figsize=(12, 10))
for model, score, color in zip(models.keys(), quality_scores.values(), colors):
    if score != 'n/a':
        plt.scatter(score, model, color=color, s=100)
        if score is not None:
            plt.text(score + 1.5, model, models[model], fontsize=8, ha='left', va='center', color='black')
    else:
        plt.scatter(score, model, color='black', marker='x', s=100)

# plt.axhline(y='4026', color='black', linestyle='--', linewidth=1)  # Add horizontal dotted line
plt.xlabel('Quality Score')
plt.ylabel('Player Pair')
# plt.title('Quality Scores Achieved by Different Agents')
plt.gca().invert_yaxis()  # Invert y-axis to have the highest room number at the top

# Set ticks for x-axis with interval of 10 and show them
plt.xticks(range(0, 105, 10), [str(x) for x in range(0, 105, 10)], fontsize=8)

# Remove ticklines
plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=True)

# Add padding to the right side of the plot
plt.xlim(right=110)
plt.ylim(top=-1)  # Add paddint on the top

plt.tight_layout()  # Adjust layout to prevent clipping of labels
plt.savefig(os.path.join(ROOT, 'taboo', 'data', 'combined_scores_taboo_plot.png'))
