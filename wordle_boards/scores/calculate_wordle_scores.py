import os
import json
import ast


from scores.game_scores import ScoresCalculator
from scores.process_logs import select_logs, build_interactions
from scores.metrics import *


def add_request_scores(scores, req_scores):
    for idx, turn_reg_scores in enumerate(req_scores):
        scores["turn scores"][idx + 1]["Violated Request Count"] = turn_reg_scores["violated_request_count"]
        scores["turn scores"][idx + 1]["Parsed Request Count"] = turn_reg_scores["parsed_request_count"]
        scores["turn scores"][idx + 1]["Request Count"] = turn_reg_scores["violated_request_count"] + turn_reg_scores[
            "parsed_request_count"]

    violated_req_count = sum([turn_req["violated_request_count"] for turn_req in req_scores])
    parsed_req_count = sum([turn_req["parsed_request_count"] for turn_req in req_scores])
    req_count = violated_req_count + parsed_req_count
    req_success_ratio = round((parsed_req_count / req_count), 2)

    scores["episode scores"][METRIC_REQUEST_COUNT] = req_count
    scores["episode scores"][METRIC_REQUEST_COUNT_PARSED] = parsed_req_count
    scores["episode scores"][METRIC_REQUEST_COUNT_VIOLATED] = violated_req_count
    scores["episode scores"][METRIC_REQUEST_SUCCESS] = req_success_ratio

    return scores


def calculate_scores(episode, critic):
    loss = True
    word_difficulty = None
    instance_id = None
    turn_results = []
    change_guess = []
    all_request_scores = []

    for turn in episode["turns"]:
        turn_requests = {}
        violated_response = 0
        parsed_response = 0
        proposal, guess, agreement = None, None, None

        for info in turn:
            if info["action"]["type"] == 'LETTER_FEEDBACK':
                turn_results.append(ast.literal_eval(info["action"]["content"]))
            elif info["action"]["type"] == 'PROPOSAL':
                proposal = info["action"]["content"]
            elif info["action"]["type"] == 'CRITIC_AGREEMENT':
                agreement = info["action"]["content"]
                # critic response is always parsed, no prefixes are used
                parsed_response += 1
            elif info["action"]["type"] == 'GUESS':
                guess = info["action"]["content"]
                # guess is logged only when it is valid.
                parsed_response += 1
            elif info["action"]["type"] == 'CORRECT_GUESS':
                loss = False

            elif info["action"]["type"] == 'WORD_FREQUENCY':
                word_difficulty = info["action"]["content"]

            elif info["action"]["type"] == 'instance id':
                instance_id = info["action"]["content"]

            # calculate requests
            elif info["action"]["type"] == "NOT_VALID_ENGLISH_WORD":
                # considered parsed in clembench
                parsed_response += 1

            elif info["action"]["type"] in ["INVALID_LENGTH", "INVALID_WORD", "EMPTY_GUESS"]:
                violated_response += 1

        turn_requests["violated_request_count"] = violated_response
        turn_requests["parsed_request_count"] = parsed_response
        all_request_scores.append(turn_requests)

        change_guess.append([proposal, guess, agreement])


    # DIFFERENTIATE IF IT IS CRITIC/STANDARD/CLUE , now I set it to TRUE
    calculator = ScoresCalculator()
    # no aborted by humans, so False
    calculator.compute_game_specific_metrics(False, loss, turn_results, critic, change_guess)
    # print(calculator.scores)

    # ADD REQUEST SCORES
    scores = add_request_scores(calculator.scores,  all_request_scores)

    # ADD GAME STATUS
    scores["episode scores"][METRIC_ABORTED] = 0
    scores["episode scores"][METRIC_LOSE] = 1 if loss else 0
    scores["episode scores"][METRIC_SUCCESS] = 0 if loss else 1
    return scores, word_difficulty, instance_id


def unfinished_episode(scores):
    """This function checks that the player used all 6 attempts to guess the word/played till the end"""
    if scores['episode scores']["Lose"] == 1:
        return len(list(scores['turn scores'].keys())) < 6
    return False


def calculate_human_scores(directory, output_file, critic=False):
    room_scores = {}
    for filename in os.listdir(directory):
        if filename.endswith("json"):
            room = filename[:4]
            print(room)
            file = os.path.join(directory, filename)
            with open(file, "r") as f:
                selected_logs = json.load(f)
                all_interactions = build_interactions(selected_logs)
                room_scores[room] = {}
                for episode_interactions in all_interactions[0]:
                    scores, word_frequency, word_id = calculate_scores(episode_interactions, critic)
                    if not unfinished_episode(scores):
                        if word_frequency in room_scores[room]:
                            room_scores[room][word_frequency][word_id ] = scores
                        else:
                            room_scores[room][word_frequency] = {}
                            room_scores[room][word_frequency][word_id] = scores
    print(room_scores.keys())
    with open(output_file, 'w', encoding ='utf8') as json_file:
        json.dump(room_scores, json_file, indent=4, ensure_ascii = False)
    return



ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Root = '....slurk-bots/wordle_boards"

# Calculate human score for critic version
print(calculate_human_scores(f"{ROOT}/selected_logs/critic", "critic_human_scores.json", critic=True))

# Calculate human score for clue version
# print(calculate_human_scores(f"{ROOT}/selected_logs/clue", "clue_human_scores.json", critic=False))

# Calculate human score for standard version
# print(calculate_human_scores(f"{ROOT}/selected_logs/standard", "standard_human_scores.json", critic=False))
