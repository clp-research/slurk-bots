from collections import defaultdict
import logging
import os
import string

import requests

from templates import TaskBot
from time import sleep
from threading import Timer

import random


LOG = logging.getLogger(__name__)

TIMEOUT_TIMER = 5  # minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 3  # minutes if a user is alone in a room


class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()
        self.left_room = dict()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER * 60, self.function, args=[self.room_id, "timeout"]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.info("reset timer")

    def cancel(self):
        self.timer.cancel()

    def cancel_all_timers(self):
        self.timer.cancel()
        for timer in self.left_room.values():
            timer.cancel()

    def user_joined(self, user):
        timer = self.left_room.get(user)
        if timer is not None:
            self.left_room[user].cancel()

    def user_left(self, user):
        self.left_room[user] = Timer(
            LEAVE_TIMER * 60, self.function, args=[self.room_id, "user_left"]
        )
        self.left_room[user].start()


class Session:
    def __init__(self):
        self.players = list()
        self.explainer = None
        self.word_to_guess = None
        self.game_over = False
        self.win = False
        self.guesser = None

    def close(self):
        pass

    def pick_explainer(self):
        self.explainer = random.choice(self.players)["id"]

    def pick_guesser(self):
        for player in self.players:
            if player["id"] != self.explainer:
                self.guesser = player["id"]


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
        self.taboo_data = {
            "Applesauce": ["fruit", "tree", "glass", "preserving"],
            "Beef patty": ["pork", "ground", "steak"],
        }

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
                        "message": f"{user['name']} has joined the game. ",
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
                    # 2) Choose an explainer and a guesser
                    this_session.pick_explainer()
                    this_session.pick_guesser()

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

        @self.sio.event
        def text_message(data):
            """Triggered when a text message is sent.
            Check that it didn't contain any forbidden words if sent
            by explainer or whether it was the correct answer when sent
            by a guesser.
            """
            LOG.debug(f"Received a message from {data['user']['name']}.")

            room_id = data["room"]
            user_id = data["user"]["id"]

            this_session = self.sessions[room_id]
            word_to_guess = this_session.word_to_guess
            new_line = '\n'

            if user_id == self.user:
                return

            # explainer
            if this_session.explainer == user_id:
                LOG.debug(f"{data['user']['name']} is the explainer.")
                message = data["message"].lower()
                # check whether the user used a forbidden word
                for taboo_word in self.taboo_data[word_to_guess]:
                    if taboo_word.lower() in message:
                        self.sio.emit(
                            "text",
                            {
                                "message": f"You used the taboo word {taboo_word}! GAME OVER :(",
                                "room": room_id,
                                "receiver_id": this_session.explainer,
                            },
                        )
                        self.sio.emit(
                            "text",
                            {
                                "message": f"{data['user']['name']} used a taboo word. You both lose!",
                                "room": room_id,
                                "receiver_id": this_session.guesser,
                            },
                        )
                        self.sessions.game_over = True
                # check whether the user used the word to guess
                if word_to_guess.lower() in message:
                    self.sio.emit(
                        "text",
                        {
                            "message": f"You used the word to guess '{word_to_guess}'! {new_line}GAME OVER",
                            "room": room_id,
                        },
                    )
                    self.sessions.game_over = True
            # Guesser
            elif word_to_guess.lower() in data["message"].lower():
                self.sio.emit(
                    "text",
                    {
                        "message": f"{word_to_guess} was correct! {new_line}YOU WON :)",
                        "room": room_id,
                    },
                )
                self.sessions.win = True

        def remove_punctuation(text: str) -> str:
            text = text.translate(str.maketrans("", "", string.punctuation))
            return text


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = TabooBot.create_argparser()

    parser.add_argument(
        "--taboo_data",
        help="json file containing words",
        default=os.environ.get("TABOO_DATA"),
    )
    args = parser.parse_args()

    # create bot instance
    taboo_bot = TabooBot(args.token, args.user, args.task, args.host, args.port)
    # taboo_bot.taboo_data = args.taboo_data
    # connect to chat server
    taboo_bot.run()
