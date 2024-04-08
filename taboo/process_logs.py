import json
import os
import csv
import matplotlib.pyplot as plt
from itertools import cycle

# from taboo.compute_scores import compute_scores
from compute_scores import compute_scores

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
directory = os.path.join(ROOT, "taboo", "data", "logs", "results", "first_round")


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
            "target word", "difficulty level", "players"
        }:
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

    for index, round in enumerate(all_rounds):
        print(f"These are the scores for round {index + 1} out of {len(all_rounds)}")
        print('')
        # for t_index, turn in enumerate(round["turns"]):
            # print(t_index, turn)
        # print(round)
        round_score, average_utt_length, average_token_length = compute_scores(round)
        all_rounds_scores.append(round_score)
        all_rounds_utterance_lengths.append(average_utt_length)
        all_rounds_token_lengths.append(average_token_length)
        print("__________")
        print('')

    print(f"Interactions of '{messages_jsonfile}' saved in '{output_jsonfile}'")
    print('The main scores for this game are:', all_rounds_scores)
    average_utterance_length = sum(all_rounds_utterance_lengths)/len(all_rounds_utterance_lengths)
    average_token_length = sum(all_rounds_token_lengths)/len(all_rounds_token_lengths)
    return all_rounds_scores, average_utterance_length, average_token_length


def write_to_csv(filename, clue, target_word):
    # Define the CSV file name
    csv_file = os.path.join(ROOT, 'taboo', 'data', 'clues_human.csv')
    # csv_file = 'instructions_human.csv'
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
    scores_dict = {}

    for file in sorted_file_names:
        messages_file = select_logs(os.path.join(ROOT, "taboo", "data", "logs", "results", "first_round", file))
        room_scores, room_utterance_length, room_token_length = build_interactions_file(messages_file)
        all_files_scores.append(room_scores)
        all_files_utterance_length.append(room_utterance_length)
        all_files_token_length.append(room_token_length)
        scores_dict[file.split('.')[0]] = room_scores

    print('The scores for all rooms are:', all_files_scores)
    # Flatten the list of lists
    flattened_scores = [score for instance_scores in all_files_scores for score in instance_scores if instance_scores]
    # Filter out None values from flattened scores
    filtered_scores = [score for score in flattened_scores if score is not None]
    return sorted_file_names, filtered_scores, scores_dict, all_files_utterance_length, all_files_token_length


def calculate_average_score(scores_list):
    average_score = sum(scores_list) / len(scores_list)  # Average score: 36.66666666666667
    print("Average score:", average_score)
    return average_score


def get_played_words_and_clues(directory):
    all_interactions = [file for file in os.listdir(directory) if 'interactions' in file]
    all_sorted_interactions = sorted(all_interactions, key=lambda x: int(x.split('_')[0]))
    played_target_words = []

    for file_name in all_sorted_interactions:
        file_path = os.path.join(directory,
                                 file_name)
        print("Reading file:", file_name)

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
                            print("Found target word:", target_word)
                            found_target_words.add(target_word)
                            played_target_words.append(target_word)

                    if 'action' in action and action['action']['type'] == 'clue':
                        clue = action['action']['content']
                        print('CLUE:', clue)
                        write_to_csv(file_name, clue, target_word)

    return played_target_words



# print(select_logs(os.path.join(ROOT, "taboo", "data", "logs", "2.jsonl")))
# build_interactions_file("2.jsonl_text_messages.json", os.path.join(ROOT, "taboo", "data", "logs", "2_interactions.json"))

all_sorted_room_files, all_scores, all_scores_dict, all_utterances_lengths, all_tokens_lengths = process_interactions(directory)  # The scores for all rooms are: [[33.333333333333336, 0, 0, 0], [0, 0, 0, 0, 0, 0], [None, 33.333333333333336, 100.0, 0, 0, None], [100.0, 100.0, 33.333333333333336, 100.0, 100.0, 100.0], [0, 50.0, 100.0, 100.0, None], [33.333333333333336, 0, 0, 50.0, 100.0, 100.0], [0, 50.0, 0, None, 0, 0]]print("The scores per room are:", all_scores_dict)
average_score = calculate_average_score(all_scores)  # 36.66666666666667
average_utterance_length = sum(all_utterances_lengths)/len(all_utterances_lengths)
print("Average utterance length:", average_utterance_length)
average_token_length = sum(all_tokens_lengths)/len(all_tokens_lengths)
print("Average token length:", average_token_length)
all_played_words = get_played_words_and_clues(directory)
unique_words = set(all_played_words)

print(f"All played words are {len(all_played_words)}:", all_played_words)  # 39
print(f"The unique target words are {len(unique_words)}:", unique_words)  # 27 # 8 high, 10 medium, 9 low

# [[33.333333333333336, 0, 0, 0],
# [0, 0, 0, 0, 0, 0],
# [None, 33.333333333333336, 100.0, 0, 0, None],
# [100.0, 100.0, 33.333333333333336, 100.0, 100.0, 100.0],
# [0, 50.0, 100.0, 100.0, None],
# [33.333333333333336, 0, 0, 50.0, 100.0, 100.0],
# [0, 50.0, 0, None, 0, 0]]



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
plt.show()

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
    "Human-Human": 36.66
}

# Define colors for each model
colors = [
    'lightblue', 'lightgreen', 'yellow', 'red', 'purple',
    'lightcoral', 'pink', 'gray', 'cyan', 'magenta', 'orange',
    'blue', 'green', 'brown', 'lightskyblue', 'lightseagreen',
    'blueviolet', 'gray', 'lime', 'olive', 'black'
]

# Plotting the scatter plot
plt.figure(figsize=(12, 10))  # Adjusted figure size for better visibility
for model, score, color in zip(models.keys(), quality_scores.values(), colors):
    if score != 'n/a':
        plt.scatter(score, model, color=color, s=100)
        plt.text(score + 1.5, model, models[model], fontsize=8, ha='left', va='center', color='black')  # Adjusted y-position for text labels
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
plt.show()
