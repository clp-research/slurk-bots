# -*- coding: utf-8 -*-

# University of Potsdam
"""Chatbot agent that both administers an interaction and acts as the
interacting player.
"""

import logging
import os
import random
import string
from time import sleep

import requests

from lib.config import *
from templates import TaskBot


LOG = logging.getLogger(__name__)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# TODO: make this class abstract to implement API access
class Chatbot(TaskBot):
    """A bot that talks to a user by calling some chatbot API"""
    """The ID of the room where users for this task are waiting."""
    waiting_room = None

    def __init__(self, *args, **kwargs):
        """This bot interacts with 1 human player by calling an API to carry
        out the actual interaction

        :param players_per_room: Each room is mapped to a list of
            users. Each user is represented as a dict with the
            keys 'name', 'id', 'msg_n' and 'status'.
        :type players_per_room: dict
        """
        super().__init__(*args, **kwargs)
        self.players_per_room = dict()

    def register_callbacks(self):

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            # read out task greeting
            # ask players to send /ready
            sleep(1)  # avoiding namespace errors
            for line in TASK_GREETING:
                self.sio.emit(
                    "text",
                    {
                        "message": line,
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
            self.request_feedback(task, "set task instruction title")
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

        @self.sio.event
        def text_message(data):
            """Triggered once a text message is sent (no leading /).

            Count user text messages.
            If encountering something that looks like a command
            then pass it on to be parsed as such.
            """
            LOG.debug(f"Received a message from {data['user']['name']}.")

            room_id = data["room"]
            user_id = data["user"]["id"]

            # filter irrelevant messages
            if user_id == self.user:
                return

            # if the message is part of the main discussion count it
            for usr in self.players_per_room[room_id]:
                if usr["id"] == user_id and usr["status"] == "ready":
                    usr["msg_n"] += 1
                elif usr["id"] == user_id and usr["status"] == "done":
                    return
                elif usr["id"] == user_id:
                    self.sio.emit(
                        "text",
                        {
                            "message": "*You haven't typed /ready yet.*",
                            "receiver_id": user_id,
                            "html": True,
                            "room": room_id,
                        },
                    )
                    return

            # feed message to language model and get response
            answer = self._interaction_loop(data["message"])
            self.sio.emit(
                "text",
                {
                    "message": answer,
                    "receiver_id": user_id,
                    "html": True,
                    "room": room_id,
                },
            )

        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]

            if data["command"].startswith("ready"):
                self._command_ready(room_id, user_id)
            elif data["command"].startswith("stop"):
                self._command_stop(room_id, user_id)
            else:
                self.sio.emit(
                    "text",
                    {
                        "message": "Sorry, but I do not understand this command.",
                        "room": room_id,
                        "receiver_id": user_id,
                    },
                )

    def join_task_room(self):
        """Let the bot join an assigned task room."""

        def join(data):
            if self.task_id is None or data["task"] != self.task_id:
                return

            room_id = data["room"]

            LOG.debug(f"A new task room was created with id: {data['task']}")
            LOG.debug(f"This bot is looking for task id: {self.task_id}")

            self.move_divider(room_id, 70, 30)

            self.players_per_room[room_id] = []
            for usr in data["users"]:
                self.players_per_room[room_id].append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )

            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, f"let {self.__class__.__name__} join room")

        return join

    def _command_stop(self, room_id, user_id):
        """Stopping criterion. End conversation"""
        # create token and send it to user
        users = self.players_per_room[room_id]
        curr_usr = users[0]
        curr_usr["status"] = "done"
        self.confirmation_code(room_id, "done", receiver_id=user_id)
        self.close_game(room_id)

    def _command_ready(self, room_id, user_id):
        """Must be sent to begin a conversation."""
        users = self.players_per_room[room_id]
        curr_usr = users[0]

        if curr_usr["id"] != user_id:
            LOG.warning("Something is wrong here.")
            return

        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            sleep(0.5)
            self.sio.emit(
                "text",
                {
                    "message": "You have already typed /ready.",
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                },
            )
            return
        curr_usr["status"] = "ready"

        # a first ready command was sent
        sleep(0.5)
        # give the user feedback that his command arrived
        self.sio.emit(
            "text",
            {
                "message": "Okay, let's begin!",
                "receiver_id": curr_usr["id"],
                "room": room_id,
            },
        )

    def _interaction_loop(self, message):
        """

        :param message: The user message will be given as input to the external
            LM via an API that then provides a response.
        :type message: str
        :return: answer(str): the answer to give to the user. Can be formatted.
        """
        return "cLLM says **NO**."

    def confirmation_code(self, room_id, status, receiver_id=None):
        """Generate a code that will be sent to each player."""
        kwargs = dict()
        # either only for one user or for both
        if receiver_id is not None:
            kwargs["receiver_id"] = receiver_id

        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # post code to logs
        response = requests.post(
            f"{self.uri}/logs",
            json={
                "event": "confirmation_log",
                "room_id": room_id,
                "data": {"status_txt": status, "code": code},
                **kwargs,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, f"post code to logs")

        self.sio.emit(
            "text",
            {
                "message": "Please enter the following token into the field on "
                "the HIT webpage, and close this browser window. ",
                "room": room_id,
                **kwargs,
            },
        )
        self.sio.emit(
            "text",
            {
                "message": f"Here is your token: {code}",
                "room": room_id,
                **kwargs
            },
        )
        return code

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        self.sio.emit(
            "text",
            {
                "message": "You will be moved out of this room "
                f"in {TIME_CLOSE*2*60}-{TIME_CLOSE*3*60}s.",
                "room": room_id,
            },
        )
        sleep(2)
        self.sio.emit(
            "text",
            {
                "message": "Make sure to save your token before that.",
                "room": room_id
            },
        )
        sleep(TIME_CLOSE*2*60)
        self.room_to_read_only(room_id)

        # remove users from room
        for usr in self.players_per_room[room_id]:
            response = requests.get(
                f"{self.uri}/users/{usr['id']}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "get user")
            etag = response.headers["ETag"]

            response = requests.delete(
                f"{self.uri}/users/{usr['id']}/rooms/{room_id}",
                headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "remove user from task room")

        # remove any task room specific objects
        self.players_per_room.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set room to read_only")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "inform user that room is read_only")
