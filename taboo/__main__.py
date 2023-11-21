from collections import defaultdict
import logging

import requests
from time import sleep

from taboo.config import TABOO_WORDS, EXPLAINER_PROMPT, GUESSER_PROMPT, RESULTS_PATH
from templates import TaskBot

import random

import os

import nltk
from nltk.corpus import stopwords
import string

nltk.download('stopwords', quiet=True)
EN_STOPWORDS = stopwords.words('english')
nltk.download('wordnet')
nltk.download('stopwords', quiet=True)
EN_LEMMATIZER = nltk.stem.WordNetLemmatizer()

from taboo.metrics import METRIC_ABORTED, METRIC_SUCCESS, METRIC_LOSE, METRIC_REQUEST_COUNT, \
    METRIC_REQUEST_COUNT_VIOLATED, METRIC_REQUEST_COUNT_PARSED, METRIC_REQUEST_SUCCESS, BENCH_SCORE

from typing import List, Dict, Tuple, Any

from datetime import datetime

from .utils import save_file
LOG = logging.getLogger(__name__)


class Session:
    # what happens between 2 players
    def __init__(self):
        self.players = list()
        self.word_to_guess = None
        self.guesses = 0
        self.guessed = False
        self.explainer = None
        self.guesser = None
        self.interactions = {
            "players": self.players,
            "turns": []
        }
        self.log_current_turn = -1

    def log_next_turn(self):
        """ Call this method to group interactions per turn """
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
        self.sessions = SessionManager(Session)

        # TODO: read the game data from file
        self.taboo_data = TABOO_WORDS
        # self.taboo_data = {
        #             "Applesauce": ["fruit", "tree", "glass", "preserving"],
        #             "Beef patty": ["pork", "ground", "steak"],
        #         }

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

        logging.debug(f"A new task room was created with id: {data['task']}")
        logging.debug(f"This bot is looking for task id: {self.task_id}")
        if task_id is not None and task_id == self.task_id:
            # modify layout
            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])
                # create a new session for these users
            logging.debug("Create data for the new task room...")
            this_session = self.sessions[room_id]

            for usr in data["users"]:
                this_session.players.append({**usr, "msg_n": 0, "status": "joined"})

            # join the newly created room
            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            #         roles
            # for user in data["users"]:
            #     this_session.players.append({**user, "status": "joined", "wins": 0})

            this_session.word_to_guess = random.choice(list(self.taboo_data.keys()))
            # 2) Choose an explainer
            this_session.pick_explainer()
            for user in data["users"]:
                if user["id"] == this_session.explainer:
                    LOG.debug(f'{user["name"]} is the explainer.')
                else:
                    LOG.debug(f'{user["name"]} is the guesser.')


            # 3) Tell the explainer about the word
            word_to_guess = this_session.word_to_guess
            # taboo_words = ", ".join(self.taboo_data[word_to_guess])

            response_e = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr",
                json={"text": EXPLAINER_PROMPT, "receiver_id": this_session.explainer},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response_e.ok:
                LOG.error(f"Could not set task instruction: {response.status_code}")
                response_e.raise_for_status()

            response_g = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr",
                json={"text": GUESSER_PROMPT, "receiver_id": this_session.guesser},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response_g.ok:
                LOG.error(f"Could not set task instruction: {response.status_code}")
                response_g.raise_for_status()

            # self.send_message_to_user(EXPLAINER_PROMPT, room_id, this_session.explainer)
            #
            # When to send th ewprd to the explainer?
            # if this_session.ready:
            #     self.send_message_to_user(
            #     f"Your task is to explain the word '{word_to_guess}'."
            #     f" You cannot use the following words: {taboo_words}",
            #     room_id,
            #     this_session.explainer,
            # )
            # # 4) Provide the instructions to the guesser
            # self.send_message_to_user(GUESSER_PROMPT, room_id, this_session.guesser)

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
            # to whom is it sent?
            self.sio.emit("text", {"message": message, "room": room_id})

        @self.sio.event
        def status(data):
            """Triggered when a user enters or leaves a room."""
            room_id = data["room"]
            event = data["type"]
            user = data["user"]

            # automatically creates a new session if not present
            # this_session = self.sessions[room_id]

            # don't do this for the bot itself
            if user["id"] == self.user:
                return

            # someone joined a task room
            if event == "join":
                # inform everyone about the join event
                self.send_message_to_user(
                    f"{user['name']} has joined the game.", room_id
                )

                # this_session.players.append({**user, "status": "joined", "wins": 0})

                # if len(this_session.players) < 2:
                #     self.sio.emit(
                #         "text",
                #         {"message": "Let's wait for more players.", "room": room_id},
                #     )
                # else:
                # TODO: check whether a game is already in progress
                # start a game
                # 1) Choose a word
                # this_session.word_to_guess = random.choice(
                #     list(self.taboo_data.keys())
                # )
                # # 2) Choose an explainer
                # this_session.pick_explainer()
                #
                # # 3) Tell the explainer about the word
                # word_to_guess = this_session.word_to_guess
                # taboo_words = ", ".join(self.taboo_data[word_to_guess])
                # self.sio.emit(
                #     "text",
                #     {
                #         "message": f"Your task is to explain the word {word_to_guess}. You cannot use the following words: {taboo_words}",
                #         "room": room_id,
                #         "receiver_id": this_session.explainer,
                #     },
                # )
                # # 4) Tell everyone else that the game has started
                # for player in this_session.players:
                #     if player["id"] != this_session.explainer:
                #         self.sio.emit(
                #             "text",
                #             {
                #                 "message": "The game has started. Try to guess the word!",
                #                 "room": room_id,
                #                 "receiver_id": player["id"],
                #             },
                #         )

            elif event == "leave":
                self.send_message_to_user(f"{user['name']} has left the game.", room_id)

                # # remove this user from current session
                # this_session.players = list(
                #     filter(
                #         lambda player: player["id"] != user["id"], this_session.players
                #     )
                # )
                #
                # if len(this_session.players) < 2:
                #     self.sio.emit(
                #         "text",
                #         {
                #             "message": "You are alone in the room, let's wait for some more players.",
                #             "room": room_id,
                #         },
                #     )

        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]

            if user_id == self.user:
                return

            this_session = self.sessions[room_id]

            if data["command"].startswith("ready"):
                self._command_ready(this_session, room_id, user_id)

            # EXPLAINER sent a command
            else:
                this_session.log_next_turn()
                if this_session.explainer == user_id:

                    # check whether the user used a forbidden word
                    explanation_errors = check_clue(
                        data["command"].lower(),
                        this_session.word_to_guess,
                        self.taboo_data[this_session.word_to_guess],

                    )

                    if not explanation_errors:
                        self.log_event(this_session, "GM", "GM", "valid format", "continue")

                        self.send_message_to_user(
                            f"HINT: {data['command']}", room_id, this_session.guesser
                        )
                    else:
                        error_type = explanation_errors[0]["type"]
                        if error_type == 0:
                            self.log_event(this_session, "GM", "GM", "invalid clue", "clue contains target word")
                        if error_type == 1:
                            self.log_event(this_session, "GM", "GM", "invalid clue", "clue contains related word")

                        message = explanation_errors[0]["message"]
                        for player in this_session.players:
                            self.send_message_to_user(
                                f"{message}",
                                room_id,
                                player["id"],
                            )
                        self.store_records(this_session)

                        sleep(1)
                        self.close_room(room_id)

                else:
                    # GUESSER sent the command

                    #  before 2 guesses were made
                    if this_session.guesses < 2:
                        this_session.guesses += 1
                        if check_guess(
                            this_session.word_to_guess, data["command"].lower()
                        ):
                            self.log_event(this_session, "GM", "GM", "correct guess", data["command"].lower())

                            for player in this_session.players:
                                self.send_message_to_user(
                                    f"GUESS {this_session.guesses}: "
                                    f"'{this_session.word_to_guess}' was correct! "
                                    f"You both win",
                                    room_id,
                                    player["id"],
                                )

                            self.store_records(this_session)
                            sleep(1)
                            self.close_room(room_id)
                        else:
                            for player in this_session.players:
                                self.send_message_to_user(
                                    f"GUESS {this_session.guesses} '{data['command']}' was false",
                                    room_id,
                                    player["id"],
                                )

                                if player["id"] == this_session.explainer:
                                    self.send_message_to_user(
                                        f"Please provide a new description",
                                        room_id,
                                        this_session.explainer,
                                    )

                    else:
                        # last guess (guess 3)
                        this_session.guesses += 1
                        if check_guess(
                            this_session.word_to_guess, data["command"].lower()
                        ):
                            for player in this_session.players:
                                self.send_message_to_user(
                                    f"GUESS {this_session.guesses}: {this_session.word_to_guess} was correct! "
                                    f"You both win.",
                                    room_id,
                                    player["id"],
                                )
                        else:
                            for player in this_session.players:
                                self.send_message_to_user(
                                    f"3 guesses have been already used. You lost.",
                                    room_id,
                                    player["id"],
                                )
                        self.store_records(this_session)
                        sleep(1)
                        self.close_room(room_id)

    def _command_ready(self, session, room_id, user_id):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = session.players
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            # sleep(0.5)
            self.sio.emit(
                "text",
                {
                    "message": "You have already typed 'ready'.",
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                },
            )
            return
        curr_usr["status"] = "ready"

        # both
        if other_usr["status"] == "ready":
            self.sio.emit(
                "text",
                {"message": "Woo-Hoo! The game will begin now.", "room": room_id},
            )
            self.sio.emit(
                "text",
                {
                    "message": "Wait a bit for the first hint about the word you need to guess",
                    "room": room_id,
                    "receiver_id": session.guesser,
                },
            )

            #     now send the word to the explainer?? Here?
            taboo_words = ", ".join(self.taboo_data[session.word_to_guess])
            self.send_message_to_user(
                f"Your task is to explain the word '{session.word_to_guess}'."
                f" You cannot use the following words: {taboo_words}",
                room_id,
                session.explainer,
            )
        else:
            self.sio.emit(
                "text",
                {
                    "message": "Now, waiting for your partner to type 'ready'.",
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                },
            )

    def close_room(self, room_id):
        # print message to close

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

    def log_event(self, session, from_: str, to: str, type_, value):
        """
        Add an event to the internal log. It can be only an action or an action
        plus an API call that should have the same timestamp as the action.

        call, if given, is a tuple whose first element is the input prompt
        object (after API-specific manipulation) as passed to the API and the
        second element is the raw response object as returned by the API.
        """
        assert session.log_current_turn >= 0, f"Call log_add_new_turn at least once " \
                                           f"(log_current_turn={session.log_current_turn})"
        action = {'type': type_, 'content': value}

        timestamp = datetime.now().isoformat()
        action_obj = {
            "from": from_,
            "to": to,
            "timestamp": timestamp,
            "action": action
        }

        session.interactions["turns"][session.log_current_turn].append(action_obj.copy())
        LOG.info(
            f"Logged {action['type']} action ({from_}->{to}).")

    def store_records(self, session):
        """Raise warnings if a mandatory element is empty or format is wrong."""
        if not session.interactions["players"]:
            LOG.warning(f"Players metadada is missing!")
        # else:
        #     for name in session.interactions["players"]:
        #         """The transcript builder relies on specific player identifiers."""
        #         try:
        #             assert name == "GM" or name.startswith("Player ")
        #         except AssertionError:
        #             self.logger.warning(f"Invalid player identifiers, html builder won't work.")
        if not session.interactions["turns"]:
            LOG.warning(f"Interaction logs are missing!")

        # if not self.requests:
        #     self.logger.warning(f"No calls logged!")

        # self.store_results_file(self.interactions, "interactions.json", sub_dir=game_record_dir)

        # in the current dict
        self.store_results_file(session.interactions, f"{RESULTS_PATH}/interactions.json")
        # self.store_results_file(self.requests, "requests.json", sub_dir=game_record_dir)


    def store_results_file(self, data, file_name: str):
        """
        Store a results file in your game results' directory. The top-level directory is 'results'.

        :param sub_dir: automatically created when given; otherwise an error will be thrown.
        :param data: to store
        :param file_name: can have subdirectories e.g. "sub/my_file"
        """
        save_file(data, file_name)
        LOG.info(f"interactions saved, {data}")


