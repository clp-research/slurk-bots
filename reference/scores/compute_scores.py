import math
from scores.metrics import *

# Compute Scores on each game level


def compute_scores(episode_interactions) -> None:
    """Episode level scores"""

    expression_length = 0
    number_of_tokens = 0
    expression_length_sum = 0
    expression_number_of_tokens = 0

    guesser_won = False
    aborted = False

    all_scores = {"turn_scores": {}, "episode_scores": {}}

    for turn_idx, turn in enumerate(episode_interactions["turns"]):
        turn_scores = {
            METRIC_REQUEST_COUNT: 0,
            METRIC_REQUEST_COUNT_PARSED: 0,
            METRIC_REQUEST_COUNT_VIOLATED: 0,
        }
        for event in turn:
            action = event["action"]

            if action["type"] == "grid type":
                all_scores["grid type"] = action["content"]

            if action["type"] == "instance id":
                all_scores["instance id"] = action["content"]

            if action["type"] == "guess":
                turn_scores[METRIC_REQUEST_COUNT] += 1
                turn_scores[METRIC_REQUEST_COUNT_PARSED] += 1

            if action["type"] == "clue":
                turn_scores[METRIC_REQUEST_COUNT] += 1
                turn_scores[METRIC_REQUEST_COUNT_PARSED] += 1

                # message length of the expression
                expression_length = len(action["content"].strip())

                # number of tokens in the generated expression
                number_of_tokens = len(action["content"].strip().split(" "))

                turn_scores["Generated Expression Length"] = expression_length
                turn_scores["Generated Expression Number of Tokens"] = number_of_tokens

            if action["type"] == "invalid guess" or action["type"] == "invalid clue":
                turn_scores[METRIC_REQUEST_COUNT_VIOLATED] += 1
                turn_scores[METRIC_REQUEST_COUNT_PARSED] -= 1
                aborted = True

            if action["type"] == "correct guess":
                guesser_won = True

            # if action["type"] == "aborted":
            #     aborted = True
            if aborted:
                turn_scores["Generated Expression Length"] = 0
                turn_scores["Generated Expression Number of Tokens"] = 0
                turn_scores[METRIC_LOSE] = 0
                turn_scores[METRIC_ABORTED] = 1

        turn_scores[METRIC_SUCCESS] = 1 if guesser_won else 0

        all_scores["turn_scores"][turn_idx] = turn_scores

        expression_length_sum += expression_length
        expression_number_of_tokens += number_of_tokens

    # EPISODE LEVEL

    expression_length_sum = round(
        expression_length_sum / float(len(all_scores["turn_scores"].keys())), 4
    )
    expression_number_of_tokens = round(
        expression_number_of_tokens / float(len(all_scores["turn_scores"].keys())), 4
    )

    all_scores["episode_scores"][
        "Average Generated Expression Length"
    ] = expression_length_sum
    all_scores["episode_scores"][
        "Average Generated Expression Number of Tokens"
    ] = expression_number_of_tokens

    violated_request_count = sum(
        [
            all_scores["turn_scores"][turn][METRIC_REQUEST_COUNT_VIOLATED]
            for turn in all_scores["turn_scores"].keys()
        ]
    )
    all_scores["episode_scores"][METRIC_REQUEST_COUNT_VIOLATED] = violated_request_count

    parsed_request_count = sum(
        [
            all_scores["turn_scores"][turn][METRIC_REQUEST_COUNT_PARSED]
            for turn in all_scores["turn_scores"].keys()
        ]
    )
    all_scores["episode_scores"][METRIC_REQUEST_COUNT_PARSED] = parsed_request_count

    request_count = sum(
        [
            all_scores["turn_scores"][turn][METRIC_REQUEST_COUNT]
            for turn in all_scores["turn_scores"].keys()
        ]
    )
    all_scores["episode_scores"][METRIC_REQUEST_COUNT] = request_count

    all_scores["episode_scores"][METRIC_REQUEST_SUCCESS] = (
        parsed_request_count / request_count
    )

    if aborted:
        all_scores["episode_scores"][METRIC_SUCCESS] = 0
        all_scores["episode_scores"][METRIC_LOSE] = 0
        all_scores["episode_scores"][METRIC_ABORTED] = 1
        all_scores["episode_scores"][BENCH_SCORE] = math.nan

    else:
        all_scores["episode_scores"][METRIC_SUCCESS] = 1 if guesser_won else 0
        all_scores["episode_scores"][METRIC_LOSE] = 0 if guesser_won else 1
        all_scores["episode_scores"][METRIC_ABORTED] = 0
        all_scores["episode_scores"][BENCH_SCORE] = 100 if guesser_won else 0

    return all_scores
