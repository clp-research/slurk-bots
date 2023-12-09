import logging
import os

from time import sleep


import requests
from templates import TaskBot

import logging

from wordle_words.config import GUESSER_PROMPT,  WORDLE_WORDS, WORDS_PER_ROOM
from wordle_words.dataloader import Dataloader


LOG = logging.getLogger(__name__)

class Session:
    def __init__(self):
        self.players = list()
        self.guesser = None
        self.words = Dataloader(WORDLE_WORDS, WORDS_PER_ROOM)
        self.word_to_guess = None

class SessionManager(dict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)

class WordleBot(TaskBot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.sessions = SessionManager()
        self.register_callbacks()

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
                self.sessions[room_id].players.append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )
            #     only one player, do wee need players/guesser?/
            self.sessions[room_id].guesser = data["users"][0]["id"]

            # join the newly created room
            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.send_instructions(room_id)
        self.sio.emit(
            "text",
            {
                "message": (
                    "Are you ready? <br>"
                    "<button class='message_button' onclick=\"confirm_ready('yes')\">YES</button> "
                    "<button class='message_button' onclick=\"confirm_ready('no')\">NO</button>"
                ),
                "room": room_id,
                # "receiver_id": player["id"],
                "html": True,
            },
        )

    @staticmethod
    def message_callback(success, error_msg="Unknown Error"):
        if not success:
            LOG.error(f"Could not send message: {error_msg}")
            exit(1)
        LOG.debug("Sent message successfully.")

    def register_callbacks(self):

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
                sleep(0.5)

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
        def text_message(data):
            """load next state after the user enters a description"""
            if self.user == data["user"]["id"]:
                return
            room_id = data["room"]



        @self.sio.event
        def command(data):
            """Parse user commands."""
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not prcess commands from itself
            if user_id == self.user:
                return

            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            if isinstance(data["command"], dict):
                # commands from interface
                event = data["command"]["event"]
                if event == "confirm_ready":
                    if data["command"]["answer"] == "yes":
                        self._command_ready(data["room"], data["user"])
                    elif data["command"]["answer"] == "no":
                        self.send_message_to_user(
                            "OK, read the instructions carefully and click on <yes> once you are ready.",
                            data["room"],
                            data["user"]["id"],
                        )

    def _command_ready(self, room_id, user):
        """Must be sent to begin a conversation."""

        # the user has sent /ready repetitively
        if self.sessions[room_id].players[0]["status"] in {"ready", "done"}:
            self.send_message_to_user(
                "You have already typed 'ready'.", room_id, user["id"]
            )
            return

        self.sessions[room_id].players[0]["status"] = "ready"
        self.send_message_to_user("Woo-Hoo! The game will begin now.", room_id)
        self.start_round(room_id)

    def start_round(self, room_id):
        if not self.sessions[room_id].words:
            self.close_room(room_id)

        # send the instructions for the round
        round_n = (WORDS_PER_ROOM - len(self.sessions[room_id].words)) + 1

        # try to log the round number
        self.log_event("round", {"number": round_n}, room_id)

        self.send_message_to_user(f"Let's start round {round_n}", room_id)
        self.send_message_to_user(
            "Make your guess",
            room_id,
            self.sessions[room_id].guesser,
        )

        self.sessions[room_id].word_to_guess = self.sessions[room_id].words[0][
            "target_word"
        ]


    def send_instructions(self, room_id):
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr",
            json={"text": f"{GUESSER_PROMPT}", "receiver_id": self.sessions[room_id].guesser},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction: {response.status_code}")
            response.raise_for_status()


    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()

        # remove user from room
        if room_id in self.sessions:
            for usr in self.sessions[room_id].players:
                response = requests.get(
                    f"{self.uri}/users/{usr['id']}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(f"Could not get user: {response.status_code}")
                    response.raise_for_status()
                etag = response.headers["ETag"]

                response = requests.delete(
                    f"{self.uri}/users/{usr['id']}/rooms/{room_id}",
                    headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(
                        f"Could not remove user from task room: {response.status_code}"
                    )
                    response.raise_for_status()
                logging.debug("Removing user from task room was successful.")

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


    def close_room(self, room_id):
        self.room_to_read_only(room_id)

        # remove any task room specific objects
        self.sessions.clear_session(room_id)

if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = WordleBot.create_argparser()


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

    args = parser.parse_args()
    logging.debug(args)

    # create bot instance
    bot = WordleBot(args.token, args.user, args.task, args.host, args.port)

    bot.post_init(args.waiting_room)

    # connect to chat server
    bot.run()
