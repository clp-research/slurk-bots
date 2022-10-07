import logging
import os
from time import sleep
from pathlib import Path

import requests

from templates import TaskBot

from .config import *


class CcbtsBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.players_per_room = dict()
        self.images_per_room = dict()
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
                for usr in data['users']:
                    self.received_waiting_token.discard(usr['id'])

                # create image items for this room
                logging.debug("Create data for the new task room...")
                self.images_per_room[room_id] = IMGS

                self.players_per_room[room_id] = []
                for usr in data["users"]:
                    self.players_per_room[room_id].append(
                        {**usr, "role": 0, "status": "joined"}
                    )

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if not response.ok:
                    logging.error(f"Could not let wordle bot join room: {response.status_code}")
                    response.raise_for_status()
                logging.debug("Sending wordle bot to new room was successful.")


        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            if room_id in self.images_per_room:
                # read out task greeting
                for line in TASK_GREETING:
                    self.sio.emit(
                        "text",
                        {"message": line,
                         "room": room_id,
                         "html": True}
                    )
                    sleep(.5)
                # ask players to send \ready
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr_title",
                    json={"text": line},
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if not response.ok:
                    logging.error(f"Could not set task instruction title: {response.status_code}")
                    response.raise_for_status()

        @self.sio.event
        def status(data):
            """Triggered if a user enters or leaves a room."""
            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{data['user']['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if not task.ok:
                logging.error(f"Could not set task instruction title: {task.status_code}")
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
                        {"message": f"{curr_usr['name']} has joined the game. ",
                         "room": room_id,
                         "receiver_id": other_usr["id"]}
                    )

                elif data["type"] == "leave":
                    # send a message to the user that was left alone
                    self.sio.emit(
                        "text",
                        {"message": f"{curr_usr['name']} has left the game. "
                                    "Please wait a bit, your partner may rejoin.",
                         "room": room_id,
                         "receiver_id": other_usr["id"]}
                    )

        @self.sio.event
        def command(data):
            """Parse user commands."""
            logging.debug(f"Received a command from {data['user']['name']}: {data['command']}")

            room_id = data["room"]
            user_id = data["user"]["id"]

            logging.debug(data)
            logging.debug(self.players_per_room)

            if room_id in self.images_per_room:
                if data["command"] == "set_role_wizard":

                    curr_usr, other_usr = self.players_per_room[room_id]
                    if curr_usr["id"] != data["user"]["id"]:
                        curr_usr, other_usr = other_usr, curr_usr

                    self.sio.emit(
                         "message_command",
                         {"command": "role_wizard",
                          "room": room_id,
                          "receiver_id": curr_usr["id"]}
                    )        

                    self.sio.emit(
                         "message_command",
                         {"command": "role_player",
                          "room": room_id,
                          "receiver_id": other_usr["id"]}
                    )         
                else:
                    self.sio.emit(
                        "text",
                        {"message": "Sorry, but I do not understand this command.",
                         "room": room_id,
                         "receiver_id": user_id}
                    )


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
        "--waiting_room", type=int, help="room where users await their partner", **waiting_room
    )
    args = parser.parse_args()

    # create bot instance
    ccbts_bot = CcbtsBot(args.token, args.user, args.task, args.host, args.port)
    ccbts_bot.waiting_room = args.waiting_room
    # connect to chat server
    ccbts_bot.run()
