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
            speed = 0
            # Compute Guess repetition
            repeats_guess, num_guess_repeats = cm.repeats_guess(turn_results)
            # print(repeats_guess)
        else:
            # Compute Speed
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
            # Compute strategy score
            turn_strategy_score = cm.turns_strategy(turn_results)
            if len(turn_strategy_score) == 1:
                if aborted:
                    turn_strategy_score = [0]

        self.scores["episode scores"][BENCH_SCORE] = speed
        self.scores["episode scores"]["repeats guess"] = repeats_guess
        self.scores["episode scores"]["total guess repetitions"] = num_guess_repeats

        for idx, score in enumerate(turn_score):
            if idx + 1 not in self.scores["turn scores"]:
                self.scores["turn scores"][idx + 1] = {}
            self.scores["turn scores"][idx + 1]["closeness score"] = score
        for idx, score in enumerate(turn_strategy_score):

            if idx + 1 not in self.scores["turn scores"]:
                self.scores["turn scores"][idx + 1] = {}
            self.scores["turn scores"][idx + 1]["strategy score"] = score

        if use_critic:
            for idx, score in enumerate(overall_change):
                if idx + 1 not in self.scores["turn scores"]:
                    self.scores["turn scores"][idx + 1] = {}
                self.scores["turn scores"][idx + 1]["change_of_opinion"] = overall_change[idx]

            if total_yes == np.nan:
                self.scores["episode scores"]["Repetition-Guesser-On-Critic-Agreement"] = np.nan
                self.scores["episode scores"]["Non-Repetition-Guesser-On-Critic-Agreement"] = np.nan
                self.scores["episode scores"]["Repetition-Guesser-On-Critic-Disagreement"] = np.nan
                self.scores["episode scores"]["Non-Repetition-Guesser-On-Critic-Disagreement"] = np.nan

                self.scores["episode scores"]["agreement_count"] \
                    = np.nan
                self.scores["episode scores"]["same_guess_submitted"] \
                    = np.nan
                self.scores["episode scores"]["guess_change"] \
                    = np.nan

            else:
                self.scores["episode scores"]["agreement_count"] \
                    = total_yes
                self.scores["episode scores"]["disagreement_count"] \
                    = total_no

                self.scores["episode scores"]["same_guess_submitted"] \
                    =  use_same_guess_yes + use_same_guess_no
                self.scores["episode scores"]["guess_change"] \
                    = use_diff_guess_yes + use_diff_guess_no

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
        return