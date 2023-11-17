from collections import defaultdict
import logging

import requests
from time import sleep

from taboo.config import TABOO_WORDS, EXPLAINER_PROMPT, GUESSER_PROMPT
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
        self.guesser = None

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
                # self.sio.emit(
                #     "text",
                #     {"message": f"{user['name']} has left the game.", "room": room_id}
                #
                # )
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

            if user_id == self.user:
                return

            this_session = self.sessions[room_id]

            if data["command"].startswith("ready"):
                self._command_ready(this_session, room_id, user_id)

            # EXPLAINER sent a command
            else:
                if this_session.explainer == user_id:
                    LOG.debug(f"{data['user']['name']} is the explainer.")

                    # check whether the user used a forbidden word
                    explanation_legal = check_explanation(
                        data["command"].lower(),
                        self.taboo_data[this_session.word_to_guess],
                        this_session.word_to_guess,
                    )
                    if explanation_legal:
                        self.send_message_to_user(
                            f"HINT: {data['command']}", room_id, this_session.guesser
                        )
                    else:
                        for player in this_session.players:
                            self.send_message_to_user(
                                f"The taboo word was used in the explanation. You both lost.",
                                room_id,
                                player["id"],
                            )
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
                            for player in this_session.players:
                                self.send_message_to_user(
                                    f"GUESS {this_session.guesses}: "
                                    f"'{this_session.word_to_guess}' was correct! "
                                    f"You both win",
                                    room_id,
                                    player["id"],
                                )
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


def check_guess(correct_answer, user_guess):
    if correct_answer in user_guess:
        return True
    return False


def check_explanation(explanation, taboo_words, word):
    taboo_words.append(word)
    for word in taboo_words:
        if word in explanation:
            return False
    return True


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
