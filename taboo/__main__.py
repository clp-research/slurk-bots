from collections import defaultdict
import logging

import requests
from time import sleep

from taboo.config import EXPLAINER_PROMPT, GUESSER_PROMPT, LEVEL_WORDS, WORDS_PER_ROOM

from templates import TaskBot


import random

import os

import nltk
from nltk.corpus import stopwords
import string

nltk.download("stopwords", quiet=True)
EN_STOPWORDS = stopwords.words("english")
nltk.download("wordnet")
nltk.download("stopwords", quiet=True)
EN_LEMMATIZER = nltk.stem.WordNetLemmatizer()

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

from typing import List, Dict, Tuple, Any

from datetime import datetime
from taboo.dataloader import Dataloader


LOG = logging.getLogger(__name__)


class Session:
    # what happens between 2 players
    def __init__(self):
        self.players = list()
        self.words = Dataloader(LEVEL_WORDS, WORDS_PER_ROOM)
        self.word_to_guess = None
        self.guesses = 0
        self.guessed = False
        self.explainer = None
        self.guesser = None
        # do not need?
        self.interactions = {"players": self.players, "turns": []}
        # do not need?
        self.log_current_turn = -1

    def log_next_turn(self):
        """Call this method to group interactions per turn"""
        self.log_current_turn += 1
        self.interactions["turns"].append([])

    def close(self):
        pass

    def pick_explainer(self):
        # assuming there are only 2 players
        self.explainer = random.choice(self.players)["id"]
        for player in self.players:
            if player["id"] != self.explainer:
                self.guesser = player["id"]


#     game over


class SessionManager(defaultdict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)


