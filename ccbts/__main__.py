import base64
import logging
import os
import random
from time import sleep

import requests

from templates import TaskBot
from executor import Executor
from .config import *


class CcbtsBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.players_per_room = dict()
        self.images_per_room = dict()
        self.executors = dict()
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
                self.images_per_room[room_id] = random.choice(IMGS)

                # create executor for this room
                self.executors[room_id] = Executor()

                self.players_per_room[room_id] = []
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

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            if room_id in self.images_per_room:
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
                        "text", {"message": line, "room": room_id, "html": True}
                    )
                    sleep(0.5)

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
            # someone joined waiting room
            if room_id == self.waiting_room:
                if data["type"] == "join":
                    logging.debug("Waiting Timer restarted.")

            # some joined a task room
            elif room_id in self.images_per_room:
                curr_usr, other_usr = self.players_per_room[room_id]
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr

                if data["type"] == "join":
                    # inform game partner about the rejoin event
                    self.sio.emit(
                        "text",
                        {
                            "message": f"{curr_usr['name']} has joined the game. ",
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                        },
                    )

                    # check if the user has a role, if so, send role command
                    role = curr_usr["role"]
                    if role is not None:
                        self.sio.emit(
                            "message_command",
                            {
                                "command": {
                                    "role": role,
                                    "instruction": INSTRUCTIONS[role],
                                },
                                "room": room_id,
                                "receiver_id": curr_usr["id"],
                            },
                        )

                        # send board again
                        self.set_boards(room_id)

                        if role == "player":
                            self.set_image(room_id, curr_usr)

                elif data["type"] == "leave":
                    # send a message to the user that was left alone
                    self.sio.emit(
                        "text",
                        {
                            "message": f"{curr_usr['name']} has left the game. "
                            "Please wait a bit, your partner may rejoin.",
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                        },
                    )

        @self.sio.event
        def command(data):
            """Parse user commands."""
            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]

            if room_id in self.images_per_room:

                # set wizard
                if data["command"] == "set_role_wizard":
                    curr_usr, other_usr = self.players_per_room[room_id]
                    if curr_usr["id"] != user_id:
                        curr_usr, other_usr = other_usr, curr_usr

                    # users have no roles so we can assign them
                    if curr_usr["role"] is None and other_usr["role"] is None:
                        for role, user in zip(
                            ["wizard", "player"], [curr_usr, other_usr]
                        ):
                            user["role"] = role
                            self.sio.emit(
                                "message_command",
                                {
                                    "command": {
                                        "role": role,
                                        "instruction": INSTRUCTIONS[role],
                                    },
                                    "room": room_id,
                                    "receiver_id": user["id"],
                                },
                            )

                        self.set_image(room_id, other_usr)
                        self.set_boards(room_id)

                    else:
                        self.sio.emit(
                            "text",
                            {
                                "message": "Roles have already be assigned, please reset roles first",
                                "room": room_id,
                                "receiver_id": user_id,
                            },
                        )

                # reset roles
                elif data["command"] == "reset_roles":
                    self.sio.emit(
                        "text",
                        {
                            "message": "Roles have been resetted, please wait for new roles to be assigned",
                            "room": room_id,
                        },
                    )

                    for user in self.players_per_room[room_id]:
                        user["role"] = None
                        self.sio.emit(
                            "message_command",
                            {
                                "command": {
                                    "role": "reset",
                                    "instruction": "",
                                },
                                "room": room_id,
                                "receiver_id": user["id"],
                            },
                        )

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

                # TODO: maybe add checks for executor commands?
                elif isinstance(data["command"], str):
                    executor = self.executors[room_id]
                    executor.execute(data["command"])
                    self.set_boards(room_id)

                else:
                    self.sio.emit(
                        "text",
                        {
                            "message": "Sorry, but I do not understand this command.",
                            "room": room_id,
                            "receiver_id": user_id,
                        },
                    )

    def set_image(self, room_id, user):
        # set image
        imagepath = self.images_per_room[room_id]
        with imagepath.open("rb") as infile:
            img_byte = infile.read()

        image = f"data:image/jpg;base64, {base64.b64encode(img_byte).decode('utf-8')}"

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/current-image",
            json={"attribute": "src", "value": image, "receiver_id": user["id"]},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not set image: {response.status_code}")
            response.raise_for_status()

    def set_boards(self, room_id):
        # set boards
        executor = self.executors[room_id]
        source_board, target_board = executor.get_slurk_boards()
        for user in self.players_per_room[room_id]:
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "board": source_board,
                        "name": "source",
                    },
                    "room": room_id,
                    "receiver_id": user["id"],
                },
            )

            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "board": target_board,
                        "name": "target",
                    },
                    "room": room_id,
                    "receiver_id": user["id"],
                },
            )

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        sleep(2)
        self.sio.emit(
            "text",
            {"message": "The room is closing, thanky you for plaing", "room": room_id},
        )
        self.room_to_read_only(room_id)

        # remove any task room specific objects
        self.images_per_room.pop(room_id)
        self.executors.pop(room_id)

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

        # remove users from room
        if room_id in self.players_per_room:
            self.players_per_room.pop(room_id)


if __name__ == "__main__":
    # set up loggingging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = CcbtsBot.create_argparser()
    if "SLURK_WAITING_ROOM" in os.environ:
        waiting_room = {"default": os.environ["SLURK_WAITING_ROOM"]}
    else:
        waiting_room = {"required": True}
    parser.add_argument(
        "--waiting_room",
        type=int,
        help="room where users await their partner",
        **waiting_room,
    )
    args = parser.parse_args()

    # create bot instance
    ccbts_bot = CcbtsBot(args.token, args.user, args.task, args.host, args.port)
    ccbts_bot.waiting_room = args.waiting_room
    # connect to chat server
    ccbts_bot.run()