def check_guess(correct_answer, user_guess):
    if correct_answer in user_guess:
        return True
    return False



def remove_punctuation(text: str) -> str:
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text

def check_clue(utterance: str, target_word: str, related_words):
    utterance = utterance.lower()
    utterance = remove_punctuation(utterance)
    # simply contain checks
    if target_word in utterance:
        return [{
            "message": f"Target word '{target_word}' was used in the clue. You both lose.",
            "type": 0
        }]
    for related_word in related_words:
        if related_word in utterance:
            return [{
                "message": f"Related word '{related_word}' was used in the clue, You both lose",
                "type": 1
            }]

    # lemma checks
    utterance = utterance.split(" ")
    filtered_clue = [word for word in utterance if word not in EN_STOPWORDS]
    target_lemma = EN_LEMMATIZER.lemmatize(target_word)
    related_lemmas = [EN_LEMMATIZER.lemmatize(related_word) for related_word in related_words]
    errors = []
    for clue_word in filtered_clue:
        clue_lemma = EN_LEMMATIZER.lemmatize(clue_word)
        if clue_lemma == target_lemma:
            return [{
                "message": f"Target word '{target_word}' is morphological similar to clue word '{clue_word}'",
                "type": 0
            }]
        if clue_lemma in related_lemmas:
            return [{
                "message": f"Related word is morphological similar to clue word '{clue_word}'",
                "type": 1
            }]
    return errors


