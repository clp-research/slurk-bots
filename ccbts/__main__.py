import logging
import os
import random
from threading import Timer
from time import sleep

import requests
import numpy as np

from templates import TaskBot
from wizardinterface import WizardInterface
from .config import *


class RoomTimers:
    """A number of timed events during the game.

    :param alone_in_room: Closes a room if one player is alone in
        the room for longer than 5 minutes

    :param round_timer: After 15 minutes the image will change
        and players get no points

    """
    def __init__(self):
        self.left_room = dict()


class CcbtsBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.players_per_room = dict()
        self.images_per_room = dict()
        self.robot_interfaces = dict()
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
                self.images_per_room[room_id] = random.choice(IMGS)

                # create robot interface for this room
                self.robot_interfaces[room_id] = WizardInterface()

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

                # create new timer for this room
                self.timers_per_room[room_id] = RoomTimers()

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
                        "text", {
                            "message": COLOR_MESSAGE.format(
                                message=line, color=STANDARD_COLOR
                            ),
                            "room": room_id,
                            "html": True
                        }
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
                            "message": COLOR_MESSAGE.format(
                                message=f"{curr_usr['name']} has joined the game.",
                                color=STANDARD_COLOR
                            ),
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                            "html": True
                        },
                    )

                    # greet the player with his name
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                message=f"Welcome {curr_usr['name']}!",
                                color=STANDARD_COLOR
                            ),
                            "room": room_id,
                            "receiver_id": curr_usr['name'],
                            "html": True
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

                    # cancel timer
                    logging.debug(f"Cancelling Timer: left room for user {curr_usr['name']}")

                    timer = self.timers_per_room[room_id].left_room.get(curr_usr["id"])
                    if timer is not None:
                        timer.cancel()

                elif data["type"] == "leave":
                    # send a message to the user that was left alone
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                message=(
                                    f"{curr_usr['name']} has left the game. "
                                    "Please wait a bit, your partner may rejoin.",
                                ),
                                color=STANDARD_COLOR
                            ),
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                            "html": True
                        },
                    )

                    # start timer since user left the room
                    logging.debug(f"Starting Timer: left room for user {curr_usr['name']}")
                    self.timers_per_room[room_id].left_room[curr_usr["id"]] = Timer(
                        TIME_LEFT*60,
                        self.close_game, args=[room_id]
                    )
                    self.timers_per_room[room_id].left_room[curr_usr["id"]].start()

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

            if room_id in self.images_per_room:
                # set wizard
                if data["command"] == "set_role_wizard":
                    self.set_wizard_role(room_id, user_id)

                # reset roles
                elif data["command"] == "reset_roles":
                    self.reset_roles(room_id)

                elif data["command"] == "game_over":
                    curr_usr, other_usr = self.players_per_room[room_id]
                    if curr_usr["id"] != user_id:
                        curr_usr, other_usr = other_usr, curr_usr
                    
                    if curr_usr["role"] == "player":
                        self.close_game(room_id)
                    else:
                        self.sio.emit(
                        "text",
                            {
                                "message": COLOR_MESSAGE.format(
                                    message="You're not allowed to do that",
                                    color=WARNING_COLOR
                                ),
                                "room": room_id,
                                "receiver_id": user_id,
                                "html": True
                            },
                        )

                elif data["command"] == "show_me":
                    self.set_boards(room_id)

                elif (data["command"].startswith("pick") or data["command"].startswith("place")):
                    curr_usr, other_usr = self.players_per_room[room_id]
                    if curr_usr["id"] != user_id:
                        curr_usr, other_usr = other_usr, curr_usr
                    
                    if curr_usr["role"] == "wizard":
                        interface = self.robot_interfaces[room_id]
                        try:
                            # execute command
                            interface.play(data["command"])

                            # inform users a command was executed
                            action = "picked from"
                            if data["command"].startswith("place"):
                                action = "placed on"
                            self.sio.emit(
                                "text",
                                    {
                                        "message": COLOR_MESSAGE.format(
                                            message=f"An object was {action} a board",
                                            color=STANDARD_COLOR
                                        ),
                                        "room": room_id,
                                        "html": True
                                    },
                                )

                        except (KeyError, TypeError, OverflowError) as error:
                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        color=WARNING_COLOR, message=str(error)
                                    ),
                                    "room": room_id,
                                    "html": True
                                },
                            )
                    else:
                        self.sio.emit(
                            "text",
                            {
                                "message": COLOR_MESSAGE.format(
                                    message="You're not allowed to do that",
                                    color=WARNING_COLOR
                                ),
                                "room": room_id,
                                "receiver_id": user_id,
                                "html": True
                            },
                        )


                else:
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                message="Sorry, but I do not understand this command.",
                                color=STANDARD_COLOR
                            ),
                            "room": room_id,
                            "receiver_id": user_id,
                            "html": True
                        },
                    )

    def set_wizard_role(self, room_id, user_id):
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
                    "message": COLOR_MESSAGE.format(
                        message="Roles have already be assigned, please reset roles first",
                        color=WARNING_COLOR
                    ),
                    "room": room_id,
                    "receiver_id": user_id,
                    "html": True
                },
            )

    def reset_roles(self, room_id):
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    message="Roles have been resetted, please wait for new roles to be assigned",
                    color=STANDARD_COLOR
                ),
                "room": room_id,
                "html": True
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

    def set_image(self, room_id, user):
        # set image
        # imagepath = self.images_per_room[room_id]
        # with imagepath.open("rb") as infile:
        #     img_byte = infile.read()

        # image = f"data:image/jpg;base64, {base64.b64encode(img_byte).decode('utf-8')}"

        image = self.images_per_room[room_id]

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/current-image",
            json={"attribute": "src", "value": image, "receiver_id": user["id"]},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not set image: {response.status_code}")
            response.raise_for_status()

    def set_boards(self, room_id):
        # get boards from the robot interface
        interface = self.robot_interfaces[room_id]
        boards = interface.get_boards()
        source_board = boards["s"].tolist()
        target_board = boards["t"].tolist()

        # set source board
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "board": source_board,
                    "name": "source",
                },
                "room": room_id
            },
        )

        # set target board
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "board": target_board,
                    "name": "target",
                },
                "room": room_id
            },
        )

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        sleep(2)
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    message="The room is closing, thanky you for plaing",
                    color=STANDARD_COLOR
                ),
                "room": room_id,
                "html": True
            },
        )
        self.room_to_read_only(room_id)

        # remove any task room specific objects
        for memory_dict in [self.images_per_room,
                            self.robot_interfaces,
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

            # remove users from room
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
