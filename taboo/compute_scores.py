# from taboo.metrics import (
#     METRIC_ABORTED,
#     METRIC_SUCCESS,
#     METRIC_LOSE,
#     METRIC_REQUEST_COUNT,
#     METRIC_REQUEST_COUNT_VIOLATED,
#     METRIC_REQUEST_COUNT_PARSED,
#     METRIC_REQUEST_SUCCESS,
#     BENCH_SCORE,
# )
from metrics import (
    METRIC_ABORTED,
    METRIC_SUCCESS,
    METRIC_LOSE,
    METRIC_REQUEST_COUNT,
    METRIC_REQUEST_COUNT_VIOLATED,
    METRIC_REQUEST_COUNT_PARSED,
    METRIC_REQUEST_SUCCESS,
    BENCH_SCORE,
)

def remove_punctuation(word):
    clean_word = word.strip('.').strip('?').strip(',').strip('"').strip('/').strip('-')
    return clean_word


def compute_scores(episode_interactions) -> None:
    """ Episode level scores"""
    main_score = None
    turn_scores = []
    average_utterance_length = 0
    average_token_length = 0
    unique_words_round = ''
    prev_guess = None
    prev_guess_counter = 0
    prev_clue = None
    prev_clue_counter = 0
    invalid_response = False  # Note: This only takes into consideration that both players were compliant or not
    guesser_won = False
    winning_clues = []
    for turn_idx, turn in enumerate(episode_interactions["turns"]):
        turn_score = {"guess": None, "clue": None, "request_count": 1}

        for event in turn:
            action = event["action"]
            if action["type"] == "invalid format":  # or invalid clue?
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
        # print(turn_idx, METRIC_REQUEST_COUNT_VIOLATED, turn_score["violated_request_count"])
        # print(turn_idx, METRIC_REQUEST_COUNT_PARSED, turn_score["parsed_request_count"])
        # print(turn_idx, METRIC_REQUEST_COUNT, turn_score["request_count"])
        prev_guess = turn_score["guess"]
        prev_clue = turn_score["clue"]
        turn_scores.append(turn_score)

    # violated_request_count = sum([turn["violated_request_count"] for turn in turn_scores])
    # print(METRIC_REQUEST_COUNT_VIOLATED, violated_request_count)
    #
    # parsed_request_count = sum([turn["parsed_request_count"] for turn in turn_scores])
    # print(METRIC_REQUEST_COUNT_PARSED, parsed_request_count)
    #
    # request_count = sum([turn["request_count"] for turn in turn_scores])
    # print(METRIC_REQUEST_COUNT, request_count)
    #
    # print(METRIC_REQUEST_SUCCESS, parsed_request_count / request_count)
    # # checking the last guess (could be None) is ok,
    # # b.c. the game ends only successfully, when there is a correct guess

    # Common metrics
    #todo: aborted if inactive or left?
    if invalid_response:  # whether a violation of the game rules happened (response not parsable)
        print(METRIC_ABORTED, 1)
        print(METRIC_SUCCESS, 0)
        print(METRIC_LOSE, 0)

        # Game-specific metrics
        # commendted this metric, import numpy!
        # self.log_episode_score(BENCH_SCORE, np.nan)  # metric not applicable
    else:
        print(METRIC_ABORTED, 0)
        clues_turn_round = [turn["clue"] for turn in turn_scores]
        # print(clues_turn_round)
        words_round = [turn.split() for turn in clues_turn_round]
        unique_words_round = list(set([remove_punctuation(word.lower()) for sublist in words_round for word in sublist]))
        # unique_words_round = [word for word in unique_words_round if word]
        print("Unique words:", unique_words_round)

        utterance_length_count = [len(clue) for clue in clues_turn_round]
        # flattened_scores = [score for instance_scores in all_files_scores for score in instance_scores if instance_scores]
        average_utterance_length = sum(utterance_length_count) / len(utterance_length_count)
        print("Average utterance length count:", average_utterance_length)
        token_number_count = [len(clue.split()) for clue in clues_turn_round]
        average_token_length = sum(token_number_count) / len(token_number_count)
        print("Average token length count:", average_token_length)
        if guesser_won:
            print(METRIC_SUCCESS, 1)
            print(METRIC_LOSE, 0)
            main_score = 100 / len(turn_scores)
            print(BENCH_SCORE, main_score)  # how early the guesser found the word
            print("All clues in the won round:", clues_turn_round)
            winning_clues.append(clues_turn_round)
        elif len(turn) < 3:
            print(METRIC_SUCCESS, 0)
            print(METRIC_LOSE, 1)
            main_score = None
            unique_words_round = ''
            print(BENCH_SCORE, None)

        else:
            print(METRIC_SUCCESS, 0)
            print(METRIC_LOSE, 1)
            main_score = 0
            print(BENCH_SCORE, 0)  # word not found

    # # Game-specific metrics
    # # How often the Guesser repeated a guess
    print('Repetition-Guesser', prev_guess_counter)
    # # How often the Describer repeated itself
    print('Repetition-Describer', prev_clue_counter)
    # this might require a side-loop between describer and GM (game should not continue with Guesser)
    # self.log_episode_score('Rule-following', ...)
    return main_score, average_utterance_length, average_token_length, unique_words_round, winning_clues

