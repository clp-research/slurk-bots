import numpy as np
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Root = '....slurk-bots/wordle_boards"


def compute_average_scores(raw_scores):
    scores = {}

    def traverse_dict(dictionary):
        nonlocal scores
        if isinstance(dictionary, dict):
            if "episode scores" in dictionary:
                for score_key, score_value in dictionary["episode scores"].items():
                    if score_key in scores:
                        scores[score_key].append(score_value)
                    else:
                        scores[score_key] = [score_value]
            else:
                for value in dictionary.values():
                    traverse_dict(value)

    traverse_dict(raw_scores)

    # Calculate the average scores

    mean_scores = {}
    for key, score in scores.items():
        if key not in [
            "agreement_count",
            "disagreement_count",
            "same_guess_submitted",
            "guess_change",
        ]:
            # for these scores, the result will be a sum instead of average
            mean_scores[key] = round(
                np.mean([val for val in score if not np.isnan(val)]), 2
            )
        else:
            mean_scores[key] = sum([val for val in score if not np.isnan(val)])

    print(
        f"Share of games won in the 1st round: "
        f"{round(len([score for score in scores['Main Score'] if score == 100])/len([score for score in scores['Main Score']if not np.isnan(score)]), 2)}"
    )
    return f"Average Scores: {mean_scores}"


def compute_average_scores_per_frequency_type(raw_scores):
    scores = {"high_frequency": {}, "medium_frequency": {}}
    frequency = None

    def traverse_dict(dictionary):
        nonlocal scores
        nonlocal frequency
        if isinstance(dictionary, dict):
            if "episode scores" in dictionary:
                for score_key, score_value in dictionary["episode scores"].items():
                    if score_key in scores[frequency]:
                        scores[frequency][score_key].append(score_value)
                    else:
                        scores[frequency][score_key] = [score_value]
            else:
                for key, value in dictionary.items():
                    if key in scores.keys():
                        frequency = key
                    traverse_dict(value)

    traverse_dict(raw_scores)
    mean_scores = {"high_frequency": {}, "medium_frequency": {}}
    for frequency, all_scores in scores.items():
        for key, score in all_scores.items():
            if key != "agreement_count" and key != "disagreement_count":
                mean_scores[frequency][key] = round(
                    np.mean([val for val in score if not np.isnan(val)]), 2
                )
            else:
                mean_scores[frequency][key] = sum(
                    [val for val in score if not np.isnan(val)]
                )

    return f"Average Scores per Frequency Type: {mean_scores}"

def compute_closeness_scores(raw_scores):
    all_closeness_scores = []
    i = 0
    mono = "True"

    def traverse_dict(dictionary):
        nonlocal all_closeness_scores
        nonlocal i
        nonlocal mono
        if isinstance(dictionary, dict):
            if "turn scores" in dictionary:
                closeness_episode = []
                for turn, turn_scores in dictionary["turn scores"].items():
                    if len(closeness_episode) != 0:
                        if turn_scores["closeness score"] < closeness_episode[-1]:
                            mono = False
                    closeness_episode.append(turn_scores["closeness score"])
                if mono == False:
                    i += 1

                # if closeness_episode[0] != 25:
                all_closeness_scores.append(closeness_episode)
                mono = "True"
            else:
                for value in dictionary.values():
                    traverse_dict(value)

    traverse_dict(raw_scores)

    #     # print(all_closeness_scores)
    # print(all_closeness_scores)
    return f"Monotonoulsy increasing closeness scores: {round((len(all_closeness_scores) - i) / len(all_closeness_scores), 2)}"

if __name__ == "__main__":
    with open("critic_human_scores.json", "r") as file:
        critic_human_scores = json.load(file)
    print(compute_average_scores(critic_human_scores))
    print(compute_average_scores_per_frequency_type(critic_human_scores))
    print(compute_closeness_scores(critic_human_scores))

    # with open("critic_model_scores.json", "r") as file:
    #     critic_model_scores = json.load(file)
    # print(compute_average_scores(critic_model_scores))
    # print(compute_average_scores_per_frequency_type(critic_model_scores))
    # print(compute_closeness_scores(critic_model_scores))

    # with open("clue_human_scores.json", "r") as file:
    #     clue_human_scores = json.load(file)
    # print(compute_average_scores(clue_human_scores))
    # print(compute_average_scores_per_frequency_type(clue_human_scores))
    # print(compute_closeness_scores(clue_human_scores))

    # with open("clue_model_scores.json", "r") as file:
    #     clue_model_scores = json.load(file)
    # print(compute_average_scores(clue_model_scores))
    # print(compute_average_scores_per_frequency_type(clue_model_scores))
    # print(compute_closeness_scores(clue_model_scores))



    # with open("standard_human_scores.json", "r") as file:
    #     standard_human_scores = json.load(file)
    # print(compute_average_scores(standard_human_scores))
    # print(compute_average_scores_per_frequency_type(standard_human_scores))
    # print(compute_closeness_scores(standard_human_scores))

    # with open("standard_model_scores.json", "r") as file:
    #     standard_model_scores = json.load(file)
    # print(compute_average_scores(standard_model_scores))
    # print(compute_average_scores_per_frequency_type(standard_model_scores))
    # print(compute_closeness_scores(standard_model_scores))
