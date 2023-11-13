from collections import defaultdict
import logging
import os
import json

import requests
from time import sleep

from taboo.config import TABOO_WORDS
from templates import TaskBot

import random

import os




LOG = logging.getLogger(__name__)


class Session:
    # what happens between 2 players
    def __init__(self):
        self.players = list()
        self.explainer = None
        self.word_to_guess = None
        self.guesses = 0
        self.guessed = False

    def close(self):
        pass

    def pick_explainer(self):
        self.explainer = random.choice(self.players)["id"]

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
            self.sio.emit("text", {"message": message, "room": room_id})

        @self.sio.event
        def status(data):
            """Triggered when a user enters or leaves a room."""
            room_id = data["room"]
            event = data["type"]
            user = data["user"]

            # automatically creates a new session if not present
            this_session = self.sessions[room_id]

            # don't do this for the bot itself
            if user["id"] == self.user:
                return

            # someone joined a task room
            if event == "join":
                # inform everyone about the join event
                self.sio.emit(
                    "text",
                    {
                        "message": f"{user['name']} has joined the game.",
                        "room": room_id,
                    },
                )

                this_session.players.append({**user, "status": "joined", "wins": 0})

                if len(this_session.players) < 2:
                    self.sio.emit(
                        "text",
                        {"message": "Let's wait for more players.", "room": room_id},
                    )
                else:
                    # TODO: check whether a game is already in progress
                    # start a game
                    # 1) Choose a word
                    this_session.word_to_guess = random.choice(
                        list(self.taboo_data.keys())
                    )
                    # 2) Choose an explainer
                    this_session.pick_explainer()

                    # 3) Tell the explainer about the word
                    word_to_guess = this_session.word_to_guess
                    taboo_words = ", ".join(self.taboo_data[word_to_guess])
                    self.sio.emit(
                        "text",
                        {
                            "message": f"Your task is to explain the word {word_to_guess}. You cannot use the following words: {taboo_words}",
                            "room": room_id,
                            "receiver_id": this_session.explainer,
                        },
                    )
                    # 4) Tell everyone else that the game has started
                    for player in this_session.players:
                        if player["id"] != this_session.explainer:
                            self.sio.emit(
                                "text",
                                {
                                    "message": "The game has started. Try to guess the word!",
                                    "room": room_id,
                                    "receiver_id": player["id"],
                                },
                            )

            elif event == "leave":
                self.sio.emit(
                    "text",
                    {"message": f"{user['name']} has left the game.", "room": room_id},
                )

                # remove this user from current session
                this_session.players = list(
                    filter(
                        lambda player: player["id"] != user["id"], this_session.players
                    )
                )

                if len(this_session.players) < 2:
                    self.sio.emit(
                        "text",
                        {
                            "message": "You are alone in the room, let's wait for some more players.",
                            "room": room_id,
                        },
                    )

        # @self.sio.event
        # def text_message(data):
        #     """Triggered when a text message is sent.
        #     Check that it didn't contain any forbidden words if sent
        #     by explainer or whether it was the correct answer when sent
        #     by a guesser.
        #     """
        #     LOG.debug(f"Received a message from {data['user']['name']}.")
        #
        #     room_id = data["room"]
        #     user_id = data["user"]["id"]
        #
        #     this_session = self.sessions[room_id]
        #
        #     if user_id == self.user:
        #         return
        #
        #     # explainer or guesser?
        #     if this_session.explainer == user_id:
        #         LOG.debug(f"{data['user']['name']} is the explainer.")
        #
        #         # check whether the user used a forbidden word
        #         for taboo_word in self.taboo_data[this_session.word_to_guess]:
        #             if taboo_word in data["message"]:
        #                 self.sio.emit(
        #                     "text",
        #                     {
        #                         "message": f"You used the taboo word {taboo_word}!",
        #                         "room": room_id,
        #                         "receiver_id": this_session.explainer
        #
        #                     },
        #                 )
        #
        #     elif this_session.word_to_guess.lower() in data["message"].lower():
        #         self.sio.emit(
        #             "text",
        #             {
        #                 "message": f"{this_session.word_to_guess} was correct!",
        #                 "room": room_id,
        #             },
        #         )




        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]

            this_session = self.sessions[room_id]

            if user_id == self.user:
                return

            # EXPLAINER sent a command
            if this_session.explainer == user_id:
                LOG.debug(f"{data['user']['name']} is the explainer.")

            # check whether the user used a forbidden word
                explanation_legal = check_explanation(data['command'],
                                                       self.taboo_data[this_session.word_to_guess])
                if explanation_legal:
                    for player in this_session.players:
                        if player["id"] != this_session.explainer:
                            send_message_to_user(self.sio, f"HINT: {data['command']}",
                                                 room_id, player["id"])
                else:
                    send_message_to_user(self.sio, f"You used the taboo word. You lost.",
                                         room_id, this_session.explainer)

            else:
                #GUESSER sent the command

                #  before 2 guesses were made
                if this_session.guesses < 2:
                    this_session.guesses += 1
                    if check_guess(this_session.word_to_guess, data["command"]):
                        for player in this_session.players:
                            send_message_to_user(self.sio,f"GUESS {this_session.guesses}: '{this_session.word_to_guess}' was correct! "
                                                          f"You both win",
                                             room_id, player["id"])
                        sleep(1)
                        self.close_room(room_id)
                    else:
                        for player in this_session.players:
                            send_message_to_user(self.sio, f"GUESS {this_session.guesses} '{data['command']}' was false",
                                                 room_id, player["id"])

                            if player["id"] == this_session.explainer:
                                send_message_to_user(self.sio, f"Please provide a new description",
                                                     room_id, this_session.explainer)

                else:
                    # last guess (guess 3)
                    this_session.guesses += 1
                    if check_guess(this_session.word_to_guess, data["command"]):
                        for player in this_session.players:
                            send_message_to_user(self.sio,f" GUESS {this_session.guesses}: {this_session.word_to_guess} was correct! "
                                                              f"You both win.",
                                             room_id, player["id"])
                    else:
                        for player in this_session.players:
                            send_message_to_user(self.sio, f"3 guesses have been already used. You lost.",
                                                     room_id, player["id"])
                    sleep(1)
                    self.close_room(room_id)


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


def send_message_to_user(sio_object, message, room, receiver):
    sio_object.emit(
        "text",
        {
            "message": f"{message}",
            "room": room,
            "receiver_id": receiver
        },
    )


def check_guess(correct_answer, user_guess):
    if correct_answer in user_guess:
        return True
    return False






def check_explanation(explanation, taboo_words):
    explanation_legal = True
    for word in taboo_words:
        if word in explanation:
            explanation_legal = False
            return explanation_legal
    return explanation_legal


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = TabooBot.create_argparser()

    parser.add_argument(
        "--taboo_data",
        help="json file containing words",
        default=os.environ.get("TABOO_DATA"),
        # default="data/taboo_words.json",
    )
    args = parser.parse_args()

    # create bot instance
    taboo_bot = TabooBot(args.token, args.user, args.task, args.host, args.port)


    # taboo_bot.taboo_data = args.taboo_data
    # connect to chat server
    taboo_bot.run()
