from typing import List, Tuple, Dict
import numpy as np

from scores.metrics import *
from scores.compute_metrics import ComputeMetrics

cm = ComputeMetrics()


class ScoresCalculator:
    def __init__(self):

        self.scores = {
            "turn scores": {},
            "episode scores": {},
            }

    def compute_game_specific_metrics(self,
            aborted,
            loss,
            turn_results,
            use_critic,
            change_guess_words,
    ):
        if loss:
            # episode_score = 0
            speed = 0
            # Compute Guess repetition
            repeats_guess, num_guess_repeats = cm.repeats_guess(turn_results)
            # print(repeats_guess)
        else:
            # deleted episode score
            # Compute Rank
            speed = cm.speed(turn_results)
            # Compute Guess repetition
            repeats_guess, num_guess_repeats = cm.repeats_guess(turn_results)

        if use_critic:
            total_yes = np.nan
            total_no = np.nan
            use_same_guess_yes = np.nan
            use_diff_guess_yes = np.nan
            use_same_guess_no = np.nan
            use_diff_guess_no = np.nan
            overall_change = [np.nan]
            if change_guess_words:
                results = cm.change_of_opinion(change_guess_words)
                # print(results)
                total_yes = results["total_yes"]
                total_no = results["total_no"]
                use_same_guess_yes = results["use_same_guess_yes"]
                use_diff_guess_yes = results["use_diff_guess_yes"]
                use_same_guess_no = results["use_same_guess_no"]
                use_diff_guess_no = results["use_diff_guess_no"]
                overall_change = results["overall_change"]

        # Compute Turn-wise Scores
        turn_score = [np.nan]
        turn_strategy_score = [np.nan]
        if turn_results:
            turn_score = cm.turns(turn_results)
            # print(turn_score)
            # Compute strategy score
            turn_strategy_score = cm.turns_strategy(turn_results)
            # print(turn_strategy_score)
            if len(turn_strategy_score) == 1:
                if aborted:
                    turn_strategy_score = [0]



        self.scores["episode scores"][BENCH_SCORE] = speed
        self.scores["episode scores"]["repeats guess"] = repeats_guess
        self.scores["episode scores"]["total guess repetitions"] = num_guess_repeats


        for idx, score in enumerate(turn_score):
            # self.log_turn_score(idx + 1, "closeness score", score)
            if idx + 1 not in self.scores["turn scores"]:
                self.scores["turn scores"][idx + 1] = {}
            self.scores["turn scores"][idx + 1]["closeness score"] = score
        # print(turn_strategy_score)
        for idx, score in enumerate(turn_strategy_score):

            # self.log_turn_score(idx + 1, "strategy score", score)
            if idx + 1 not in self.scores["turn scores"]:
                self.scores["turn scores"][idx + 1] = {}
            self.scores["turn scores"][idx + 1]["strategy score"] = score

        if use_critic:
            for idx, score in enumerate(overall_change):
                # self.log_turn_score(idx + 1, "change_of_opinion", overall_change[idx])
                if idx + 1 not in self.scores["turn scores"]:
                    self.scores["turn scores"][idx + 1] = {}
                self.scores["turn scores"][idx + 1]["change_of_opinion"] = overall_change[idx]

            if total_yes == np.nan:
                self.scores["episode scores"]["Repetition-Guesser-On-Critic-Agreement"] = np.nan
                self.scores["episode scores"]["Non-Repetition-Guesser-On-Critic-Agreement"] = np.nan
                self.scores["episode scores"]["Repetition-Guesser-On-Critic-Disagreement"] = np.nan
                self.scores["episode scores"]["Non-Repetition-Guesser-On-Critic-Disagreement"] = np.nan

            else:
                if total_yes != 0:

                    self.scores["episode scores"]["Repetition-Guesser-On-Critic-Agreement"]\
                        = round(use_same_guess_yes / total_yes, 2)

                    self.scores["episode scores"]["Non-Repetition-Guesser-On-Critic-Agreement"]\
                        = round(use_diff_guess_yes / total_yes, 2)
                else:


                    self.scores["episode scores"]["Repetition-Guesser-On-Critic-Agreement"] = 0
                    self.scores["episode scores"]["Non-Repetition-Guesser-On-Critic-Agreement"] = 0

                if total_no != 0:

                    self.scores["episode scores"]["Repetition-Guesser-On-Critic-Disagreement"] \
                        =round(use_same_guess_no / total_no, 2)
                    self.scores["episode scores"]["Non-Repetition-Guesser-On-Critic-Disagreement"] \
                        =round(use_diff_guess_no / total_no, 2)

                else:

                    self.scores["episode scores"]["Repetition-Guesser-On-Critic-Disagreement"] = 0
                    self.scores["episode scores"]["Non-Repetition-Guesser-On-Critic-Disagreement"] = 0
