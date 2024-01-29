import math
import re
from typing import Dict

from drawing_game.data.metrics import (
    METRIC_ABORTED,
    METRIC_SUCCESS,
    METRIC_LOSE,
    METRIC_REQUEST_COUNT,
    METRIC_REQUEST_COUNT_VIOLATED,
    METRIC_REQUEST_COUNT_PARSED,
    METRIC_REQUEST_SUCCESS,
    BENCH_SCORE,
)


def compute_scores_taboo(episode_interactions) -> None:
    """ Episode level scores"""
    turn_scores = []
    prev_guess = None
    prev_guess_counter = 0
    prev_clue = None
    prev_clue_counter = 0
    invalid_response = False  # Note: This only takes into consideration that both players were compliant or not
    guesser_won = False
    for turn_idx, turn in enumerate(episode_interactions["turns"]):
        turn_score = {"guess": None, "clue": None, "request_count": 1}

        for event in turn:
            action = event["action"]
            if action["type"] == "invalid format":
                invalid_response = True
            if action["type"] == "guess":
                turn_score["guess"] = action["content"]
            if action["type"] == "clue":
                turn_score["clue"] = action["content"]
            if action["type"] == "correct guess":
                guesser_won = True

        if invalid_response:
            turn_score["violated_request_count"] = 1
            turn_score["parsed_request_count"] = 0
        else:
            turn_score["violated_request_count"] = 0
            turn_score["parsed_request_count"] = 1

        if turn_score["guess"] is not None and turn_score["guess"] == prev_guess:  # might be None, if clue is wrong
            prev_guess_counter += 1
        if turn_score["clue"] is not None and turn_score["clue"] == prev_clue:
            prev_clue_counter += 1
        print(turn_idx, 'Accuracy', 1 if guesser_won else 0)
        print(turn_idx, METRIC_REQUEST_COUNT_VIOLATED, turn_score["violated_request_count"])
        print(turn_idx, METRIC_REQUEST_COUNT_PARSED, turn_score["parsed_request_count"])
        print(turn_idx, METRIC_REQUEST_COUNT, turn_score["request_count"])
        prev_guess = turn_score["guess"]
        prev_clue = turn_score["clue"]
        turn_scores.append(turn_score)

    violated_request_count = sum([turn["violated_request_count"] for turn in turn_scores])
    print(METRIC_REQUEST_COUNT_VIOLATED, violated_request_count)

    parsed_request_count = sum([turn["parsed_request_count"] for turn in turn_scores])
    print(METRIC_REQUEST_COUNT_PARSED, parsed_request_count)

    request_count = sum([turn["request_count"] for turn in turn_scores])
    print(METRIC_REQUEST_COUNT, request_count)

    print(METRIC_REQUEST_SUCCESS, parsed_request_count / request_count)
    # # checking the last guess (could be None) is ok,
    # # b.c. the game ends only successfully, when there is a correct guess

    # Common metrics
    if invalid_response:  # whether a violation of the game rules happened (response not parsable)
        print(METRIC_ABORTED, 1)
        print(METRIC_SUCCESS, 0)
        print(METRIC_LOSE, 0)

        # Game-specific metrics
        # commendted this metric, import numpy!
        # self.log_episode_score(BENCH_SCORE, np.nan)  # metric not applicable
    else:
        print(METRIC_ABORTED, 0)
        if guesser_won:
            print(METRIC_SUCCESS, 1)
            print(METRIC_LOSE, 0)
            print(BENCH_SCORE, 100 / len(turn_scores))  # how early the guesser found the word
        else:
            print(METRIC_SUCCESS, 0)
            print(METRIC_LOSE, 1)
            print(BENCH_SCORE, 0)  # word not found

    # # Game-specific metrics
    # # How often the Guesser repeated a guess
    print('Repetition-Guesser', prev_guess_counter)
    # # How often the Describer repeated itself
    print('Repetition-Describer', prev_clue_counter)
    # this might require a side-loop between describer and GM (game should not continue with Guesser)
    # self.log_episode_score('Rule-following', ...)


