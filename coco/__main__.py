import logging
import os
import random
from threading import Timer
from time import sleep

import requests

from templates import TaskBot
from .config import *
from .golmi_client import *


class RoomTimers:
    """A number of timed events during the game.

    :param alone_in_room: Closes a room if one player is alone in
        the room for longer than 5 minutes

    :param round_timer: After 15 minutes the image will change
        and players get no points
    """

    def __init__(self):
        self.left_room = dict()

    def cancel(self):
        for timer in self.left_room.values():
            timer.cancel()

    def reset(self):
        pass


class ActionNode:
    def __init__(self, action, obj):
        self.action = action
        self.obj = obj
        self.parent = None
        self.child = None

    def __str__(self):
        return f"Node({self.action}, {self.obj['type']})"

    def __repr__(self):
        return self.__str__()

    def next_state(self):
        if self.child is not None:
            return self.child
        return None

    def previous_state(self):
        if self.parent is not None:
            return self.parent
        return None

    def add_action(self, action, object):
        new_node = ActionNode(action, object)
        new_node.parent = self
        self.child = new_node
        return new_node

    @classmethod
    def new_tree(cls):
        return cls("root", None)


class Session:
    def __init__(self):
        self.players = list()
        self.timer = RoomTimers()
        self.golmi_client = None
        self.current_action = ActionNode.new_tree()
        self.states = load_states()
        self.game_over = False
        self.checkpoint = dict()

    def close(self):
        self.golmi_client.disconnect()
        self.timer.cancel()


class SessionManager(dict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)
            

class MoveEvaluator:
    def __init__(self, rules):
        self.rules = rules

    def can_place_on_top(self, this_obj, top_obj):
        if top_obj["type"] in self.rules:
            allowed_objs_on_top = self.rules[top_obj["type"]]
            if this_obj["type"] not in allowed_objs_on_top:
                return False
        return True

    def is_allowed(self, this_obj, client, x, y, block_size):
        # last item on cell cannot be a screw
        cell_objs = client.get_wizard_working_cell(
            x, y, block_size
        )

        if cell_objs:
            # make sure this object can be placed on the last one on this cell
            top_obj = cell_objs[-1]
            valid_placement = self.can_place_on_top(this_obj, top_obj)
            if valid_placement is False:
                return False

        if "bridge" in this_obj["type"]:
            # make sure bridges are levled on board
            this_cell_height = len(cell_objs)

            if this_obj["type"] == "hbridge":
                other_cell = (x + block_size, y)
            elif this_obj["type"] == "vbridge":
                other_cell = (x, y + block_size)

            x, y = other_cell
            other_cell_objs = client.get_wizard_working_cell(
                x, y, block_size
            )
            other_cell_height = len(other_cell_objs)

            if this_cell_height != other_cell_height:
                return False

            if other_cell_objs:
                # make sure bridge is not resting on a screw
                allowed_placement = self.can_place_on_top(this_obj, other_cell_objs[-1])
                if allowed_placement is False:
                    return False
        return True

class CoCoBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.sessions = SessionManager()
        self.move_evaluator = MoveEvaluator(RULES)
        self.register_callbacks()

    def post_init(self, waiting_room, golmi_server, golmi_password):
        """
        save extra variables after the __init__() method has been called
        and create the init_base_dict: a dictionary containing
        needed arguments for the init event to send to the JS frontend
        """
        self.waiting_room = waiting_room
        self.golmi_server = golmi_server
        self.golmi_password = golmi_password

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
                # reduce height of sidebar
                self.move_divider(room_id, chat_area=30, task_area=70)
                sleep(0.5)
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/sidebar",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"attribute": "style", "value": f"height: 90%; width:70%"},
                )
                # sleep(0.5)

                for usr in data["users"]:
                    self.received_waiting_token.discard(usr["id"])

                # create image items for this room
                logging.debug("Create data for the new task room...")

                self.sessions.create_session(room_id)
                for usr in data["users"]:
                    self.sessions[room_id].players.append(
                        {**usr, "role": None, "status": "joined"}
                    )

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(
                        f"Could not let coco bot join room: {response.status_code}"
                    )
                    response.raise_for_status()
                logging.debug("Sending wordle bot to new room was successful.")

                # create client
                client = QuadrupleClient(str(room_id), self.golmi_server)
                client.run(self.golmi_password)
                self.sessions[room_id].golmi_client = client

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]
            if room_id in self.sessions:
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
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                message=line, color=STANDARD_COLOR
                            ),
                            "room": room_id,
                            "html": True,
                        },
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
            elif room_id in self.sessions:
                curr_usr, other_usr = self.sessions[room_id].players
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr

                if data["type"] == "join":
                    sleep(0.5)
                    # inform game partner about the rejoin event
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                message=f"{curr_usr['name']} has joined the game.",
                                color=STANDARD_COLOR,
                            ),
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                            "html": True,
                        },
                    )

                    # check if the user has a role, if so, send role command
                    role = curr_usr["role"]
                    if role is not None:
                        golmi_rooms = self.sessions[room_id].golmi_client.rooms.json
                        self.sio.emit(
                            "message_command",
                            {
                                "command": {
                                    "event": "init",
                                    "url": self.golmi_server,
                                    "password": self.golmi_password,
                                    "instruction": INSTRUCTIONS[role],
                                    "role": role,
                                    "room_id": str(room_id),
                                    "golmi_rooms": golmi_rooms,
                                },
                                "room": room_id,
                                "receiver_id": curr_usr["id"],
                            },
                        )

                    # cancel timer
                    logging.debug(
                        f"Cancelling Timer: left room for user {curr_usr['name']}"
                    )
                    timer = self.sessions[room_id].timer.left_room.get(curr_usr["id"])
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
                                    "Please wait a bit, your partner may rejoin."
                                ),
                                color=STANDARD_COLOR,
                            ),
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                            "html": True,
                        },
                    )

                    # start timer since user left the room
                    logging.debug(
                        f"Starting Timer: left room for user {curr_usr['name']}"
                    )
                    self.sessions[room_id].timer.left_room[curr_usr["id"]] = Timer(
                        TIME_LEFT * 60, self.close_game, args=[room_id]
                    )
                    self.sessions[room_id].timer.left_room[curr_usr["id"]].start()

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

            this_client = self.sessions[room_id].golmi_client

            board = data["coordinates"]["board"]
            if board == "wizard_working":
                if data["coordinates"]["button"] == "left":
                    # check if the user selected an object on his selection board
                    selected = this_client.get_wizard_selection()
                    if selected:
                        # wizard wants to place a new object
                        obj = list(selected.values()).pop()

                        current_state = this_client.get_working_state()
                        id_n = new_obj_name(current_state)

                        x = data["coordinates"]["x"]
                        y = data["coordinates"]["y"]
                        block_size = data["coordinates"]["block_size"]

                        # update object
                        obj["id_n"] = id_n
                        obj["x"] = x // block_size
                        obj["y"] = y // block_size
                        obj["gripped"] = None

                        allowed_move = self.move_evaluator.is_allowed(obj, this_client, x, y, block_size)
                        if allowed_move is False:
                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        message="This move is not allowed",
                                        color=WARNING_COLOR,
                                    ),
                                    "room": room_id,
                                    "receiver_id": user_id,
                                    "html": True,
                                },
                            )
                            return

                        action, obj = this_client.add_object(obj)
                        if action is not False:
                            current_action = self.sessions[room_id].current_action
                            self.sessions[
                                room_id
                            ].current_action = current_action.add_action(action, obj)

                            # the state changes, log it
                            current_state = this_client.get_working_state()
                            self.log_event("working_board_log", current_state, room_id)

                        # ungrip any selected object
                        this_client.remove_selection("wizard_selection", "mouse")
                        this_client.remove_selection("wizard_working", "cell")

                    else:
                        # no object is selected, we can select this object
                        this_client.remove_selection("wizard_working", "cell")

                        piece = this_client.grip_object(
                            x=data["coordinates"]["x"],
                            y=data["coordinates"]["y"],
                            block_size=data["coordinates"]["block_size"],
                        )
                        self.log_event(
                            "user_selection",
                            dict(
                                x=data["coordinates"]["x"],
                                y=data["coordinates"]["y"],
                                block_size=data["coordinates"]["block_size"],
                                selection="single_object",
                                board="wizard_working",
                            ),
                            room_id,
                        )

                elif data["coordinates"]["button"] == "right":
                    this_client.remove_selection("wizard_selection", "mouse")
                    this_client.remove_selection("wizard_working", "mouse")

                    gripper_on_board = this_client.get_gripper("cell")

                    if gripper_on_board:
                        cell_objects = this_client.get_wizard_entire_cell(
                            x=gripper_on_board["x"],
                            y=gripper_on_board["y"],
                            block_size=1,
                        )

                        logging.debug(cell_objects)

                        old_x = gripper_on_board["x"]
                        old_y = gripper_on_board["y"]

                        for obj in cell_objects:
                            current_state = this_client.get_working_state()
                            id_n = new_obj_name(current_state)

                            block_size = data["coordinates"]["block_size"]
                            new_x = data["coordinates"]["x"] // block_size
                            new_y = data["coordinates"]["y"] // block_size

                            # update object parameters
                            obj["id_n"] = id_n
                            obj["x"] = obj["x"] - old_x + new_x
                            obj["y"] = obj["y"] - old_y + new_y
                            obj["gripped"] = None

                            allowed_move = self.move_evaluator.is_allowed(obj, this_client, obj["x"], obj["y"], 1)
                            if allowed_move is False:
                                self.sio.emit(
                                    "text",
                                    {
                                        "message": COLOR_MESSAGE.format(
                                            message="This move is not allowed",
                                            color=WARNING_COLOR,
                                        ),
                                        "room": room_id,
                                        "receiver_id": user_id,
                                        "html": True,
                                    },
                                )
                                this_client.remove_working_gripper("cell")
                                return

                            action, obj = this_client.add_object(obj)
                            if action is not False:
                                current_action = self.sessions[room_id].current_action
                                self.sessions[
                                    room_id
                                ].current_action = current_action.add_action(action, obj)

                                # the state changes, log it
                                current_state = this_client.get_working_state()
                                self.log_event("working_board_log", current_state, room_id)
                            else:
                                # invalid positioning, stop
                                return

                        this_client.remove_working_gripper("cell")
                        
                    else:
                        this_client.grip_cell(
                            x=data["coordinates"]["x"],
                            y=data["coordinates"]["y"],
                            block_size=data["coordinates"]["block_size"],
                        )

                        self.log_event(
                            "user_selection",
                            dict(
                                x=data["coordinates"]["x"],
                                y=data["coordinates"]["y"],
                                block_size=data["coordinates"]["block_size"],
                                selection="entire_cell",
                                board="wizard_working",
                            ),
                            room_id,
                        )

            if board == "wizard_selection":
                this_client.wizard_select_object(
                    x=data["coordinates"]["x"],
                    y=data["coordinates"]["y"],
                    block_size=data["coordinates"]["block_size"],
                )

                # remove selected objects from wizard's working board
                this_client.remove_selection("wizard_working", "mouse")
                this_client.remove_selection("wizard_working", "cell")

                self.log_event(
                    "user_selection",
                    dict(
                        x=data["coordinates"]["x"],
                        y=data["coordinates"]["y"],
                        block_size=data["coordinates"]["block_size"],
                        selection="single_object",
                        board="wizard_selection",
                    ),
                    room_id,
                )
                return

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

            curr_usr, other_usr = self.sessions[room_id].players
            if curr_usr["id"] != user_id:
                curr_usr, other_usr = other_usr, curr_usr

            if room_id in self.sessions:
                if isinstance(data["command"], dict):
                    event = data["command"]["event"]
                    # interface = self.sessions[room_id].robot_interface
                    this_client = self.sessions[room_id].golmi_client

                    # clear board
                    if event == "clear_board":
                        right_user = self.check_role(user_id, "wizard", room_id)
                        if right_user is False:
                            return

                        this_client.clear_working_state()
                        self.sessions[room_id].current_action = ActionNode.new_tree()

                    elif event == "delete_object":
                        right_user = self.check_role(user_id, "wizard", room_id)
                        if right_user is False:
                            return

                        selected = this_client.get_gripped_object()
                        if selected:
                            obj = list(selected.values()).pop()
                            action, obj = this_client.delete_object(obj)

                            if action is not False:
                                current_action = self.sessions[room_id].current_action
                                self.sessions[
                                    room_id
                                ].current_action = current_action.add_action(
                                    action, obj
                                )

                                # the state changes, log it
                                current_state = this_client.get_working_state()
                                self.log_event(
                                    "working_board_log", current_state, room_id
                                )

                    elif event == "show_progress":
                        right_user = self.check_role(user_id, "wizard", room_id)
                        if right_user is False:
                            return

                        this_client.copy_working_state()
                        current_state = this_client.get_working_state()
                        self.sessions[room_id].checkpoint = current_state

                    elif event == "revert_session":
                        right_user = self.check_role(user_id, "wizard", room_id)
                        if right_user is False:
                            return

                        # undo should not work anymore after reverting
                        self.sessions[room_id].current_action = ActionNode.new_tree()

                        client = self.sessions[room_id].golmi_client
                        client.load_working_state(self.sessions[room_id].checkpoint)

                        self.sio.emit(
                            "text",
                            {
                                "message": COLOR_MESSAGE.format(
                                    message="Reverting session to last checkpoint",
                                    color=STANDARD_COLOR,
                                ),
                                "room": room_id,
                                "receiver_id": curr_usr["id"],
                                "html": True,
                            },
                        )

                        # the state changes, log it
                        current_state = this_client.get_working_state()
                        self.log_event("working_board_log", current_state, room_id)

                    elif event == "work_in_progress":
                        right_user = self.check_role(user_id, "wizard", room_id)
                        if right_user is False:
                            return

                        self.sio.emit(
                            "text",
                            {
                                "message": COLOR_MESSAGE.format(
                                    message="... processing...",
                                    color=STANDARD_COLOR,
                                ),
                                "room": room_id,
                                "receiver_id": other_usr["id"],
                                "html": True,
                            },
                        )

                    elif event == "ok":
                        right_user = self.check_role(user_id, "wizard", room_id)
                        if right_user is False:
                            return

                        self.sio.emit(
                            "text",
                            {
                                "message": COLOR_MESSAGE.format(
                                    message="... ok...",
                                    color=SUCCESS_COLOR,
                                ),
                                "room": room_id,
                                "receiver_id": other_usr["id"],
                                "html": True,
                            },
                        )

                    elif event == "undo":
                        right_user = self.check_role(user_id, "wizard", room_id)
                        if right_user is False:
                            return

                        last_command = self.sessions[room_id].current_action

                        if last_command.action == "root":
                            return

                        if last_command.action == "add":
                            action, obj = this_client.delete_object(last_command.obj)
                        elif last_command.action == "delete":
                            action, obj = this_client.add_object(last_command.obj)

                        # register new last actiond
                        if action is not False:
                            current_state = last_command.previous_state()
                            if current_state is not None:
                                self.sessions[room_id].current_action = current_state

                                # the state changes, log it
                                current_state = this_client.get_working_state()
                                self.log_event(
                                    "working_board_log", current_state, room_id
                                )

                    elif event == "redo":
                        right_user = self.check_role(user_id, "wizard", room_id)
                        if right_user is False:
                            return

                        current_state = self.sessions[room_id].current_action
                        current_state = current_state.next_state()

                        if current_state is not None:
                            self.sessions[room_id].current_action = current_state

                            if current_state.action == "add":
                                action, obj = this_client.add_object(current_state.obj)
                            elif current_state.action == "delete":
                                action, obj = this_client.delete_object(
                                    current_state.obj
                                )

                            # register new last actiond
                            if action is not False:

                                # the state changes, log it
                                current_state = this_client.get_working_state()
                                self.log_event(
                                    "working_board_log", current_state, room_id
                                )

                    elif event == "next_state":
                        right_user = self.check_role(user_id, "player", room_id)
                        if right_user is False:
                            return

                        if self.sessions[room_id].game_over is True:
                            self.load_next_state(room_id)
                        else:
                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        message=(
                                            "The game is not over yet, you can only load the next "
                                            "episode once this is over (command: /episode:over)."
                                        ),
                                        color=WARNING_COLOR,
                                    ),
                                    "room": room_id,
                                    "receiver_id": curr_usr["id"],
                                    "html": True,
                                },
                            )

                else:
                    # user command
                    # set wizard
                    if data["command"] == "role:wizard":
                        self.set_wizard_role(room_id, user_id)

                    # elif data["command"] == "game:over":
                    #     right_user = self.check_role(user_id, "player", room_id)
                    #     if right_user is True:
                    #         self.close_game(room_id)

                    elif data["command"] == "episode:over":
                        right_user = self.check_role(user_id, "player", room_id)
                        if right_user is False:
                            return

                        self.sessions[room_id].game_over = True

                    else:
                        self.sio.emit(
                            "text",
                            {
                                "message": COLOR_MESSAGE.format(
                                    message="Sorry, but I do not understand this command.",
                                    color=STANDARD_COLOR,
                                ),
                                "room": room_id,
                                "receiver_id": user_id,
                                "html": True,
                            },
                        )

    def check_role(self, user_id, wanted_role, room_id):
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        if curr_usr["role"] == wanted_role:
            return True

        else:
            # inform user
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        message="You're not allowed to do that", color=WARNING_COLOR
                    ),
                    "room": room_id,
                    "receiver_id": user_id,
                    "html": True,
                },
            )

            return False

    def set_wizard_role(self, room_id, user_id):
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # users have no roles so we can assign them
        if curr_usr["role"] is None and other_usr["role"] is None:
            golmi_rooms = self.sessions[room_id].golmi_client.rooms.json
            for role, user in zip(["wizard", "player"], [curr_usr, other_usr]):
                user["role"] = role

                self.sio.emit(
                    "message_command",
                    {
                        "command": {
                            "event": "init",
                            "url": self.golmi_server,
                            "password": self.golmi_password,
                            "instruction": INSTRUCTIONS[role],
                            "role": role,
                            "room_id": str(room_id),
                            "golmi_rooms": golmi_rooms,
                        },
                        "room": room_id,
                        "receiver_id": user["id"],
                    },
                )
            self.load_state(room_id)

        else:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        message="Roles have already be assigned", color=WARNING_COLOR
                    ),
                    "room": room_id,
                    "receiver_id": user_id,
                    "html": True,
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

    def load_next_state(self, room_id):
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    message="Let's get you to the next board!", color=STANDARD_COLOR
                ),
                "room": room_id,
                "html": True,
            },
        )

        self.sessions[room_id].game_over = False
        self.sessions[room_id].timer.reset()
        self.sessions[room_id].states.pop(0)
        self.load_state(room_id)

    def load_state(self, room_id, from_disconnect=False):
        """load the current board on the golmi server"""
        if not self.sessions[room_id].states:
            self.sessions[room_id].states = load_states()

        # get current state
        this_state = self.sessions[room_id].states[0]
        client = self.sessions[room_id].golmi_client

        # load configuration and selector board
        client.load_config(CONFIG)
        client.load_selector()

        # load new target state
        client.load_target_state(this_state)
        client.clear_working_states()

        self.log_event("target_board_log", this_state, room_id)

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        sleep(2)
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    message="The room is closing, thanky you for plaing",
                    color=STANDARD_COLOR,
                ),
                "room": room_id,
                "html": True,
            },
        )
        self.room_to_read_only(room_id)

        # remove any task room specific objects
        self.sessions.clear_session(room_id)

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


if __name__ == "__main__":
    # set up loggingging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = CoCoBot.create_argparser()
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

    args = parser.parse_args()

    # create bot instance
    bot = CoCoBot(args.token, args.user, args.task, args.host, args.port)
    bot.post_init(args.waiting_room, args.golmi_server, args.golmi_password)
    # connect to chat server
    bot.run()
