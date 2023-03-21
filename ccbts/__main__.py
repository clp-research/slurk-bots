import logging
import os
import random
from threading import Timer
from time import sleep

import requests

from templates import TaskBot
from wizardinterface import WizardInterface
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


class CcbtsBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.players_per_room = dict()
        self.images_per_room = dict()
        self.robot_interfaces = dict()
        self.timers_per_room = dict()
        self.golmi_client_per_room = dict()
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
                        f"Could not let coco bot join room: {response.status_code}"
                    )
                    response.raise_for_status()
                logging.debug("Sending wordle bot to new room was successful.")

                # create new timer for this room
                self.timers_per_room[room_id] = RoomTimers()

                self.golmi_client_per_room[room_id] = TripleClient(str(room_id), self.golmi_server)
                self.golmi_client_per_room[room_id].run(self.golmi_password)
                self.golmi_client_per_room[room_id].load_config(CONFIG)

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
                    self.move_divider(room_id, chat_area=30, task_area=70)
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

                    # check if the user has a role, if so, send role command
                    role = curr_usr["role"]
                    if role is not None:
                        self.sio.emit(
                            "message_command",
                            {
                                "command": {
                                    "event": "assign_role",
                                    "role": role,
                                    "instruction": INSTRUCTIONS[role],
                                },
                                "room": room_id,
                                "receiver_id": curr_usr["id"],
                            },
                        )

                        # send board again
                        self.set_boards(room_id)

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
                                    "Please wait a bit, your partner may rejoin."
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
        def mouse(data):
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process events from itself
            if user_id == self.user:
                return

            if room_id not in self.players_per_room:
                return

            # don't react to mouse movements
            if data["type"] != "click":
                return

            logging.debug(data)
            this_client = self.golmi_client_per_room[room_id]

            action = data["coordinates"]["action"]
            if action == "place":
                state = this_client.get_working_state()

                shape = data["coordinates"]["shape"]
                color = data["coordinates"]["color"]

                # create a new object and add it to the state
                obj = OBJS[shape]
                obj["color"] = COLORS[color]
                x = data["coordinates"]["x"] // data["coordinates"]["block_size"]
                y = data["coordinates"]["y"] // data["coordinates"]["block_size"]

                obj["x"] = x #- len(obj["block_matrix"][0]) // 2
                obj["y"] = y #- len(obj["block_matrix"]) // 2
                
                id_n = str(next(NAME_GEN))
                obj["id_n"] = id_n
                state["objs"][id_n] = obj

                this_client.load_working_state(state)

            elif action == "select":
                piece = this_client.grip_object(
                    x=data["coordinates"]["x"],
                    y=data["coordinates"]["y"],
                    block_size=data["coordinates"]["block_size"]
                )
                if piece:
                    piece = list(piece.values())[0]
                    self.sio.emit(
                        "message_command",
                        {
                            "command": {
                                "event": "update_selectors",
                                "color": piece["color"][0],
                                "shape": piece["type"],
                            },
                            "room": room_id,
                            "receiver_id": user_id,
                        }
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

            if room_id in self.images_per_room:
                if isinstance(data["command"], dict):
                    event = data["command"]["event"]
                    interface = self.robot_interfaces[room_id]
                    this_client = self.golmi_client_per_room[room_id]
                    # front end commands (wizard only)
                    right_user = self.check_role(user_id, "wizard", room_id)
                    if right_user is True:
                        # clear board
                        if event == "clear_board":
                            # interface.clear_board()
                            # self.set_boards(room_id)
                            this_client.clear_working_state()

                        elif event == "delete_object":
                            
                            state = this_client.get_working_state()

                            # obtain selected object
                            gripped = state["grippers"]["mouse"]["gripped"]
                            state["grippers"]["mouse"]["gripped"] = None
                            gripped_id = list(gripped.keys())[0]
                            state["objs"].pop(gripped_id)

                            # load new state
                            this_client.load_working_state(state)

                        elif event == "show_progress":
                            this_client.copy_working_state()

                        # run command
                        # elif event == "run":
                        #     commands = data["command"]["commands"]
                        #     to_run = commands.copy()
                        #     executed = list()

                        #     for command in commands:
                        #         result = self.run_command(command, room_id, user_id)
                        #         if result[0] is True:
                        #             executed.append(to_run.pop(0))

                        #             self.sio.emit(
                        #                 "message_command",
                        #                 {
                        #                     "command": {
                        #                         "event": "success_run",
                        #                         "executed": command,
                        #                         "to_run": to_run 
                        #                     },
                        #                     "room": room_id,
                        #                     "receiver_id": user_id,
                        #                 }
                        #             )
                        #         else:
                        #             return

                        # revert session
                        # elif event == "revert_session":
                        #     history = data["command"]["command_list"]
                        #     try:
                        #         status = interface.revert_session(history)

                        #     except (KeyError, TypeError, OverflowError) as error:
                        #         self.sio.emit(
                        #             "text",
                        #             {
                        #                 "message": COLOR_MESSAGE.format(
                        #                     color=WARNING_COLOR, message=str(error)
                        #                 ),
                        #                 "room": room_id,
                        #                 "receiver_id": user_id,
                        #                 "html": True
                        #             },
                        #         )
                        #     self.set_boards(room_id)

                        # change the color of the selected object
                        elif event == "update_object":
                            this_client = self.golmi_client_per_room[room_id]
                            state = this_client.get_working_state()
                            piece = this_client.get_gripped_object()

                            if piece:
                                id_n = list(piece.keys())[0]
                                obj = piece[id_n]

                                color = data["command"]["color"]
                                shape = data["command"]["shape"]
                                if color in COLORS:
                                    new_color = COLORS[color]
                                    obj["color"] = new_color

                                state["objs"][id_n] = obj
                                state["grippers"]["mouse"]["gripped"][id_n] = obj

                                logging.debug(state)
                                this_client.load_working_state(state)

                else:
                    # user command
                    # set wizard
                    if data["command"] == "role:wizard":
                        self.set_wizard_role(room_id, user_id)

                    # reset roles
                    elif data["command"] == "reset_roles":
                        self.reset_roles(room_id)

                    elif data["command"] == "game_over":
                        right_user = self.check_role(user_id, "player", room_id)
                        if right_user is True:
                            self.close_game(room_id)

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

    def check_role(self, user_id, wanted_role, room_id):
        curr_usr, other_usr = self.players_per_room[room_id]
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
                        message="You're not allowed to do that",
                        color=WARNING_COLOR
                    ),
                    "room": room_id,
                    "receiver_id": user_id,
                    "html": True
                },
            )

            return False

    def run_command(self, command, room_id, user_id):
        """
        pass a command list to the backend
        """
        interface = self.robot_interfaces[room_id]
        try:
            result = interface.play(command)

        except (KeyError, TypeError, OverflowError) as error:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=WARNING_COLOR, message=str(error)
                    ),
                    "room": room_id,
                    "receiver_id": user_id,
                    "html": True
                },
            )
            result = [False]
        
        # update board for wizard and send feedback
        self.set_boards(room_id)
        return result

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
                # self.sio.emit(
                #     "message_command",
                #     {
                #         "command": {
                #             "event": "assign_role",
                #             "role": role,
                #             "instruction": INSTRUCTIONS[role],
                #         },
                #         "room": room_id,
                #         "receiver_id": user["id"],
                #     },
                # )
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
                        },
                        "room": room_id,
                        "receiver_id": user["id"],
                    },
                )

            # self.set_image(room_id, other_usr)
            # self.set_boards(room_id)
            random_state = get_random_state()
            self.golmi_client_per_room[room_id].load_target_state(random_state)
            self.golmi_client_per_room[room_id].clear_working_states()

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
                        "event": "reset_roles",
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

    def set_boards(self, room_id, wizard_only=False):
        # get boards from the robot interface
        interface = self.robot_interfaces[room_id]
        boards = interface.get_boards()
        source_board = boards["s"].tolist()
        target_board = boards["t"].tolist()

        # get player information
        player_usr, wizard_usr = self.players_per_room[room_id]
        if player_usr["role"] != "player":
            player_usr, wizard_usr = wizard_usr, player_usr

        # send board update
        for name, board in zip(["source", "target"], [source_board, target_board]):
            command_dict = {
                "command": {
                    "event": "set_board",
                    "board": board,
                    "name": name,
                },
                "room": room_id
            }

            if wizard_only is True:
                command_dict["receiver_id"] = wizard_usr["id"]

            # set source board
            self.sio.emit("message_command", command_dict)

        # set reference board (only player)
        if wizard_only is False:
            # TODO wizard interface should return numpy array
            if not hasattr(interface, "ref_board"):
                reference_json = interface.get_reference_boards()
                reference_board = random.choice(list(reference_json["references"].values()))
                interface.ref_board = reference_board

            reference_board = interface.ref_board

            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "set_board",
                        "board": reference_board,
                        "name": "reference",
                    },
                    "room": room_id,
                    "receiver_id": player_usr["id"],
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
    bot = CcbtsBot(args.token, args.user, args.task, args.host, args.port)
    bot.post_init(args.waiting_room, args.golmi_server, args.golmi_password)
    # connect to chat server
    bot.run()
