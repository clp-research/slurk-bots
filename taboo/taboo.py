import argparse
import logging
import os

import requests
import socketio

import random


LOG = logging.getLogger(__name__)


class TabooBot:
    """Bot that manages a taboo game.

    - Bot enters a room and starts a taboo game as soon as 2 participants are
      present.
    - Game starts: select a word to guess, assign one of the participants as
      explainer, present the word and taboo words to her
    - Game is in progress: check for taboo words or solutions
    - Solution has been said: end the game, record the winner, start a new game.
    - When new users enter while the game is in progress: make them guessers.
    """

    sio = socketio.Client(logger=True)
    task_id = None
    taboo_data = None

    def __init__(self, token, user, host, port):
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"

        LOG.info(f"Running taboo bot on {self.uri} with token {self.token}")
        # register all event handlers
        self.register_callbacks()

        self.players_per_room = dict()
        self.explainer_per_room = dict()
        self.word_to_guess = dict()
        # read the game data
        self.taboo_data = {
            "Applesauce": ["fruit", "tree", "glass", "preserving"],
            "Beef patty": ["pork", "ground", "steak"],
        }

    def run(self):
        # establish a connection to the server
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": self.user},
            namespaces="/",
        )
        # wait until the connection with the server ends
        self.sio.wait()

    @staticmethod
    def message_callback(success, error_msg="Unknown Error"):
        if not success:
            LOG.error(f"Could not send message: {error_msg}")
            exit(1)
        LOG.debug("Sent message successfully.")

    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            self.user = data["user"]

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

                # keep track of users per room
                if not self.players_per_room.get(room_id):
                    self.players_per_room[room_id] = []
                    self.explainer_per_room[room_id] = None

                self.players_per_room[room_id].append(
                    {**user, "status": "joined", "wins": 0}
                )

                if len(self.players_per_room[room_id]) < 2:
                    self.sio.emit(
                        "text",
                        {"message": "Let's wait for more players.", "room": room_id},
                    )
                else:
                    # TODO: check whether a game is already in progress
                    # start a game
                    # 1) Choose a word
                    self.word_to_guess[room_id] = random.choice(
                        list(self.taboo_data.keys())
                    )
                    # 2) Choose an explainer
                    self.explainer_per_room[room_id] = random.choice(
                        self.players_per_room[room_id]
                    )["id"]
                    # 3) Tell the explainer about the word
                    self.sio.emit(
                        "text",
                        {
                            "message": f"Your task is to explain the word {self.word_to_guess[room_id]}. You cannot use the following words: {self.taboo_data[self.word_to_guess[room_id]]}",
                            "room": room_id,
                            "receiver_id": self.explainer_per_room[room_id],
                        },
                    )
                    # 4) Tell everyone else that the game has started
                    for player in self.players_per_room[room_id]:
                        if player["id"] != self.explainer_per_room[room_id]:
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

                self.players_per_room[room_id] = {
                    player
                    for player in self.players_per_room[room_id].keys()
                    if player["id"] != user["id"]
                }

                if len(self.players_per_room[room_id]) < 2:
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

            if user_id == self.user:
                return

            # explainer or guesser?
            if self.explainer_per_room[room_id] == user_id:
                LOG.debug(f"{data['user']['name']} is the explainer.")

                # check whether the user used a forbidden word
                for taboo_word in self.taboo_data[self.word_to_guess[room_id]]:
                    if taboo_word in data["message"]:
                        self.sio.emit(
                            "text",
                            {
                                "message": f"You used the taboo word {taboo_word}!",
                                "room": room_id,
                            },
                        )
            elif self.word_to_guess[room_id] in data["message"]:
                self.sio.emit(
                    "text",
                    {
                        "message": f"{self.word_to_guess[room_id]} was correct!",
                        "room": room_id,
                    },
                )


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = argparse.ArgumentParser(description="Run Taboo Bot.")

    # collect environment variables as defaults
    if "SLURK_TOKEN" in os.environ:
        token = {"default": os.environ["SLURK_TOKEN"]}
    else:
        token = {"required": True}
    if "SLURK_USER" in os.environ:
        user = {"default": os.environ["SLURK_USER"]}
    else:
        user = {"required": True}
    host = {"default": os.environ.get("SLURK_HOST", "http://localhost")}
    port = {"default": os.environ.get("SLURK_PORT")}
    taboo_data = {"default": os.environ.get("TABOO_DATA")}

    # register commandline arguments
    parser.add_argument("-t", "--token", help="token for logging in as bot", **token)
    parser.add_argument("-u", "--user", help="user id for the bot", **user)
    parser.add_argument(
        "-c", "--host", help="full URL (protocol, hostname) of chat server", **host
    )
    parser.add_argument("-p", "--port", type=int, help="port of chat server", **port)
    parser.add_argument("--taboo_data", help="json file containing words", **taboo_data)
    args = parser.parse_args()

    # create bot instance
    taboo_bot = TabooBot(args.token, args.user, args.host, args.port)
    # taboo_bot.taboo_data = args.taboo_data
    # connect to chat server
    taboo_bot.run()