# def compute_scores(self, episode_interactions: Dict) -> None:
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
#         self.log_turn_score(turn_idx, 'Accuracy', 1 if guesser_won else 0)
#         self.log_turn_score(turn_idx, METRIC_REQUEST_COUNT_VIOLATED, turn_score["violated_request_count"])
#         self.log_turn_score(turn_idx, METRIC_REQUEST_COUNT_PARSED, turn_score["parsed_request_count"])
#         self.log_turn_score(turn_idx, METRIC_REQUEST_COUNT, turn_score["request_count"])
#         prev_guess = turn_score["guess"]
#         prev_clue = turn_score["clue"]
#         turn_scores.append(turn_score)
#
#     violated_request_count = sum([turn["violated_request_count"] for turn in turn_scores])
#     self.log_episode_score(METRIC_REQUEST_COUNT_VIOLATED, violated_request_count)
#
#     parsed_request_count = sum([turn["parsed_request_count"] for turn in turn_scores])
#     self.log_episode_score(METRIC_REQUEST_COUNT_PARSED, parsed_request_count)
#
#     request_count = sum([turn["request_count"] for turn in turn_scores])
#     self.log_episode_score(METRIC_REQUEST_COUNT, request_count)
#
#     self.log_episode_score(METRIC_REQUEST_SUCCESS, parsed_request_count / request_count)
#     # checking the last guess (could be None) is ok,
#     # b.c. the game ends only successfully, when there is a correct guess
#
#     # Common metrics
#     if invalid_response:  # whether a violation of the game rules happened (response not parsable)
#         self.log_episode_score(METRIC_ABORTED, 1)
#         self.log_episode_score(METRIC_SUCCESS, 0)
#         self.log_episode_score(METRIC_LOSE, 0)
#
#         # Game-specific metrics
#         # commendted this metric, import numpy!
#         # self.log_episode_score(BENCH_SCORE, np.nan)  # metric not applicable
#     else:
#         self.log_episode_score(METRIC_ABORTED, 0)
#         if guesser_won:
#             self.log_episode_score(METRIC_SUCCESS, 1)
#             self.log_episode_score(METRIC_LOSE, 0)
#             self.log_episode_score(BENCH_SCORE, 100 / len(turn_scores))  # how early the guesser found the word
#         else:
#             self.log_episode_score(METRIC_SUCCESS, 0)
#             self.log_episode_score(METRIC_LOSE, 1)
#             self.log_episode_score(BENCH_SCORE, 0)  # word not found
#
#     # Game-specific metrics
#     # How often the Guesser repeated a guess
#     self.log_episode_score('Repetition-Guesser', prev_guess_counter)
#     # How often the Describer repeated itself
#     self.log_episode_score('Repetition-Describer', prev_clue_counter)
#     # this might require a side-loop between describer and GM (game should not continue with Guesser)
#     # self.log_episode_score('Rule-following', ...)

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