class TabooBot(TaskBot):
    """Bot that manages a taboo game.

    - Bot enters a room and starts a taboo game as soon as 2 participants are
      present.
    - Game starts: select a word to guess, assign one of the participants as
      explainer, present the word and taboo words to her
    - Game is in progress: check for taboo words or solutions
    - Solution has been said: end the game, record the winner, start a new game.
    - When new users enter while the game is in progress: make them guessers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        # the next session then starts automatically?
        # self.sessions = SessionManager(Session)
        self.sessions = SessionManager()

    def post_init(self, waiting_room):
        """
        save extra variables after the __init__() method has been called
        and create the init_base_dict: a dictionary containing
        needed arguments for the init event to send to the JS frontend
        """
        self.waiting_room = waiting_room

    def on_task_room_creation(self, data):
        """This function is executed as soon as 2 users are paired and a new
        task took is created
        """
        room_id = data["room"]

        task_id = data["task"]
        logging.debug(f"A new task room was created with id: {data['room']}")
        logging.debug(f"A new task room was created with task id: {data['task']}")
        logging.debug(f"This bot is looking for task id: {self.task_id}")
        if task_id is not None and task_id == self.task_id:
            # modify layout
            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])
            logging.debug("Create data for the new task room...")
            # create a new session for these users
            # this_session = self.sessions[room_id]
            self.sessions.create_session(room_id)

            for usr in data["users"]:
                # this_session.players.append({**usr, "msg_n": 0, "status": "joined"})
                self.sessions[room_id].players.append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )

            # join the newly created room
            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            #         roles
            # for user in data["users"]:
            #     this_session.players.append({**user, "status": "joined", "wins": 0})

            # now define in a sep function, so that it's possible to change the word
            # self.sessions[room_id].word_to_guess = self.sessions[room_id].words[0]["target_word"]

            # 2) Choose an explainer
            self.sessions[room_id].pick_explainer()
            for user in data["users"]:
                if user["id"] == self.sessions[room_id].explainer:
                    LOG.debug(f'{user["name"]} is the explainer.')
                else:
                    LOG.debug(f'{user["name"]} is the guesser.')

            response_e = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr",
                json={
                    "text": EXPLAINER_PROMPT,
                    "receiver_id": self.sessions[room_id].explainer,
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response_e.ok:
                LOG.error(f"Could not set task instruction: {response.status_code}")
                response_e.raise_for_status()

            response_g = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr",
                json={
                    "text": GUESSER_PROMPT,
                    "receiver_id": self.sessions[room_id].guesser,
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response_g.ok:
                LOG.error(f"Could not set task instruction: {response.status_code}")
                response_g.raise_for_status()

    @staticmethod
    def message_callback(success, error_msg="Unknown Error"):
        if not success:
            LOG.error(f"Could not send message: {error_msg}")
            exit(1)
        LOG.debug("Sent message successfully.")

    def register_callbacks(self):
        @self.sio.event
        def user_message(data):
            LOG.debug("Received a user_message.")
            LOG.debug(data)

            user = data["user"]
            message = data["message"]
            room_id = data["room"]
            # it sends to itself, user id = null, receiver if = null
            self.sio.emit("text", {"message": message, "room": room_id})

        @self.sio.event
        def status(data):
            """Triggered when a user enters or leaves a room."""
            room_id = data["room"]
            event = data["type"]
            user = data["user"]

            # don't do this for the bot itself
            if user["id"] == self.user:
                return

            # someone joined a task room
            if event == "join":
                # inform everyone about the join event
                self.send_message_to_user(
                    f"{user['name']} has joined the game.", room_id
                )

            elif event == "leave":
                self.send_message_to_user(f"{user['name']} has left the game.", room_id)

                # # remove this user from current session
                # this_session.players = list(
                #     filter(
                #         lambda player: player["id"] != user["id"], this_session.players
                #     )
                # )
                #

        @self.sio.event
        def command(data):
            if data["command"].startswith("ready"):
                self._command_ready(data["room"], data["user"]["id"])

        @self.sio.event
        def text_message(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a message from {data['user']['name']}: {data['message']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]

            if user_id == self.user:
                return

            this_session = self.sessions[room_id]
            this_session.log_next_turn()
            if data['message'] == "ready":
                self.send_message_to_user(
                    f"Pleasy type a backshlash before ready, like this '/ready'",
                    room_id,
                    user_id
                )
                return


            if this_session.explainer == user_id:
                # EXPLAINER sent a message
                self.update_interactions(room_id, "clue", data['message'])

                # means that new turn began?
                self.log_event("turn", dict(), room_id)

                # try logging event
                self.log_event("clue", {"content": data['message']}, room_id)

                self.set_message_privilege(self.sessions[room_id].explainer, False)
                self.make_input_field_unresponsive(
                    room_id, self.sessions[room_id].explainer
                )

                # check whether the explainer used a forbidden word
                explanation_errors = check_clue(
                    data["message"].lower(),
                    this_session.word_to_guess,
                    this_session.words[0]["related_word"],
                )
                # log that send message

                if explanation_errors:
                    message = explanation_errors[0]["message"]
                    self.update_interactions(room_id, "invalid clue", message)
                    self.log_event("invalid clue", {"content": message}, room_id)
                    # for player in this_session.players:
                    self.send_message_to_user(
                            f"{message}",
                            room_id,
                        )

                    self.load_next_state(room_id)
                else:
                    self.set_message_privilege(self.sessions[room_id].guesser, True)
                    # assign writing rights to other user
                    self.give_writing_rights(room_id, self.sessions[room_id].guesser)

            else:
                # GUESSER sent the command
                self.update_interactions(room_id, "guess", data['message'])
                self.log_event("guess", {"content": data['message']}, room_id)

                self.set_message_privilege(self.sessions[room_id].explainer, True)
                # assign writing rights to other user
                self.give_writing_rights(room_id, self.sessions[room_id].explainer)

                self.set_message_privilege(self.sessions[room_id].guesser, False)
                self.make_input_field_unresponsive(
                    room_id, self.sessions[room_id].guesser
                )
                valid_guess = check_guess(data["message"].lower())

                if not valid_guess:
                    self.update_interactions(room_id, "invalid format", "abort game")
                    self.log_event("invalid format", {"content": data['message']}, room_id)

                    # for player in this_session.players:
                    self.send_message_to_user(
                            f"INVALID GUESS: '{data['message'].lower()}' contains more than one word."
                            f"You both lose this round.",
                            room_id,
                            # player["id"],
                        )
                    self.load_next_state(room_id)
                    return

                guess_is_correct = correct_guess(this_session.word_to_guess, data["message"].lower())
                #  before 2 guesses were made
                if this_session.guesses < 2:
                    this_session.guesses += 1
                    if guess_is_correct:

                        self.update_interactions(room_id, "correct guess", data["message"].lower())
                        self.log_event("correct guess", {"content": data['message']}, room_id)

                        # for player in this_session.players:
                        self.send_message_to_user(
                                f"GUESS {this_session.guesses}: "
                                f"'{this_session.word_to_guess}' was correct! "
                                f"You both win this round.",
                                room_id,
                                # player["id"],
                            )
                        self.load_next_state(room_id)

                    else:

                        # for player in this_session.players:
                        self.send_message_to_user(
                                f"GUESS {this_session.guesses} '{data['message']}' was false",
                                room_id,
                                # player["id"],
                            )

                            # if player["id"] == this_session.explainer:
                        self.send_message_to_user(
                                    f"Please provide a new description",
                                    room_id,
                                    this_session.explainer,
                                )
                        self.set_message_privilege(
                            self.sessions[room_id].explainer, True
                        )
                        # assign writing rights to other user
                        self.give_writing_rights(room_id, self.sessions[room_id].explainer )
                        self.set_message_privilege(
                            self.sessions[room_id].guesser, False
                        )
                        self.make_input_field_unresponsive(
                            room_id, self.sessions[room_id].guesser
                        )

                else:
                    # last guess (guess 3)
                    this_session.guesses += 1
                    if guess_is_correct:
                        self.update_interactions(room_id, "correct guess", data["message"].lower())
                        self.log_event("correct guess", {"content": data['message']}, room_id)

                        # for player in this_session.players:
                        self.send_message_to_user(
                                f"GUESS {this_session.guesses}: {this_session.word_to_guess} was correct! "
                                f"You both win this round.",
                                room_id,
                                # player["id"],
                            )

                    else:
                        self.update_interactions(room_id, "max turns reached", str(3))
                        self.log_event("max turns reached", {"content": str(3)}, room_id)

                        # for player in this_session.players:
                        self.send_message_to_user(
                                f"3 guesses have been already used. You lost this round.",
                                room_id,
                                # player["id"],
                            )
                    self.load_next_state(room_id)
                self.set_message_privilege(self.sessions[room_id].explainer, True)

                # assign writing rights to other user
                self.give_writing_rights(room_id, self.sessions[room_id].explainer)

                self.set_message_privilege(self.sessions[room_id].guesser, False)

                # make input field unresponsive
                self.make_input_field_unresponsive(
                    room_id, self.sessions[room_id].guesser
                )

    def _command_ready(self, room_id, user_id):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            sleep(0.5)
            self.send_message_to_user(
                "You have already typed 'ready'.", room_id, curr_usr["id"]
            )

            return
        curr_usr["status"] = "ready"

        # both
        if other_usr["status"] == "ready":
            self.send_message_to_user("Woo-Hoo! The game will begin now.", room_id)
            self.start_round(room_id)
        else:
            self.send_message_to_user(
                "Now, waiting for your partner to type 'ready'.",
                room_id,
                curr_usr["id"],
            )

    def start_round(self, room_id):
        # self.send_message_to_user(f"{self.sessions[room_id].interactions}", room_id)

        if not self.sessions[room_id].words:
            self.close_room(room_id)
        # send the instructions for the round
        round_n = (WORDS_PER_ROOM - len(self.sessions[room_id].words)) + 1

        # try to log the round number
        self.log_event("round", {"number": round_n}, room_id)

        self.send_message_to_user(f"Let's start round {round_n}", room_id)
        self.send_message_to_user(
            "Wait a bit for the first hint about the word you need to guess",
            room_id,
            self.sessions[room_id].guesser,
        )

        self.sessions[room_id].word_to_guess = self.sessions[room_id].words[0][
            "target_word"
        ]
        taboo_words = ", ".join(self.sessions[room_id].words[0]["related_word"])
        self.sessions[room_id].guesses = 0

        self.send_message_to_user(
            f"Your task is to explain the word '{self.sessions[room_id].word_to_guess}'."
            f" You cannot use the following words: {taboo_words}",
            room_id,
            self.sessions[room_id].explainer,
        )

        # update writing_rights
        self.set_message_privilege(self.sessions[room_id].explainer, True)
        # assign writing rights to other user
        self.give_writing_rights(room_id, self.sessions[room_id].explainer)
        self.set_message_privilege(self.sessions[room_id].guesser, False)
        self.make_input_field_unresponsive(room_id, self.sessions[room_id].guesser)

    def load_next_state(self, room_id):
        # word list gets smaller, next round starts
        self.sessions[room_id].words.pop(0)
        if not self.sessions[room_id].words:
            self.close_room(room_id)
            return
        self.start_round(room_id)

    def close_room(self, room_id):
        # print message to close

        # LOG.info(f"{self.sessions[room_id].interactions}")
        # compute_scores(self.sessions[room_id].interactions)

        self.room_to_read_only(room_id)

        # remove any task room specific objects
        self.sessions.clear_session(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()

    def send_message_to_user(self, message, room, receiver=None):
        if receiver:
            self.sio.emit(
                "text",
                {"message": f"{message}", "room": room, "receiver_id": receiver},
            )
        else:
            self.sio.emit(
                "text",
                {"message": f"{message}", "room": room},
            )
        # sleep(1)

    def set_message_privilege(self, user_id, value):
        """
        change user's permission to send messages
        """
        # get permission_id based on user_id
        response = requests.get(
            f"{self.uri}/users/{user_id}/permissions",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "retrieving user's permissions")

        permission_id = response.json()["id"]
        requests.patch(
            f"{self.uri}/permissions/{permission_id}",
            json={"send_message": value},
            headers={
                "If-Match": response.headers["ETag"],
                "Authorization": f"Bearer {self.token}",
            },
        )
        self.request_feedback(response, "changing user's message permission")

    def make_input_field_unresponsive(self, room_id, user_id):
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "readonly",
                "value": "true",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "placeholder",
                "value": "Wait for a message from your partner",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def give_writing_rights(self, room_id, user_id):
        response = requests.delete(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "readonly",
                "value": "placeholder",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "placeholder",
                "value": "Enter your message here!",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )


    def update_interactions(self, room_id, type_, value_):
        turn_info = {"action": {"type": type_, "content": value_}}
        self.sessions[room_id].interactions["turns"][self.sessions[room_id].log_current_turn].append(turn_info)

def check_guess(user_guess):
     return len(user_guess.split()) == 1


def correct_guess(correct_answer, user_guess):
    return correct_answer in user_guess



def remove_punctuation(text: str) -> str:
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text


def check_clue(utterance: str, target_word: str, related_words):
    utterance = utterance.lower()
    utterance = remove_punctuation(utterance)
    # simply contain checks
    if target_word in utterance:
        return [
            {
                "message": f"Target word '{target_word}' was used in the clue. You both lose this round.",
                "type": 0,
            }
        ]
    for related_word in related_words:
        if related_word in utterance:
            return [
                {
                    "message": f"Related word '{related_word}' was used in the clue, You both lose this round",
                    "type": 1,
                }
            ]

    # lemma checks
    utterance = utterance.split(" ")
    filtered_clue = [word for word in utterance if word not in EN_STOPWORDS]
    target_lemma = EN_LEMMATIZER.lemmatize(target_word)
    related_lemmas = [
        EN_LEMMATIZER.lemmatize(related_word) for related_word in related_words
    ]
    errors = []
    for clue_word in filtered_clue:
        clue_lemma = EN_LEMMATIZER.lemmatize(clue_word)
        if clue_lemma == target_lemma:
            return [
                {
                    "message": f"Target word '{target_word}' is morphological similar to clue word '{clue_word}'",
                    "type": 0,
                }
            ]
        if clue_lemma in related_lemmas:
            return [
                {
                    "message": f"Related word is morphological similar to clue word '{clue_word}'",
                    "type": 1,
                }
            ]
    return errors

# def compute_scores(episode_interactions) -> None:
#     """ Episode level scores"""
#     turn_scores = []
#     prev_guess = None
#     prev_guess_counter = 0
#     prev_clue = None
#     prev_clue_counter = 0
#     invalid_response = False  # Note: This only takes into consideration that both players were compliant or not
#     guesser_won = False
#     for turn_idx, turn in enumerate(episode_interactions["turns"]):
#         turn_score = {"guess": None, "clue": None, "request_count": 1}
#
#         for event in turn:
#             action = event["action"]
#             if action["type"] == "invalid format":
#                 invalid_response = True
#             if action["type"] == "guess":
#                 turn_score["guess"] = action["content"]
#             if action["type"] == "clue":
#                 turn_score["clue"] = action["content"]
#             if action["type"] == "correct guess":
#                 guesser_won = True
#
#         if invalid_response:
#             turn_score["violated_request_count"] = 1
#             turn_score["parsed_request_count"] = 0
#         else:
#             turn_score["violated_request_count"] = 0
#             turn_score["parsed_request_count"] = 1
#
#         if turn_score["guess"] is not None and turn_score["guess"] == prev_guess:  # might be None, if clue is wrong
#             prev_guess_counter += 1
#         if turn_score["clue"] is not None and turn_score["clue"] == prev_clue:
#             prev_clue_counter += 1
#         # LOG.debug(f" {turn_idx}, 'Accuracy', 1 if guesser_won else 0)
#         LOG.debug(f'{turn_idx}, METRIC_REQUEST_COUNT_VIOLATED, {turn_score["violated_request_count"]}')
#         LOG.debug(f'{turn_idx}, METRIC_REQUEST_COUNT_PARSED, {turn_score["parsed_request_count"]}')
#         LOG.debug(f'{turn_idx}, METRIC_REQUEST_COUNT, {turn_score["request_count"]}')
#         prev_guess = turn_score["guess"]
#         prev_clue = turn_score["clue"]
#         turn_scores.append(turn_score)
#
#     violated_request_count = sum([turn["violated_request_count"] for turn in turn_scores])
#     LOG.debug(f"{METRIC_REQUEST_COUNT_VIOLATED}, {violated_request_count}")
#
#     parsed_request_count = sum([turn["parsed_request_count"] for turn in turn_scores])
#     LOG.debug(f"{METRIC_REQUEST_COUNT_PARSED}, {parsed_request_count}")
#
#     request_count = sum([turn["request_count"] for turn in turn_scores])
#     LOG.debug(f"{METRIC_REQUEST_COUNT}, {request_count}")
#
#     LOG.debug(f"{METRIC_REQUEST_SUCCESS}, {parsed_request_count / request_count}")
#     # checking the last guess (could be None) is ok,
#     # b.c. the game ends only successfully, when there is a correct guess

    # commented
    # # Common metrics
    # if invalid_response:  # whether a violation of the game rules happened (response not parsable)
    #     LOG.debug(METRIC_ABORTED, 1)
    #     LOG.debug(METRIC_SUCCESS, 0)
    #     LOG.debug(METRIC_LOSE, 0)
    #
    #     # Game-specific metrics
    #     # commendted this metric, import numpy!
    #     # self.log_episode_score(BENCH_SCORE, np.nan)  # metric not applicable
    # else:
    #     LOG.debug(METRIC_ABORTED, 0)
    #     if guesser_won:
    #         LOG.debug(METRIC_SUCCESS, 1)
    #         LOG.debug(METRIC_LOSE, 0)
    #         LOG.debug(BENCH_SCORE, 100 / len(turn_scores))  # how early the guesser found the word
    #     else:
    #         LOG.debug(METRIC_SUCCESS, 0)
    #         LOG.debug(METRIC_LOSE, 1)
    #         LOG.debug(BENCH_SCORE, 0)  # word not found
    #
    # # Game-specific metrics
    # # How often the Guesser repeated a guess
    # LOG.debug('Repetition-Guesser', prev_guess_counter)
    # # How often the Describer repeated itself
    # LOG.debug('Repetition-Describer', prev_clue_counter)
    # # this might require a side-loop between describer and GM (game should not continue with Guesser)
    # # self.log_episode_score('Rule-following', ...)

if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = TabooBot.create_argparser()

    if "WAITING_ROOM" in os.environ:
        waiting_room = {"default": os.environ["WAITING_ROOM"]}
    else:
        waiting_room = {"required": True}
    parser.add_argument(
        "--waiting_room",
        type=int,
        help="room where users await their partner",
        **waiting_room,
    )

    parser.add_argument(
        "--taboo_data",
        help="json file containing words",
        default=os.environ.get("TABOO_DATA"),
        # default="data/taboo_words.json",
    )
    args = parser.parse_args()

    # create bot instance
    taboo_bot = TabooBot(args.token, args.user, args.task, args.host, args.port)

    taboo_bot.post_init(args.waiting_room)

    # taboo_bot.taboo_data = args.taboo_data
    # connect to chat server
    taboo_bot.run()
