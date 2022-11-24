import logging
import os
import json
from time import sleep
from threading import Timer

import requests
from templates import TaskBot
from .config import *
from .golmi_client import *
from .dataloader import Dataloader


class RoomTimer:
    def __init__(self, time, function, room_id):
        self.function = function
        self.time = time
        self.room_id = room_id
        self.start_timer()

    def start_timer(self):
        self.timer = Timer(self.time*60, self.function, args=[self.room_id])
        self.timer.start()

    def snooze(self):
        self.timer.cancel()
        self.start_timer()
        logging.debug("snooze")

    def cancel(self):
        self.timer.cancel()


class GolmiEval(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.players_per_room = dict()
        self.golmi_client_per_room = dict()
        self.boards_per_room = Dataloader(BOARDS, BOARDS_PER_ROOM)
        self.can_load_next_state = dict()
        self.timers_per_room = dict()
        self.register_callbacks()

    def register_callbacks(self):
        @self.sio.event
        def new_task_room(data):
            """Triggered after a new task room is created.

            An example scenario would be that the concierge
            bot emitted a room_created event once enough
            users for a task have entered the waiting room.
            """
            room_id = data["room"]
            task_id = data["task"]

            logging.debug(f"A new task room was created with id: {data['task']}")
            logging.debug(f"This bot is looking for task id: {self.task_id}")

            if task_id is not None and task_id == self.task_id:
                for usr in data["users"]:
                    self.received_waiting_token.discard(usr["id"])

                # create image items for this room
                logging.debug("Create data for the new task room...")

                self.boards_per_room.get_boards(room_id)
                self.can_load_next_state[room_id] = False
                self.players_per_room[room_id] = []
                self.timers_per_room[room_id] = RoomTimer(TIMEOUT_TIMER, self.close_game, room_id)
                for usr in data["users"]:
                    self.players_per_room[room_id].append(
                        {**usr, "role": None, "status": "joined"}
                    )

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(
                        f"Could not let wordle bot join room: {response.status_code}"
                    )
                    response.raise_for_status()
                logging.debug("Sending wordle bot to new room was successful.")

                self.golmi_client_per_room[room_id] = GolmiClient(
                    self.golmi_server, self.sio, room_id
                )
                self.golmi_client_per_room[room_id].run(self.golmi_password)
                self.load_state(room_id)


        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            if room_id in self.players_per_room:
                # add description title
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr_title",
                    json={"text": "Please wait for the roles to be assigned"},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(
                        f"Could not set task instruction title: {response.status_code}"
                    )
                    response.raise_for_status()

                # read out task greeting
                for line in TASK_GREETING:
                    self.sio.emit(
                        "text", {
                            "message": line.format(board_number=BOARDS_PER_ROOM),
                            "room": room_id,
                            "html": True
                        }
                    )
                    sleep(0.5)
                self.sio.emit(
                        "text", {
                            "message": "Here's a little help: you can reference pieces according to this legend",
                            "room": room_id,
                            "html": True
                        }
                    )
                self.sio.emit(
                    "image",
                    {
                        "room": room_id,
                        "url": TYPES,
                        "width": 600,
                        "height": 300,
                    }
                )

        @self.sio.event
        def status(data):
            """Triggered if a user enters or leaves a room."""
            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{data['user']['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not task.ok:
                logging.error(
                    f"Could not set task instruction title: {task.status_code}"
                )
                task.raise_for_status()
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

            room_id = data["room"]

            # some joined a task room
            if room_id in self.players_per_room:
                if data["type"] == "join":
                    # connect view
                    self.sio.emit(
                        "message_command",
                        {
                            "command": {
                                "url": self.golmi_server,
                                "room_id": room_id,
                                "password": self.golmi_password
                            },
                            "room": room_id,
                            "receiver_id": data["user"]["id"]
                        },
                    )

        @self.sio.event
        def text_message(data):
            """load next state after the user enters a description"""
            if self.user == data["user"]["id"]:
                return

            room_id = data["room"]
            # user sent at least one message, he can load the next state
            self.can_load_next_state[room_id] = True
            self.timers_per_room[room_id].snooze()

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

            if room_id in self.players_per_room:
                if isinstance(data["command"], dict):
                    logging.debug(data["command"])
                    if "command" in data["command"]:
                        if data["command"]["command"] == "next":
                            if self.can_load_next_state[room_id] is False:
                                self.sio.emit(
                                    "text",
                                    {
                                        "room": room_id,
                                        "message": COLOR_MESSAGE.format(
                                            message=(
                                                "**You need to send at least one message before you can move on.** "
                                                "Remember to press enter to send your description"
                                            ),
                                            color=WARNING_COLOR
                                        ),
                                        "html": True
                                    },
                                )
                                return

                            self.boards_per_room[room_id].pop(0)
                            # no more image, close room
                            if not self.boards_per_room[room_id]:
                                self.sio.emit(
                                    "text",
                                    {
                                        "room": room_id,
                                        "message": "That was the last one, thank you very much for your help &hearts;",
                                        "html": True
                                    },
                                )
                                self.close_game(room_id)

                            else:
                                self.can_load_next_state[room_id] = False
                                self.load_state(room_id)
                                boards_left = len(self.boards_per_room[room_id])
                                self.sio.emit(
                                    "text",
                                    {
                                        "room": room_id,
                                        "message": f"Let's get you on the next board, still {boards_left} to go",
                                    },
                                )

                    # else:
                    #     x, y = self.__translate(
                    #         data["command"]["offset_x"],
                    #         data["command"]["offset_y"],
                    #         data["command"]["block_size"]
                    #     )

                    #     logging.debug(f"{x}\t{y}")

                    #     if x > 5:
                    #         on_target = True
                    #     else:
                    #         on_target = False

                    #     self.sio.emit(
                    #         "message_command",
                    #         {
                    #             "command": {
                    #                 "on_target": on_target,
                    #             },
                    #             "room": room_id,
                    #             "receiver_id": data["user"]["id"]
                    #         },
                    #     )


                else:
                    self.sio.emit(
                        "text",
                        {
                            "message": "Sorry, but I do not understand this command.",
                            "room": room_id,
                            "receiver_id": user_id,
                        },
                    )

    @staticmethod
    def __translate(x, y, granularity):
        return x // granularity, y // granularity

    def load_state(self, room_id):
        """load the current board on the golmi server"""
        board = self.boards_per_room[room_id][0]

        # send a message to self to log config and board?
        self.sio.emit(
            "text",
            {
                "message": json.dumps(board),
                "room": room_id,
                "receiver_id": self.user,
            },
        )

        self.golmi_client_per_room[room_id].load_config(board["config"])
        self.golmi_client_per_room[room_id].load_state(board["state"])

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        sleep(2)
        self.sio.emit(
            "text",
            {"message": "The room is closing, thanky you for plaing", "room": room_id},
        )
        self.room_to_read_only(room_id)

        # disconnect golmi client
        golmi_client = self.golmi_client_per_room[room_id]
        golmi_client.disconnect()

        for memory_dict in [self.players_per_room,
                            self.golmi_client_per_room,
                            self.boards_per_room,
                            self.timers_per_room]:
            if room_id in memory_dict:
                memory_dict.pop(room_id)


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
        if room_id in self.players_per_room:
            for usr in self.players_per_room[room_id]:
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

            self.players_per_room.pop(room_id)


if __name__ == "__main__":
    # set up loggingging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = GolmiEval.create_argparser()
    if "GOLMI_SERVER" in os.environ:
       golmi_server = {"default": os.environ["GOLMI_SERVER"]}
    else:
        golmi_server = {"required": True}

    if "GOLMI_PASSWORD" in os.environ:
       golmi_password = {"default": os.environ["GOLMI_PASSWORD"]}
    else:
        golmi_password = {"required": True}


    parser.add_argument(
        "--golmi-server",
        type=str,
        help="ip address to the golmi server",
        **golmi_server,
    )
    parser.add_argument(
        "--golmi-password",
        type=str,
        help="password to connect to the golmi server",
        **golmi_password,
    )
    args = parser.parse_args()
    logging.debug(args)
    # create bot instance
    bot = GolmiEval(args.token, args.user, args.task, args.host, args.port)
    bot.golmi_server = args.golmi_server
    bot.golmi_password = args.golmi_password
    # connect to chat server
    bot.run()
