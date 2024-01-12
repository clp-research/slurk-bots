import logging
import os
import random
from time import sleep


import requests
from templates import TaskBot

import logging

from reference.config import EXPLAINER_HTML, GUESSER_HTML, EMPTY_GRID, GRIDS, GRIDS_PER_ROOM
from reference.dataloader import Dataloader
from reference.grid import GridManager


LOG = logging.getLogger(__name__)

class Session:
    def __init__(self):
        self.players = list()
        self.grids = Dataloader(GRIDS, GRIDS_PER_ROOM)
        self.grid_manager = GridManager(EMPTY_GRID)
        self.word_to_guess = None
        self.word_letters = {}
        self.guesses = 0
        self.guesser = None
        self.points = {
            "score": 0,
            "history": [{"correct": 0, "wrong": 0, "warnings": 0}],
        }

    def close(self):
        pass

    def pick_explainer(self):
        # assuming there are only 2 players
        self.explainer = random.choice(self.players)["id"]
        for player in self.players:
            if player["id"] != self.explainer:
                self.guesser = player["id"]

class SessionManager(dict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)

class ReferenceBot(TaskBot):

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
        # self.version = version


    def on_task_room_creation(self, data):
        """This function is executed as soon as 2 users are paired and a new
        task took is created
        """
        room_id = data["room"]

        task_id = data["task"]
        logging.debug(f"A new task room was created with id: {data['room']}")
        logging.debug(f"A new task room was created with task id: {data['task']}")
        logging.debug(f"This bot is looking for task id: {self.task_id}")

        # self.log_event("bot_version_log", {"version": self.version}, room_id)

        if task_id is not None and task_id == self.task_id:
            # modify layout
            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])
            logging.debug("Create data for the new task room...")
            # create a new session for these users
            # this_session = self.sessions[room_id]

            self.move_divider(room_id, 20, 80)
            self.sessions.create_session(room_id)

            for usr in data["users"]:
                self.sessions[room_id].players.append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )

            # join the newly created room
            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )

        # 2) Choose an explainer/guesser
            self.sessions[room_id].pick_explainer()
            for user in data["users"]:
                if user["id"] == self.sessions[room_id].explainer:
                    LOG.debug(f'{user["name"]} is the explainer.')
                else:
                    LOG.debug(f'{user["name"]} is the guesser.')

            # send_instructions
            for player in self.sessions[room_id].players:
                self.send_instr(room_id, player["id"])
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
        def user_message(data):
            LOG.debug("Received a user_message.")
            LOG.debug(data)
            # it sends to itself, user id = null, receiver if = null
            self.sio.emit("text", {"message": data["message"], "room": data["room"]})

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
            """Parse user messages."""
            LOG.debug(
                f"Received a message from {data['user']['name']}: {data['message']}"
            )
            room_id = data["room"]
            user_id = data["user"]["id"]

            if user_id == self.user:
                return




        @self.sio.event
        def command(data):
            """Parse user commands."""

            # do not prcess commands from itself
            if data["user"]["id"] == self.user:
                return

            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            if isinstance(data["command"], dict):
                # commands from interface
                event = data["command"]["event"]
                if event == "confirm_ready":
                    if data["command"]["answer"] == "yes":
                        self._command_ready(data["room"], data["user"]["id"])
                    elif data["command"]["answer"] == "no":
                        self.send_message_to_user(
                            "OK, read the instructions carefully and click on <yes> once you are ready.",
                            data["room"],
                            data["user"]["id"],
                        )

    def _command_ready(self, room_id, user):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user:
            curr_usr, other_usr = other_usr, curr_usr

        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            sleep(0.5)
            self.send_message_to_user(
                "You have already  clicked 'ready'.", room_id, curr_usr["id"]
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

    def send_instr(self, room_id, user_id):
        if user_id == self.sessions[room_id].explainer:
            message = f"{EXPLAINER_HTML}"
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "mark_target_grid",
                        "message": "Target grid"
                    },
                    "room": room_id,
                    "receiver_id": user_id,
                }
            )

        else:
            message = f"{GUESSER_HTML}"

        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "send_instr",
                    "message": message
                },
                "room": room_id,
                "receiver_id": user_id,
            }
        )
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "show_grid",
                    "message": f"{EMPTY_GRID}"
                },
                "room": room_id,
                "receiver_id": user_id,
            }
        )
        sleep(1)
        # grid = "X ▢ X X X\n▢ ▢ ▢ ▢ X\nX ▢ ▢ ▢ X\nX ▢ ▢ ▢ X\nX X X X X"
        # self.change_grid(emepty_grid, grid)





    def start_round(self, room_id):
        self.send_message_to_user(f"Let's start round 1", room_id)
        grid_instance = self.sessions[room_id].grids[0]
        self.show_items(room_id, grid_instance[:3], self.sessions[room_id].explainer)
        self.show_items(room_id, grid_instance[3:6], self.sessions[room_id].guesser)

    def show_items(self, room_id, grid_instance, user_id):
        for i in range(len(grid_instance)):
            updated_grid = self.sessions[room_id].grid_manager.update_grid(grid_instance[i][1])
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": f"update_grid{i+1}",
                        "message": updated_grid
                    },
                    "room": room_id,
                    "receiver_id": user_id,
                }
            )







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

    def move_divider(self, room_id, chat_area=50, task_area=50):
        """move the central divider and resize chat and task area
        the sum of char_area and task_area must sum up to 100
        """
        if chat_area + task_area != 100:
            LOG.error("Could not resize chat and task area: invalid parameters.")
            raise ValueError("chat_area and task_area must sum up to 100")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/sidebar",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"attribute": "style", "value": f"width: {task_area}%"},
        )
        self.request_feedback(response, "resize sidebar")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/content",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"attribute": "style", "value": f"width: {chat_area}%"},
        )
        self.request_feedback(response, "resize content area")

    def room_to_read_only(self, room_id):
        """Set room to read only."""
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

    def close_room(self, room_id):
        self.room_to_read_only(room_id)

        # remove any task room specific objects
        self.sessions.clear_session(room_id)







if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = ReferenceBot.create_argparser()


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
    bot = ReferenceBot(args.token, args.user, args.task, args.host, args.port)

    bot.post_init(args.waiting_room)

    # connect to chat server
    bot.run()