def compute_scores(episode_interactions: Dict) -> None:
    precision, recall, f1 = 0, 0, 0

    previous_turn_grid = '▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢'
    flipped_count_sum = 0
    expression_length_sum = 0
    expression_number_of_tokens = 0
    target_grid = ''
    current_turn_grid = ''

    episode_request_count = 0
    episode_parsed_request_count = 0
    episode_violated_request_count = 0

    aborted = False
    number_of_turns = 0

    player_b_pattern = r'^\n*([A-Z▢]\s){4}[A-Z▢]\n([A-Z▢]\s){4}[A-Z▢]\n([A-Z▢]\s){4}[A-Z▢]\n([A-Z▢]\s){4}[A-Z▢]\n([A-Z▢]\s){4}[A-Z▢]\n*$'
    player_a_pattern = r'^\s*([a-zA-Z]+)\n*([a-zA-Z]+)*$'  # # Modified to exclude 'instruction'
    terminate_pattern = r'^\s*(?i)done\s*$'  # optional whitespace, followed by 'done' (or any case variation), and optional whitespace.

    # loop over each turn and calculate the metrics for both Player 1 and 2.

    for t_index, turn in enumerate(episode_interactions["turns"]):
        print(t_index, turn)
        turn_request_count = 0
        turn_parsed_request_count = 0
        turn_violated_request_count = 0

        # Player 1 message
        player_1_message = turn[1]['action']['content']


        # Player generates "DONE"
        match = re.match(terminate_pattern, player_1_message)
        if match:
            break

        turn_request_count += 1
        episode_request_count += 1

        #todo: don't compute since we are not enforcing 'instruction'

        # check the Player 1 message if it matches the rule, start with "Instruction:"
        # player_1_message_matched = False
        # if player_1_message.startswith('Instruction:'):
        #     if '\n' in player_1_message:
        #         parsed_instruction = player_1_message.split('\n')[0]
        #         player_1_message = parsed_instruction
        #     player_1_message_matched = True
        #
        # if player_1_message_matched:
        #     turn_parsed_request_count += 1
        #     episode_parsed_request_count += 1
        # else:
        #     turn_violated_request_count += 1
        #     episode_violated_request_count += 1
        #     aborted = True
        #     # do not continue processing the rest of the turn when the game is aborted
        #     break

        # check if the turn includes the Player 2 message
        # in case the turn doesn't include an item and index position 4, it means the game has been aborted
        if len(turn) < 4:
            aborted = True
            break

        # Player 2 message
        player_2_message = turn[4]['action']['content']
        turn_request_count += 1
        episode_request_count += 1

        # check Player 2 message if it matches the instruction => grid
        match = re.compile(player_b_pattern).match(player_2_message)
        if match:
            turn_parsed_request_count += 1
            episode_parsed_request_count += 1
        else:
            turn_violated_request_count += 1
            episode_violated_request_count += 1
            aborted = True
            break

        # calculate player-specific and turn-specific metrics

        try:
            precision, recall, f1 = evaluate(target_grid, player_2_message)  #todo:load target_grid
        except:
            pass

        # number of turns other
        number_of_turns += 1

        # Player 1 - message length
        expression_length = len(player_1_message.replace('Instruction:', '').strip())
        print(t_index, 'Generated Expression Length', expression_length)
        expression_length_sum += expression_length

        # Player 1 - number of tokens in the generated expression
        number_of_tokens = len(player_1_message.replace('Instruction:', '').strip().split(' '))
        print(t_index, 'Generated Expression Number of Tokens', number_of_tokens)
        expression_number_of_tokens += number_of_tokens

        print(t_index, 'Precision', precision)
        print(t_index, 'Recall', recall)
        print(t_index, 'F1', f1)

        # calculate flipped pixel counts
        flipped_count = 0
        try:
            current_turn_grid = player_2_message
            flipped_count = calculate_flipped_pixels(previous_turn_grid, current_turn_grid)
        except:
            pass

        flipped_count_sum += flipped_count
        previous_turn_grid = current_turn_grid
        print(t_index, 'Changed Cell Count', flipped_count)

        # request count, parsed & violated request counts
        print(t_index, METRIC_REQUEST_COUNT,
                            turn_request_count)
        print(t_index, METRIC_REQUEST_COUNT_PARSED,
                            turn_parsed_request_count)
        print(t_index, METRIC_REQUEST_COUNT_VIOLATED,
                            turn_violated_request_count)

    # Episode level logging
    if aborted:
        # if aborted give NaN value to all metrics
        print('Precision', math.nan)
        print('Recall', math.nan)
        print('F1', math.nan)
        print(BENCH_SCORE, math.nan)

        # average of flipped pixel counts
        print('Average Changed Cell Count', math.nan)

        # average of expression length
        print('Average Generated Instruction Length', math.nan)

        # average of number of tokens in generated expression
        print('Average Generated Expression Number of Tokens', math.nan)

        # the last turn scores are also the scores for the episode
        print(METRIC_SUCCESS, 0)

        # lose ratio
        print(METRIC_LOSE, 0)

        # aborted ratio
        print(METRIC_ABORTED, 1)
    else:
        # the last turn scores are also the scores for the episode
        print('Precision', precision)
        print('Recall', recall)
        print('F1', f1)
        print(BENCH_SCORE, f1)

        # average of flipped pixel counts
        flipped_count_sum = round(flipped_count_sum / float(number_of_turns), 4)
        print('Average Changed Cell Count', flipped_count_sum)

        # average of expression length
        expression_length_sum = round(expression_length_sum / float(number_of_turns), 4)
        print('Average Generated Instruction Length', expression_length_sum)

        # average of number of tokens in generated expression
        expression_number_of_tokens = round(expression_number_of_tokens / float(number_of_turns), 4)
        print('Average Generated Expression Number of Tokens', expression_number_of_tokens)

        # the last turn scores are also the scores for the episode
        print(METRIC_SUCCESS, 1 if f1 >= 99 else 0)

        # lose ratio
        print(METRIC_LOSE, 0 if f1 >= 99 else 1)

        # aborted ratio
        print(METRIC_ABORTED, 0)

    # request count, parsed & violated request counts
    print(METRIC_REQUEST_COUNT, episode_request_count)
    print(METRIC_REQUEST_COUNT_VIOLATED, episode_violated_request_count)
    print(METRIC_REQUEST_COUNT_PARSED, episode_parsed_request_count)

    # request success ratio
    if episode_request_count == 0:
        print(METRIC_REQUEST_SUCCESS, 0)
    else:
        request_success_ratio = round(episode_parsed_request_count / float(episode_request_count), 4)
        print(METRIC_REQUEST_SUCCESS, request_success_ratio)


