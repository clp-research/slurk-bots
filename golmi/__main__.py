import base64
import logging
import os
import random
from time import sleep

import requests

from templates import TaskBot
from .config import *
from .golmi_client import *


def set_text_message(value):
    """
    change user's permission to send messages
    """
    response = requests.get(f"{uri}/permissions/4", headers={"Authorization": f"Bearer {token}"})
    requests.patch(
        f"{uri}/permissions/4",
        json={"send_message":value},
        headers={"If-Match": response.headers["ETag"], "Authorization": f"Bearer {token}"}
    )


class GolmiBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.players_per_room = dict()
        self.golmi_client_per_room = dict()
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

                # self.golmi_client_per_room[room_id] = GolmiClient(
                #     "http://localhost:5001", self.sio, room_id
                # )
                # self.golmi_client_per_room[room_id].run(AUTH)
                # self.golmi_client_per_room[room_id].random_init({"width": 30, "height": 30, "move_step": 0.5, "prevent_overlap": True})

                


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
            elif room_id in self.players_per_room:
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
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not prcess commands from itself
            if user_id == self.user:
                return

            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            if room_id in self.players_per_room:
                # set wizard
                if data["command"] == "set_role_wizard":
                    self.set_wizard_role(room_id, user_id)

                elif data["command"] == "start":
                    self.sio.emit(
                        "message_command",
                        {
                            "command": {
                                "url": "http://localhost:5001",
                                "room_id": room_id
                            },
                            "room": room_id,
                        },
                    )

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
                            "message": "You're not allowed to do that",
                            "room": room_id,
                            "receiver_id": user_id,
                        },
                    )

                elif (data["command"].startswith("pick") or data["command"].startswith("place")):
                    curr_usr, other_usr = self.players_per_room[room_id]
                    if curr_usr["id"] != user_id:
                        curr_usr, other_usr = other_usr, curr_usr
                    
                    if curr_usr["role"] == "wizard":
                        interface = self.robot_interfaces[room_id]
                        try:
                            interface.execute(data["command"])
                        except (KeyError, TypeError, OverflowError) as error:
                            self.sio.emit(
                                "text",
                                {
                                    "message": str(error),
                                    "room": room_id,
                                    "receiver_id": user_id,
                                }, 
                            )
                        self.set_boards(room_id)
                    else:
                        self.sio.emit(
                        "text",
                        {
                            "message": "You're not allowed to do that",
                            "room": room_id,
                            "receiver_id": user_id,
                        },
                    )


                else:
                    self.sio.emit(
                        "text",
                        {
                            "message": "Sorry, but I do not understand this command.",
                            "room": room_id,
                            "receiver_id": user_id,
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
                    "message": "Roles have already be assigned, please reset roles first",
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )

    def reset_roles(self, room_id):
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

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        sleep(2)
        self.sio.emit(
            "text",
            {"message": "The room is closing, thanky you for plaing", "room": room_id},
        )
        self.room_to_read_only(room_id)


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
    parser = GolmiBot.create_argparser()
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
    bot = GolmiBot(args.token, args.user, args.task, args.host, args.port)
    bot.waiting_room = args.waiting_room
    # connect to chat server
    bot.run()
