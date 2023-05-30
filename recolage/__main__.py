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


class Session:
    def __init__(self):
        self.players = list()
        self.golmi_client = None
        self.timer = None
        self.boards = Dataloader(BOARDS, BOARDS_PER_ROOM)
        self.description = False
        self.selected_object = False
        self.game_over = False
        self.points = {
            "score": STARTING_POINTS,
            "history": [
                {"correct": 0, "wrong": 0, "warnings": 0}
            ]
        }

    def close(self):
        self.golmi_client.disconnect()
        self.timer.cancel_all_timers()


class SessionManager(dict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)


class RecolageBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.sessions = SessionManager()
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
        def start_typing(data):
            if data["user"]["id"] == self.user:
                return

            for room_id, session in self.sessions.items():
                players_id = {player["id"] for player in session.players}
                
                if data["user"]["id"] in players_id:
                    self.log_event("start_typing", data, room_id)
                    return

        @self.sio.event
        def stop_typing(data):
            if data["user"]["id"] == self.user:
                return
            
            for room_id, session in self.sessions.items():
                players_id = {player["id"] for player in session.players}
                
                if data["user"]["id"] in players_id:
                    self.log_event("stop_typing", data, room_id)
                    return

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
                # reduce height of sidebar
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/sidebar",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"attribute": "style", "value": f"height: 90%"}
                )

                for usr in data["users"]:
                    self.received_waiting_token.discard(usr["id"])

                # create session for these users
                self.sessions.create_session(room_id)
                timer = RoomTimer(self.timeout_close_game, room_id)
                self.sessions[room_id].timer = timer

                for usr in data["users"]:
                    self.sessions[room_id].players.append(
                        {**usr, "role": None, "status": "joined"}
                    )

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "letting task bot join room")
                logging.debug("Sending golmi bot to new room was successful.")

                client = GolmiClient(self.sio, self, room_id)
                client.run(self.golmi_server, str(room_id), self.golmi_password)
                self.sessions[room_id].golmi_client = client

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            if room_id in self.sessions:
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

                # if self.version != "no_feedback":
                #     self.update_title_points(room_id)

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
            elif room_id in self.sessions:
                curr_usr, other_usr = self.sessions[room_id].players
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
                    self.sessions[room_id].timer.user_joined(curr_usr["id"])

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
                    else:
                        sleep(0.5)
                        #start demo
                        self.sio.emit(
                            "message_command",
                            {
                                "command": {
                                    "url": self.golmi_server,
                                    "event": "demo",
                                    "password": self.golmi_password,
                                    "room": f"{room_id}_demo"
                                },
                                "room": room_id,
                            },
                        )

                elif data["type"] == "leave":
                    # send a message to the user that was left alone
                    if room_id in self.sessions:
                        if self.sessions[room_id].game_over is False:
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
                            self.sessions[room_id].timer.user_left(curr_usr["id"])

                            # if the wizard left, load the state again with no gripper
                            # once the wizard reconnects a new gripper will be created
                            if curr_usr["role"] == "wizard":
                                self.load_state(room_id, from_disconnect=True)

        @self.sio.event
        def text_message(data):
            room_id = data["room"]
            user_id = data["user"]["id"]

            # ignore messages from self
            if user_id == self.user:
                return

            # get user
            curr_usr, other_usr = self.sessions[room_id].players
            if curr_usr["id"] != user_id:
                curr_usr, other_usr = other_usr, curr_usr

            # roles have not been assigned yet, don't do anything
            if not all([curr_usr["role"], other_usr["role"]]):
                return

            self.sessions[room_id].timer.reset()

            # we have a message from the player
            # revoke user's text privilege
            if curr_usr["role"] == "player":
                self.sessions[room_id].description = True
                if self.version != "show_gripper":
                    self.set_message_privilege(user_id, False)

                elif self.version == "show_gripper":
                    # attach wizard's controller
                    self.sio.emit(
                        "message_command",
                        {
                            "command": {"event": "attach_controller"},
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                        },
                    )

        @self.sio.event
        def mouse(data):
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process events from itself
            if user_id == self.user:
                return

            if room_id not in self.sessions:
                return

            # don't react to mouse movements
            if data["type"] != "click":
                return

            self.sessions[room_id].timer.reset()

            # get users
            curr_usr, other_usr = self.sessions[room_id].players
            if curr_usr["id"] != user_id:
                curr_usr, other_usr = other_usr, curr_usr

            if curr_usr["role"] == "player":
                x = data["coordinates"]["x"]
                y = data["coordinates"]["y"]
                block_size = data["coordinates"]["block_size"]

                req = requests.get(
                    f"{self.golmi_server}/slurk/{room_id}/{x}/{y}/{block_size}"
                )
                self.request_feedback(req, "retrieving gripped piece")

                piece = req.json()
                target = self.sessions[room_id].boards[0]["state"]["targets"]

                if piece.keys() == target.keys():
                    self.sio.emit(
                        "text",
                        {
                            "room": room_id,
                            "message": "That is your target",
                            "receiver_id": user_id,
                        },
                    )

            else:
                if self.sessions[room_id].selected_object is True:
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
                if self.sessions[room_id].description is False:
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

                # check if player selected the correct area
                x = data["coordinates"]["x"]
                y = data["coordinates"]["y"]
                block_size = data["coordinates"]["block_size"]

                if self.version == "confirm_selection":
                    req = requests.get(
                        f"{self.golmi_server}/slurk/grip/{room_id}/{x}/{y}/{block_size}"
                    )
                else:    
                    req = requests.get(
                        f"{self.golmi_server}/slurk/{room_id}/{x}/{y}/{block_size}"
                    )

                self.request_feedback(req, "retrieving gripped piece")

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

            self.sessions[room_id].timer.reset()

            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            if room_id in self.sessions:
                # get users
                curr_usr, other_usr = self.sessions[room_id].players
                if curr_usr["id"] != user_id:
                    curr_usr, other_usr = other_usr, curr_usr

                if isinstance(data["command"], dict):
                    # commands from interface
                    event = data["command"]["event"]

                    if event == "confirm_selection":
                        self.sessions[room_id].selected_object = False

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
                            # remove gripper
                            if self.version != "show_gripper":
                                response = requests.delete(
                                    f"{self.golmi_server}/slurk/gripper/{room_id}/mouse"
                                )
                                self.request_feedback(response, "removing mouse gripper")

                            else:
                                # reset the gripper to its original position
                                req = requests.get(f"{self.golmi_server}/slurk/{room_id}/state")
                                self.request_feedback(req, "retrieving state")

                                state = req.json()
                                grippers = state["grippers"]
                                gr_id = list(grippers.keys())[0]

                                req = requests.patch(f"{self.golmi_server}/slurk/gripper/reset/{room_id}/{gr_id}")

                            # allow the player to send a second description
                            self.sessions[room_id].description = False
                            self.set_message_privilege(user_id, True)

                            # remove points
                            self.update_reward(room_id, NEGATIVE_REWARD)
                            self.sessions[room_id].points["history"][-1]["wrong"] += 1

                            # update points in title
                            if self.version != "no_feedback":
                                self.update_title_points(room_id)

                            # inform users
                            self.sio.emit(
                                "text",
                                {
                                    "message": (
                                        "Your partner thinks you selected the wrong piece, "
                                        "wait for the new instruction and try again"),
                                    "room": room_id,
                                    "receiver_id": other_usr["id"],
                                    "html": True,
                                },
                            )
                            self.sio.emit(
                                "text",
                                {
                                    "message": "You can now send a new description to your partner",
                                    "room": room_id,
                                    "receiver_id": curr_usr["id"],
                                    "html": True,
                                },
                            )
                        else:
                            # player thinks the wizard selected the right object
                            req = requests.get(
                                f"{self.golmi_server}/slurk/{room_id}/gripped"
                            )
                            self.request_feedback(req, "retrieving gripped piece")

                            piece = req.json()
                            if piece:
                                target = self.sessions[room_id].boards[0]["state"][
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

                        if self.sessions[room_id].description is True:
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
                            self.sessions[room_id].description = False
                            self.set_message_privilege(other_usr["id"], True)

                            # remove points
                            self.update_reward(room_id, NEGATIVE_REWARD)
                            self.sessions[room_id].points["history"][-1]["warnings"] += 1

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

                    # user wants to terminate experiment
                    if event == "abort":
                        self.terminate_experiment(room_id)

                else:
                    # commands from users
                    # set wizard
                    if data["command"] == "role:wizard":
                        self.set_wizard_role(room_id, user_id)

                    elif data["command"] == "abort":
                        self.terminate_experiment(room_id)

                    else:
                        self.sio.emit(
                            "text",
                            {
                                "message": "Sorry, but I do not understand this command.",
                                "room": room_id,
                                "receiver_id": user_id,
                            },
                        )

    def update_reward(self, room_id, reward):
        score = self.sessions[room_id].points["score"]
        score += reward
        score = round(score, 2)
        self.sessions[room_id].points["score"] = max(0, score)


    def piece_selection(self, room_id, piece):
        # get users
        wizard, player = self.sessions[room_id].players
        if wizard["role"] != "wizard":
            wizard, player = player, wizard

        # get target piece
        target = self.sessions[room_id].boards[0]["state"]["targets"]
        result = "right" if piece.keys() == target.keys() else "wrong"

        # add selected piece to logs
        self.log_event("wizard_piece_selection", piece, room_id)

        # load next state
        if self.version not in {"confirm_selection", "show_gripper"}:
            self.load_next_state(room_id, result)
        else:
            self.sessions[room_id].selected_object = True

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
                    "message": (
                        "Your partner selected an object, is it correct? <br>"
                        "<button class='message_button' onclick=\"confirm_selection('yes')\">YES</button> "
                        "<button class='message_button' onclick=\"confirm_selection('no')\">NO</button>"
                    ),
                    "room": room_id,
                    "receiver_id": player["id"],
                    "html": True,
                },
            )

    def load_next_state(self, room_id, result):
        self.sessions[room_id].timer.reset()

        if result == "right":
            self.update_reward(room_id, POSITIVE_REWARD)
            self.sessions[room_id].points["history"][-1]["correct"] += 1
            result_emoji = "✅"
        else:
            self.update_reward(room_id, NEGATIVE_REWARD)
            self.sessions[room_id].points["history"][-1]["wrong"] += 1
            result_emoji = "❌"

        player, wizard = self.sessions[room_id].players
        if player["role"] != "player":
            player, wizard = wizard, player

        self.sessions[room_id].boards.pop(0)
        self.sessions[room_id].description = False
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
        self.set_message_privilege(player["id"], True)

        score = self.sessions[room_id].points["score"]

        if self.version != "no_feedback":
            # update points on title
            self.update_title_points(room_id)

        if not self.sessions[room_id].boards:
            # no more boards, close the room
            self.terminate_experiment(room_id)

        else:
            # create a new dictionary to keep track of board
            self.sessions[room_id].points["history"].append(
                {"correct": 0, "wrong": 0, "warnings": 0}
            )
            message = "Let's get you to the next board"
            if self.version != "no_feedback":
                message = f"That was the {result} piece {result_emoji} {message}"

            # limited number of boards, inform the user that how many left
            if BOARDS_PER_ROOM > 0:
                boards_left = len(self.sessions[room_id].boards)
                if boards_left % 5 == 0:
                    message = f"{message}. Still {boards_left} to go"

                    if boards_left < 10:
                        message = f"{message}. You almost made it!"

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
        self.request_feedback(response, "retrieving user's permissions")

        permission_id = response.json()["id"]
        requests.patch(
            f"{self.uri}/permissions/{permission_id}",
            json={"send_message": value},
            headers={
                "If-Match": response.headers["ETag"],
                "Authorization": f"Bearer {self.token}",
            },
        )
        self.request_feedback(response, "changing user's message permission")

    def set_wizard_role(self, room_id, user_id):
        self.sessions[room_id].timer.reset()

        curr_usr, other_usr = self.sessions[room_id].players
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

            # update title with points
            if self.version != "no_feedback":
                self.update_title_points(room_id)

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


    def load_state(self, room_id, from_disconnect=False):
        """load the current board on the golmi server"""
        # load and log state
        if not self.sessions[room_id].boards:
            return

        board = deepcopy(self.sessions[room_id].boards[0])

        # add gripper if not present
        if self.version == "show_gripper":
            if from_disconnect is False:
                # copy over to new board the gripper of the previous one
                # so that the controller can still operate it
                if not board["state"]["grippers"]:
                    req = requests.get(f"{self.golmi_server}/slurk/{room_id}/state")
                    self.request_feedback(req, "retrieving state")

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
            self.log_event("board_log", {"board": board}, room_id)

        self.sessions[room_id].golmi_client.load_config(board["config"])
        self.sessions[room_id].golmi_client.load_state(board["state"])

    def confirmation_code(self, room_id, status):
        """Generate AMT token that will be sent to each player."""
        amt_token = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        points = self.sessions[room_id].points
        # post AMT token to logs
        self.log_event(
            "confirmation_log",
            {"status_txt": status, "amt_token": amt_token, "reward": points},
            room_id,
        )

        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR,
                    message=(
                        "The experiment is over, please remember to "
                        "save your token before you close this browser window. "
                        f"Your token: {amt_token}"
                    ),
                ),
                "room": room_id,
                "html": True,
            },
        )

    def update_title_points(self, room_id):
        score = self.sessions[room_id].points["score"]

        correct = 0
        for board in self.sessions[room_id].points["history"]:
            # only count a board as correct if the wizard
            # got it on the first try (only relevant for confirm
            # selection and gripper variants)
            if board["wrong"] == 0:
                correct += board["correct"]

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/title",
            json={"text": f"Score: {score} 🏆 | Correct: {correct} ✅"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "setting point stand in title")

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        self.sio.emit(
            "text",
            {"message": "The room is closing, see you next time 👋", "room": room_id},
        )

        self.sessions[room_id].game_over = True
        self.room_to_read_only(room_id)
        self.sessions.clear_session(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "setting room to read_only")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "setting room title to read_only")

        # remove user from room
        if room_id in self.sessions:
            for usr in self.sessions[room_id].players:
                response = requests.get(
                    f"{self.uri}/users/{usr['id']}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "getting user")
                etag = response.headers["ETag"]

                response = requests.delete(
                    f"{self.uri}/users/{usr['id']}/rooms/{room_id}",
                    headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "removing user from task toom")
                logging.debug("Removing user from task room was successful.")

    def timeout_close_game(self, room_id, status):
        self.sio.emit(
            "text",
            {"message": "The room is closing because of inactivity", "room": room_id},
        )
        self.confirmation_code(room_id, status)
        self.close_game(room_id)

    def terminate_experiment(self, room_id):
        self.sio.emit(
            "text",
            {
                "room": room_id,
                "message": (
                    "The experiment is over 🎉 🎉 thank you very much for your time!"
                ),
                "html": True,
            },
        )
        self.confirmation_code(room_id, "sucess")
        self.close_game(room_id)


if __name__ == "__main__":
    # set up loggingging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = RecolageBot.create_argparser()
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
    bot = RecolageBot(
        args.token,
        args.user,
        args.task,
        args.host,
        args.port
    )
    bot.post_init(
        args.waiting_room,
        args.golmi_server,
        args.golmi_password,
        args.bot_version
    )
    # connect to chat server
    bot.run()