def evaluate(target, generated):
    if get_size(target) != get_size(generated):
        return 0.0, 0.0, 0.0

    target_rows = target.strip().split('\n')
    generated_rows = generated.strip().split('\n')

    recall_counter = 0
    total_recall_counter = 0

    precision_counter = 0
    total_precision_counter = 0

    for r_index in range(0, len(target_rows)):

        target_cells = target_rows[r_index].split(' ')
        generated_cells = generated_rows[r_index].split(' ')

        for c_index in range(0, len(target_cells)):

            if target_cells[c_index] != '▢':
                total_recall_counter += 1

                if target_cells[c_index].lower() == generated_cells[c_index].lower():
                    recall_counter += 1

            if generated_cells[c_index] != '▢':
                total_precision_counter += 1

                if target_cells[c_index].lower() == generated_cells[c_index].lower():
                    precision_counter += 1

    recall = round(recall_counter / float(total_recall_counter), 4)
    precision = round(precision_counter / float(total_precision_counter), 4)

    if precision == 0 or recall == 0:
        f1 = 0
    else:
        f1 = (2 * precision * recall) / (precision + recall)
    f1 = round(f1, 4)

    precision = round(100 * precision, 0)
    recall = round(100 * recall, 0)
    f1 = round(100 * f1, 0)

    return precision, recall, f1


def calculate_flipped_pixels(previous, current):
    target_rows = previous.strip().split('\n')
    generated_rows = current.strip().split('\n')

    flipped_counter = 0

    for r_index in range(0, len(target_rows)):

        target_cells = target_rows[r_index].split(' ')
        generated_cells = generated_rows[r_index].split(' ')

        for c_index in range(0, len(target_cells)):

            if target_cells[c_index].lower() != generated_cells[c_index].lower():
                flipped_counter += 1

    return flipped_counter


def get_size(grid):
    rows = grid.strip().split('\n')

    row_size = len(rows)
    column_size = 0
    for r_index in range(0, len(rows)):
        target_cells = rows[r_index].split(' ')
        column_size = len(target_cells)
        break

    return row_size, column_size
