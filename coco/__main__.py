import logging
import os
import random
from threading import Timer
from time import sleep

import requests

from templates import TaskBot
from .config import *
from .golmi_client import *
from .dataloader import Dataloader


class RoomTimers:
    """A number of timed events during the game.

    :param alone_in_room: Closes a room if one player is alone in
        the room for longer than 5 minutes

    :param round_timer: After 15 minutes the image will change
        and players get no points
    """

    def __init__(self):
        self.left_room = dict()
        self.typing_timer = None

    def cancel(self):
        self.typing_timer.cancel()
        for timer in self.left_room.values():
            timer.cancel()

    def reset(self):
        pass


class ActionNode:
    """Base class for the linked list representing
    the action history, every action performed by the wizard
    if saved as a node in this linked list to allow for
    the redo and undo button
    """
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
        self.checkpoint = EMPTYSTATE

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
    """Given a json file containing the placing rules
    this class decides if a move is allowed or not
    """
    def __init__(self, rules):
        self.rules = rules

    def can_place_on_top(self, this_obj, top_obj):
        if top_obj["type"] in self.rules:
            allowed_objs_on_top = self.rules[top_obj["type"]]
            if this_obj["type"] not in allowed_objs_on_top:
                return False
        return True

    def is_allowed(self, this_obj, client, x, y, block_size):
        # coordinates must be on the board
        board_x = x // block_size
        board_y = y // block_size

        if board_x < 0 or board_x > CONFIG["width"]:
            return False

        if board_y < 0 or board_y > CONFIG["height"]:
            return False

        # last item on cell cannot be a screw
        cell_objs = client.get_entire_cell(
            x=x, y=y, block_size=block_size, board="wizard_working"
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
            other_cell_objs = client.get_entire_cell(
                x=x, y=y, block_size=block_size, board="wizard_working"
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
        self.patterns = get_patterns()

    def post_init(self, waiting_room, golmi_server, golmi_password):
        """
        save extra variables after the __init__() method has been called
        and create the init_base_dict: a dictionary containing
        needed arguments for the init event to send to the JS frontend
        """
        self.waiting_room = waiting_room
        self.golmi_server = golmi_server
        self.golmi_password = golmi_password

    def on_task_room_creation(self, data):
        """This function is executed as soon as 2 users are paired and a new
        task took is created
        """
        room_id = data["room"]
        task_id = data["task"]

        logging.debug(f"A new task room was created with id: {data['task']}")
        logging.debug(f"This bot is looking for task id: {self.task_id}")

        if task_id is not None and task_id == self.task_id:
            # move the chat | task area divider
            self.move_divider(room_id, chat_area=30, task_area=70)
            sleep(0.5)

            # reduce height of sidebar
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/sidebar",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"attribute": "style", "value": f"height: 90%; width:70%"},
            )
            sleep(0.5)

            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])

            # create a new session for these users
            logging.debug("Create data for the new task room...")
            self.sessions.create_session(room_id)
            for usr in data["users"]:
                self.sessions[room_id].players.append(
                    {**usr, "role": None, "status": "joined"}
                )

            # join the newly created room
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

            # create and connect the golmi client
            client = QuadrupleClient(str(room_id), self.golmi_server)
            client.run(self.golmi_password)
            self.sessions[room_id].golmi_client = client

    def send_typing_input(self, room_id):
        """Send typing events when the wizard is working on the boards
        """
        player, wizard = self.sessions[room_id].players
        if player["role"] != "player":
            player, wizard = wizard, player

        def send_typing(value, room_id, user):
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "typing",
                        "value": value
                    },
                    "room": room_id,
                    "receiver_id": user["id"],
                },
            )

        # no need to send a new start typing event if the old one is still running
        timer = self.sessions[room_id].timer.typing_timer
        if timer is None or timer.is_alive() is False:
            send_typing(True, room_id, wizard)

        # cancel old timer to avoid overlapping events
        if timer is not None:
            timer.cancel()

        # start a new timer for the stop typing event
        self.sessions[room_id].timer.typing_timer = Timer(3,
            send_typing,
            args=[False, room_id, wizard]
        )
        self.sessions[room_id].timer.typing_timer.start()

    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]
            if room_id in self.sessions:
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
            """capture mouse clicks on the board
            """
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
                if data["coordinates"]["ctrl"] is False:
                    # send typing message
                    self.send_typing_input(room_id)

                    # check if the user selected an object on his selection board
                    selected = this_client.get_wizard_selection()
                    current_state = this_client.get_working_state()
                    if selected:
                        # wizard wants to place a new object
                        obj = list(selected.values()).pop()
                        id_n = new_obj_name(current_state)

                        x = data["coordinates"]["x"]
                        y = data["coordinates"]["y"]
                        block_size = data["coordinates"]["block_size"]

                        # update object
                        obj["id_n"] = id_n
                        obj["x"] = x // block_size
                        obj["y"] = y // block_size
                        obj["gripped"] = None

                        allowed_move = self.move_evaluator.is_allowed(
                            obj, this_client, x, y, block_size
                        )
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
                        this_client.remove_cell_grippers()

                    else:
                        # no object is selected, we can select this object
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

                        if piece:
                            this_client.remove_cell_grippers()
                        else:
                            current_state = this_client.get_working_state()
                            if any("cell" in i for i in current_state["grippers"].keys()):
                                cells_to_copy = list()
                                positions = list()
                                clicks = list()
                                for name, gripper in current_state["grippers"].items():
                                    if "cell" in name:
                                        cell_index = int(name.split("_")[-1])
                                        clicks.append((cell_index, (gripper["x"], gripper["y"])))
                                        cell_objects = this_client.get_entire_cell(
                                            x=gripper["x"],
                                            y=gripper["y"],
                                            block_size=1,
                                            board="wizard_working",
                                        )
                                        cells_to_copy.append(cell_objects)
                                        positions.append((gripper["x"], gripper["y"]))

                                # build structure bottom up
                                highest_index = max(len(i) for i in cells_to_copy)

                                # check first click
                                clicks.sort()
                                first_x, first_y = clicks[0][-1]

                                # anchor coordinates for copying
                                block_size = data["coordinates"]["block_size"]
                                new_x = data["coordinates"]["x"] // block_size
                                new_y = data["coordinates"]["y"] // block_size
                                already_placed = set()

                                for i in range(highest_index):
                                    for cell, position in zip(cells_to_copy, positions):
                                        current_state = this_client.get_working_state()
                                        id_n = new_obj_name(current_state)

                                        old_x, old_y = position
                                        translation_x = first_x - old_x
                                        translation_y = first_y - old_y

                                        if i >= len(cell):
                                            continue

                                        obj = cell[i]

                                        if obj["id_n"] not in already_placed:
                                            already_placed.add(obj["id_n"])
                                            obj["id_n"] = id_n
                                            obj["x"] = obj["x"] - old_x + new_x - translation_x
                                            obj["y"] = obj["y"] - old_y + new_y - translation_y
                                            obj["gripped"] = None

                                            allowed_move = self.move_evaluator.is_allowed(
                                                obj, this_client, obj["x"], obj["y"], 1
                                            )
                                            logging.debug("**********************************")
                                            logging.debug(allowed_move)
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
                                                this_client.remove_cell_grippers()
                                                return

                                            action, obj = this_client.add_object(obj)
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
                                            else:
                                                # invalid positioning, stop
                                                logging.debug("**********************************")
                                                return

                                this_client.remove_cell_grippers()

                elif data["coordinates"]["ctrl"] is True:
                    this_client.remove_selection("wizard_selection", "mouse")
                    this_client.remove_selection("wizard_working", "mouse")

                    gripper_on_board = this_client.get_gripper("cell")
                    current_state = this_client.get_working_state()

                    # obtain new name for this gripper
                    taken = [int(i.split("_")[-1]) for i in current_state["grippers"]]
                    taken.sort()

                    if not taken:
                        gripper_id = 0
                    else:
                        highest = taken[-1]
                        possible = set(range(highest + 2))
                        new_ids = list(possible - set(taken))
                        new_ids.sort()
                        gripper_id = new_ids[0]


                    this_client.add_gripper(
                        gripper=f"cell_{gripper_id}",
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
                self.send_typing_input(room_id)
                this_client.wizard_select_object(
                    x=data["coordinates"]["x"],
                    y=data["coordinates"]["y"],
                    block_size=data["coordinates"]["block_size"],
                )

                # remove selected objects from wizard's working board
                this_client.remove_selection("wizard_working", "mouse")
                this_client.remove_cell_grippers()

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

            if board == "player_target":
                cell = this_client.get_entire_cell(
                    x=data["coordinates"]["x"],
                    y=data["coordinates"]["y"],
                    block_size=data["coordinates"]["block_size"],
                    board="target",
                )

                if cell:
                    message = "Bottom to top: "
                    obj_strings = list()
                    for obj in cell:
                        name = obj["type"]
                        if name == "vbridge":
                            name = "vertical bridge"

                        if name == "hbridge":
                            name = "horizontal bridge"

                        this_obj = f"{obj['color'][0]} {name}"
                        obj_strings.append(this_obj)

                    message += ", ".join(obj_strings)

                    # detect patterns
                    state = this_client.get_target_state()
                    cell_ids = [obj["id_n"] for obj in cell]

                    x = int(data["coordinates"]["x"] // data["coordinates"]["block_size"])
                    y = int(data["coordinates"]["y"] // data["coordinates"]["block_size"])
                    coordinates = f"{y}:{x}"

                    for pattern in self.patterns:
                        if pattern.detect((coordinates, cell_ids), state):
                            message += " | detected patterns:"
                            
                            if pattern.cells > 1:
                                message += f" part of a {pattern.name}"
                            else:
                                message += f" {pattern.name}"

                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                message=message,
                                color=STANDARD_COLOR,
                            ),
                            "room": room_id,
                            "receiver_id": user_id,
                            "html": True,
                        },
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
                                    message="ready",
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

                    elif event == "inspect":
                        gripper = this_client.get_mouse_gripper()
                        cell = this_client.get_entire_cell(
                            x=gripper["x"],
                            y=gripper["y"],
                            block_size=1,
                            board="wizard_working",
                        )

                        if cell:
                            message = "Bottom to top: "
                            obj_strings = list()
                            for obj in cell:
                                name = obj["type"]
                                if name == "vbridge":
                                    name = "vertical bridge"

                                if name == "hbridge":
                                    name = "horizontal bridge"

                                this_obj = f"{obj['color'][0]} {name}"
                                obj_strings.append(this_obj)

                            message += ", ".join(obj_strings)

                            state = this_client.get_working_state()
                            cell_ids = [obj["id_n"] for obj in cell]

                            x = int(gripper["x"])
                            y = int(gripper["y"])
                            coordinates = f"{y}:{x}"

                            for pattern in self.patterns:
                                if pattern.detect((coordinates, cell_ids), state):
                                    message += " | detected patterns:"
                                    
                                    if pattern.cells > 1:
                                        message += f" part of a {pattern.name}"
                                    else:
                                        message += f" {pattern.name}"

                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        message=message,
                                        color=STANDARD_COLOR,
                                    ),
                                    "room": room_id,
                                    "receiver_id": curr_usr["id"],
                                    "html": True,
                                },
                            )
                            return

                else:
                    # user command
                    # set wizard
                    if data["command"] == "role:wizard":
                        self.set_wizard_role(room_id, user_id)

                    elif data["command"] == "episode:over":
                        right_user = self.check_role(user_id, "player", room_id)
                        if right_user is False:
                            return

                        # load next state
                        self.load_next_state(room_id)

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
        self.sessions[room_id].timer.reset()
        self.sessions[room_id].states.pop(0)
        self.load_state(room_id)

    def load_state(self, room_id, from_disconnect=False):
        """load the current board on the golmi server"""
        if not self.sessions[room_id].states:
            self.sessions[room_id].states.get_boards()

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
