from copy import deepcopy
import logging
import os
import random
from time import sleep
from threading import Timer
import requests
import string

from templates import TaskBot
from .config import *
from .golmi_client import *
from .dataloader import Dataloader


class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()
        self.left_room = dict()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER * 60, self.function, args=[self.room_id, "timeout"]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.info("reset timer")

    def cancel(self):
        self.timer.cancel()

    def cancel_all_timers(self):
        self.timer.cancel()
        for timer in self.left_room.values():
            timer.cancel()

    def user_joined(self, user):
        timer = self.left_room.get(user)
        if timer is not None:
            self.left_room[user].cancel()

    def user_left(self, user):
        self.left_room[user] = Timer(
            LEAVE_TIMER * 60, self.function, args=[self.room_id, "user_left"]
        )
        self.left_room[user].start()


class GolmiBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.players_per_room = dict()
        self.golmi_client_per_room = dict()
        self.timers_per_room = dict()
        self.description_per_room = dict()
        self.points_per_room = dict()
        self.selected_object_per_room = dict()
        self.boards_per_room = Dataloader(BOARDS, BOARDS_PER_ROOM)
        self.register_callbacks()

    def post_init(self, waiting_room, golmi_server, golmi_password, version):
        """
        save extra variables after the __init__() method has been called
        and create the init_base_dict: a dictionary containing
        needed arguments for the init event to send to the JS frontend
        """
        self.waiting_room = waiting_room
        self.golmi_server = golmi_server
        self.golmi_password = golmi_password
        self.version = version
        self.base_init_dict = {
            "event": "init",
            "url": golmi_server,
            "password": golmi_password,
            "tracking": version != "show_gripper",
            "show_gripper": version == "show_gripper",
            "show_gripped_objects": version in {"confirm_selection", "show_gripper"},
            "warning": version != "no_feedback",
        }

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
                self.boards_per_room.get_boards(room_id)
                self.players_per_room[room_id] = list()
                self.description_per_room[room_id] = False
                self.selected_object_per_room[room_id] = False
                self.points_per_room[room_id] = STARTING_POINTS
                self.timers_per_room[room_id] = RoomTimer(
                    self.timeout_close_game, room_id
                )
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
                        f"Could not let golmi bot join room: {response.status_code}"
                    )
                    response.raise_for_status()
                logging.debug("Sending golmi bot to new room was successful.")

                self.golmi_client_per_room[room_id] = GolmiClient(
                    self.sio, self, room_id
                )
                self.golmi_client_per_room[room_id].run(
                    self.golmi_server, str(room_id), self.golmi_password
                )

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
                for line in task_greeting():
                    self.sio.emit(
                        "text",
                        {
                            "message": line.format(board_number=BOARDS_PER_ROOM),
                            "room": room_id,
                            "html": True,
                        },
                    )
                    sleep(0.5)

                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr",
                    json={"text": "Please wait for the roles to be assigned"},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    LOG.error(
                        f"Could not set task instruction title: {response.status_code}"
                    )
                    response.raise_for_status()

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

                    # cancel leave timers if any
                    self.timers_per_room[room_id].user_joined(curr_usr["id"])

                    # check if the user has a role, if so, send role command
                    role = curr_usr["role"]
                    if role is not None:
                        self.sio.emit(
                            "message_command",
                            {
                                "command": {
                                    **self.base_init_dict,
                                    "role": role,
                                    "room_id": str(room_id),
                                },
                                "room": room_id,
                                "receiver_id": data["user"]["id"],
                            },
                        )

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

                    # start a timer
                    self.timers_per_room[room_id].user_left(curr_usr["id"])

                    # if the wizard left, load the state again with no gripper
                    # once the wizard reconnects a new gripper will be created
                    if curr_usr["role"] == "wizard":
                        self.load_state(room_id, from_disconnect=True)

        @self.sio.event
        def text_message(data):
            room_id = data["room"]
            user_id = data["user"]["id"]

            # get user
            curr_usr, other_usr = self.players_per_room[room_id]
            if curr_usr["id"] != user_id:
                curr_usr, other_usr = other_usr, curr_usr

            # roles have not been assigned yet, don't do anything
            if not all([curr_usr["role"], other_usr["role"]]):
                return

            self.timers_per_room[room_id].reset()

            # we have a message from the player
            # revoke user's text privilege
            if curr_usr["role"] == "player":
                self.description_per_room[room_id] = True
                if self.version != "show_gripper":
                    self.set_message_privilege(user_id, False)

        @self.sio.event
        def mouse(data):
            room_id = data["room"]
            user_id = data["user"]["id"]

            if room_id not in self.players_per_room:
                return

            # don't react to mouse movements
            if data["type"] != "click":
                return

            self.timers_per_room[room_id].reset()

            if self.selected_object_per_room[room_id] is True:
                self.sio.emit(
                    "text",
                    {
                        "message": COLOR_MESSAGE.format(
                            color=WARNING_COLOR,
                            message=(
                                "WARNING: you already selected an object, "
                                "wait for your partner to confirm your selection"
                            ),
                        ),
                        "room": room_id,
                        "receiver_id": user_id,
                        "html": True,
                    },
                )
                return

            # no description yet, warn the user
            if self.description_per_room[room_id] is False:
                self.sio.emit(
                    "text",
                    {
                        "message": COLOR_MESSAGE.format(
                            color=WARNING_COLOR,
                            message=(
                                "WARNING: wait for your partner "
                                "to send a description first"
                            ),
                        ),
                        "room": room_id,
                        "receiver_id": user_id,
                        "html": True,
                    },
                )
                return

            curr_usr, other_usr = self.players_per_room[room_id]
            if curr_usr["id"] != user_id:
                curr_usr, other_usr = other_usr, curr_usr

            # check if player selected the correct area
            x = data["coordinates"]["x"]
            y = data["coordinates"]["y"]
            block_size = data["coordinates"]["block_size"]

            req = requests.get(
                f"{self.golmi_server}/slurk/{room_id}/{x}/{y}/{block_size}"
            )
            if req.ok is not True:
                logging.error("Could not retrieve gripped piece")

            piece = req.json()
            if piece:
                self.piece_selection(room_id, piece)

        @self.sio.event
        def command(data):
            """Parse user commands."""
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if user_id == self.user:
                return

            self.timers_per_room[room_id].reset()

            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            if room_id in self.players_per_room:
                # get users
                curr_usr, other_usr = self.players_per_room[room_id]
                if curr_usr["id"] != user_id:
                    curr_usr, other_usr = other_usr, curr_usr

                if isinstance(data["command"], dict):
                    # commands from interface
                    event = data["command"]["event"]

                    if event == "confirm_selection":
                        self.selected_object_per_room[room_id] = False

                        if self.version == "show_gripper":
                            # attach wizard's controller
                            self.sio.emit(
                                "message_command",
                                {
                                    "command": {"event": "attach_controller"},
                                    "room": room_id,
                                    "receiver_id": other_usr["id"],
                                },
                            )

                        if data["command"]["answer"] == "no":
                            # TODO: remove points?
                            self.points_per_room[room_id] += NEGATIVE_REWARD
                            self.sio.emit(
                                "text",
                                {
                                    "message": "Your partner thinks you selected the wrong piece, try again",
                                    "room": room_id,
                                    "receiver_id": other_usr["id"],
                                    "html": True,
                                },
                            )
                            self.sio.emit(
                                "text",
                                {
                                    "message": "Your partner will shortly try again",
                                    "room": room_id,
                                    "receiver_id": curr_usr["id"],
                                    "html": True,
                                },
                            )
                        else:
                            req = requests.get(
                                f"{self.golmi_server}/slurk/{room_id}/gripped"
                            )
                            if req.ok is not True:
                                logging.error("Could not retrieve gripped piece")

                            piece = req.json()
                            if piece:
                                target = self.boards_per_room[room_id][0]["state"][
                                    "targets"
                                ]
                                result = (
                                    "right" if piece.keys() == target.keys()
                                    else "wrong"
                                )
                                self.load_next_state(room_id, result)

                    # wizard sends a warning
                    if event == "warning":
                        logging.debug("emitting WARNING")

                        if self.version == "no_feedback":
                            # not available
                            return

                        # TODO: add official warning log??

                        if self.description_per_room.get(room_id) is True:
                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        color=WARNING_COLOR,
                                        message=("You sent a warning to your partner"),
                                    ),
                                    "room": room_id,
                                    "receiver_id": curr_usr["id"],
                                    "html": True,
                                },
                            )

                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        color=WARNING_COLOR,
                                        message=(
                                            "WARNING: your partner thinks that you "
                                            "are not doing the task correctly"
                                        ),
                                    ),
                                    "room": room_id,
                                    "receiver_id": other_usr["id"],
                                    "html": True,
                                },
                            )

                            # give user possibility to send another message
                            self.description_per_room[room_id] = False
                            self.set_message_privilege(other_usr["id"], True)

                            # TODO: should players lose points?
                            self.points_per_room[room_id] += NEGATIVE_REWARD

                        else:
                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        color=WARNING_COLOR,
                                        message=(
                                            "Wait for your partner fo send at least one message"
                                        ),
                                    ),
                                    "room": room_id,
                                    "receiver_id": curr_usr["id"],
                                    "html": True,
                                },
                            )

                else:
                    # commands from user
                    # set wizard
                    if data["command"] == "set_role_wizard":
                        self.set_wizard_role(room_id, user_id)

                    # reset roles
                    elif data["command"] == "reset_roles":
                        self.reset_roles(room_id)

                    else:
                        self.sio.emit(
                            "text",
                            {
                                "message": "Sorry, but I do not understand this command.",
                                "room": room_id,
                                "receiver_id": user_id,
                            },
                        )

    def piece_selection(self, room_id, piece):
        # get users
        wizard, player = self.players_per_room[room_id]
        if wizard["role"] != "wizard":
            wizard, player = player, wizard

        # get target piece
        target = self.boards_per_room[room_id][0]["state"]["targets"]
        result = "right" if piece.keys() == target.keys() else "wrong"

        # add selected piece to logs
        self.add_to_log("wizard_piece_selection", piece, room_id)

        # load next state
        if self.version not in {"confirm_selection", "show_gripper"}:
            self.load_next_state(room_id, result)
        else:
            self.selected_object_per_room[room_id] = True

            if self.version == "show_gripper":
                # detach wizard's controller
                self.sio.emit(
                    "message_command",
                    {
                        "command": {"event": "detach_controller"},
                        "room": room_id,
                        "receiver_id": wizard["id"],
                    },
                )

            self.sio.emit(
                "text",
                {
                    "message": "Your partner selected an object, is it correct? <button onclick=\"confirm_selection('yes')\">YES</button> <button onclick=\"confirm_selection('no')\">NO</button>.",
                    "room": room_id,
                    "receiver_id": player["id"],
                    "html": True,
                },
            )

    def add_to_log(self, event, data, room_id):
        response = requests.post(
            f"{self.uri}/logs",
            json={
                "event": event,
                "room_id": room_id,
                "data": data,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not post AMT token to logs: {response.status_code}")
            response.raise_for_status()

    def load_next_state(self, room_id, result):
        self.timers_per_room[room_id].reset()

        if result == "right":
            self.points_per_room[room_id] += POSITIVE_REWARD
        else:
            self.points_per_room[room_id] += NEGATIVE_REWARD

        player, wizard = self.players_per_room[room_id]
        if player["role"] != "player":
            player, wizard = wizard, player

        self.boards_per_room[room_id].pop(0)
        self.description_per_room[room_id] = False
        self.set_message_privilege(player["id"], True)

        if not self.boards_per_room[room_id]:
            # no more boards, close the room
            score = self.points_per_room[room_id]
            self.sio.emit(
                "text",
                {
                    "room": room_id,
                    "message": (
                        "That was the last one 🎉 🎉 thank you very much for your time! "
                        f"Your total score is: {score} points."
                    ),
                    "html": True,
                },
            )
            self.confirmation_code(room_id, "sucess")
            self.close_game(room_id)

        else:
            points = self.points_per_room[room_id]
            message = "Let's get you to the next board"
            if self.version != "no_feedback":
                message = (
                    f"That was the {result} piece, you currently have {points} points. "
                    f"{message}"
                )
            self.sio.emit(
                "text",
                {
                    "room": room_id,
                    "message": message,
                    "html": True,
                },
            )
            self.load_state(room_id)

    def set_message_privilege(self, user_id, value):
        """
        change user's permission to send messages
        """
        # get permission_id based on user_id
        response = requests.get(
            f"{self.uri}/users/{user_id}/permissions",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(
                f"Could not retrieve user's permission: {response.status_code}"
            )
            response.raise_for_status()

        permission_id = response.json()["id"]
        requests.patch(
            f"{self.uri}/permissions/{permission_id}",
            json={"send_message": value},
            headers={
                "If-Match": response.headers["ETag"],
                "Authorization": f"Bearer {self.token}",
            },
        )
        if not response.ok:
            logging.error(
                f"Could not change user's message permission: {response.status_code}"
            )
            response.raise_for_status()

    def set_wizard_role(self, room_id, user_id):
        self.timers_per_room[room_id].reset()

        curr_usr, other_usr = self.players_per_room[room_id]
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # users have no roles so we can assign them
        if not all([curr_usr["role"], other_usr["role"]]):
            instruction_functions = {"player": player_instr, "wizard": wizard_instr}
            for user, role in zip([curr_usr, other_usr], ["wizard", "player"]):
                user["role"] = role

                self.sio.emit(
                    "message_command",
                    {
                        "command": {
                            **self.base_init_dict,
                            "role": role,
                            "room_id": str(room_id),
                        },
                        "room": room_id,
                        "receiver_id": user["id"],
                    },
                )

                if role == "wizard":
                    self.set_message_privilege(curr_usr["id"], False)

                instr = instruction_functions.get(role)

                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr",
                    json={"text": instr(), "receiver_id": user["id"]},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    LOG.error(
                        f"Could not set task instruction title: {response.status_code}"
                    )
                    response.raise_for_status()

            sleep(0.5)
            self.load_state(room_id)

            self.sio.emit(
                "text",
                {
                    "message": "You're all set to go, have fun!",
                    "room": room_id,
                },
            )

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
        self.timers_per_room[room_id].reset()

        self.sio.emit(
            "text",
            {
                "message": "Roles have been reset, please wait for new roles to be assigned",
                "room": room_id,
            },
        )

        for user in self.players_per_room[room_id]:
            self.set_message_privilege(user["id"], True)
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

    def load_state(self, room_id, from_disconnect=False):
        """load the current board on the golmi server"""
        # load and log state
        board = deepcopy(self.boards_per_room[room_id][0])

        # add gripper if not present
        if self.version == "show_gripper":
            if from_disconnect is False:
                # copy over to new board the gripper of the previous one
                # so that the controller can still operate it
                if not board["state"]["grippers"]:
                    req = requests.get(f"{self.golmi_server}/slurk/{room_id}/state")
                    if req.ok is not True:
                        logging.error("Could not retrieve state")

                    state = req.json()
                    grippers = state["grippers"]
                    gr_id = list(grippers.keys())[0]

                    grippers[gr_id]["gripped"] = None
                    grippers[gr_id]["x"] = 12.5
                    grippers[gr_id]["y"] = 12.5

                    board["state"]["grippers"] = grippers

        # no need to log if the board is loaded again
        # after the wizard disconnected
        if from_disconnect is False:
            self.add_to_log("board_log", {"board": board}, room_id)

        self.golmi_client_per_room[room_id].load_config(board["config"])
        self.golmi_client_per_room[room_id].load_state(board["state"])

    def confirmation_code(self, room_id, status):
        """Generate AMT token that will be sent to each player."""
        amt_token = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        points = self.points_per_room[room_id]
        # post AMT token to logs
        self.add_to_log(
            "confirmation_log",
            {"status_txt": status, "amt_token": amt_token, "points": points},
            room_id,
        )

        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR,
                    message=(
                        "Please enter the following token into the field on "
                        "the HIT webpage, and close this browser window. "
                        f"Your token: {amt_token}"
                    ),
                ),
                "room": room_id,
                "html": True,
            },
        )

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        sleep(2)
        self.sio.emit(
            "text",
            {"message": "The room is closing, see you next time 👋", "room": room_id},
        )
        self.room_to_read_only(room_id)

        # cancel all timers
        self.timers_per_room[room_id].cancel_all_timers()

        # disconnect from golmi server
        self.golmi_client_per_room[room_id].disconnect()

        # remove any task room specific objects
        memory_dicts = [
            self.golmi_client_per_room,
            self.players_per_room,
            self.timers_per_room,
            self.description_per_room,
            self.boards_per_room,
            self.points_per_room,
            self.selected_object_per_room,
        ]
        for memory_dict in memory_dicts:
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

    def timeout_close_game(self, room_id, status):
        self.confirmation_code(room_id, status)
        self.close_game(room_id)


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

    # versions:
    #  no_feedback: player can only send one message, does not know if the wizard selected the correct object
    #  feedback: player can only send one message, is informed if the wizard selected the correct object
    #  confirm_selection: player needs to confirm the wizard's selection
    #  show_gripper: player can see the mouse movements of the wizard
    if "BOT_VERSION" in os.environ:
        bot_version = {"default": os.environ["BOT_VERSION"]}
    else:
        bot_version = {"required": True}
    parser.add_argument(
        "--bot_version",
        type=str,
        help="version of the golmi bot",
        **bot_version,
    )

    args = parser.parse_args()

    # create bot instance
    bot = GolmiBot(args.token, args.user, args.task, args.host, args.port)
    bot.post_init(
        args.waiting_room, args.golmi_server, args.golmi_password, args.bot_version
    )
    # connect to chat server
    bot.run()
