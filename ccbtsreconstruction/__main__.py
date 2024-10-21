import logging
import os
from threading import Timer
from time import sleep
import requests

from templates import TaskBot

from .config import *
from .utils import *
from .preparedata import Dataloader

TIMEOUT_TIMER = 60  # minutes
LEAVE_TIMER = 60  # minutes
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
INSTRUCTION_COLOR = "Blue"
WARNING_COLOR = "FireBrick"

class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER*60,
            self.function,
            args=[self.room_id]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.debug("reset timer")

    def cancel(self):
        self.timer.cancel()


class CCBTSReconstructionBot(TaskBot):
    timers_per_room = dict()

    def __init__(self, token, user, task, host, port):
        logging.debug(f"CCBTS Reconstruction: __init__, task = {task}, user = {user}")
        super().__init__(token, user, task, host, port)
        self.num_boards = 0
        self.golmi_client = None
        self.checkpoint = EMPTYSTATE
        self.game_over = False
        self.move_evaluator = MoveEvaluator(RULES)

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
        room_id = data["room"]
        task_id = data["task"]

        self.num_boards = 0
        self.board_info = {}
        self.dataloader = Dataloader()

        if task_id is not None and task_id == self.task_id:
            self.disable_chat_area(room_id)
            self.timers_per_room[room_id] = RoomTimer(self.close_room, room_id)

            for usr in data["users"]:
                logging.debug(
                    f"Loading input grid during task creation room_id: {room_id} user_id: {usr['id']}"
                )
            self.showwelcomemessage(room_id, usr["id"])

            logging.debug(f"Creating golmi client for room {room_id}")
            # create and connect the golmi client
            client = QuadrupleClient(str(room_id), self.golmi_server)
            client.run(self.golmi_password)
            self.golmi_client = client

            self.setwizardrole(room_id, usr["id"])
            self.load_target_instruction(room_id, usr["id"])


    def showwelcomemessage(self, room_id, user_id):
        """Show welcome message."""
        logging.debug(f"Inside showwelcomemessage, room_id = {room_id}, user_id = {user_id}")
        welcome_message = "Welcome to the COCOBOT Task Room <br><br> You need to reconstruct the board by following the given instructions.<br><br>"
        #Downloaded the image from this site: https://apps.timwhitlock.info/emoji/tables/unicode
        #Emoji: SCROLL, U+1F447
        task_message = "Read the instructions below 👇<br>"
        self.sio.emit(
            "text",
            {
                "room": room_id,
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR,
                    message=welcome_message+task_message,
                ),
                "receiver_id": user_id,
                "html": True,
            },
            callback=self.message_callback,
        )     

    def setwizardrole(self, room_id, user_id):
        golmi_rooms = self.golmi_client.rooms.json
        logging.debug(f"Inside setwizardrole, room_id = {room_id}, user_id = {user_id} golmi_rooms = {golmi_rooms}")
        logging.debug(f"setwizardrole(), sending init event to golmi_rooms")
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "init",
                    "url": self.golmi_server,
                    "password": self.golmi_password,
                    "instruction": INSTRUCTIONS['wizard'],
                    "role": 'wizard',
                    "room_id": str(room_id),
                    "golmi_rooms": golmi_rooms,
                },
                "room": room_id,
                "receiver_id": user_id,
            },
        )

        client = self.golmi_client

        # load configuration and selector board
        client.load_config(CONFIG)
        client.load_state(SELECTIONSTATE, "selector")

        # send to frontend instructions
        logging.debug(f"setwizardrole(), sending instruction event to frontend")
        role = "wizard"
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "instruction",
                    "base": INSTRUCTIONS[role],
                    "extra": [role],
                },
                "room": room_id,
                "receiver_id": user_id,
            },
        )            

    def load_target_instruction(self, room_id, user_id):
        """Load the target board."""
        logging.debug(f"Inside load_target_instruction, room_id = {room_id}, user_id = {user_id}")

        client = self.golmi_client
        working_state = client.get_state("wizard_working")
        if self.num_boards:
            #Log the data
            data = {"working_board_state": working_state,
                    "boardinfo": self.board_info,
                   }
            self.log_event("reconstruction_log", data, room_id)
            self.board_info = {}

        client.clear_state("wizard_working")

        self.num_boards += 1

        if self.num_boards >= 11:
            #User has reconstructed 10 boards, close the room
            logging.debug("User has reconstructed 10 boards, close the room")

            self.sio.emit(
                "message_command",
                {
                    "command": {"event": "close_after_10_boards", "message": ""},
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )

            self.sio.emit(
                "text",
                {
                    "room": room_id,
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message="You have done 10 boards, please take a break and get back to me later. Room is closing now",
                    ),
                    "receiver_id": user_id,
                    "html": True,
                },
                callback=self.message_callback,
            ) 

            self.close_room(room_id)
            return
        
        board_info = self.dataloader.get_target_board()
        logging.debug(f"board_instruction is:\n{board_info['instruction']}")
        logging.debug(f"Other board_info: boardname: {board_info['boardname']}, filename: {board_info['filename']}, objectname: {board_info['objectname']}, legendname: {board_info['legendname']}")
        self.board_info = board_info
        self.sio.emit(
            "text",
            {
                "room": room_id,
                "message": COLOR_MESSAGE.format(
                    color=INSTRUCTION_COLOR,
                    message=f"<span style='color:{INSTRUCTION_COLOR}; font-size:20px;'>{board_info['instruction']}</span>",
                ),
                "receiver_id": user_id,
                "html": True,
            },
            callback=self.message_callback,
        )
        '''
        message_color = WARNING_COLOR
        message=(
        "After you complete the reconstuction, click here to go to next instruction <br>"
        "<button class='message_button' onclick=\"goto_next_board()\">Next Board</button> "
        )
        output_to_show = COLOR_MESSAGE.format(color=message_color, message=message)
        self.sio.emit(
                        "text",
                        {
                            "room": room_id,
                            "message": output_to_show,
                            #"message": COLOR_MESSAGE.format(
                            #    color=STANDARD_COLOR, message=output
                            #),
                            "html": True,
                        },
                        callback=self.message_callback,
                    )     
        '''
        if board_info["legend_image_base64"]:
            #Need to display the legend image in the chat area
            logging.debug(f"Legend is available, should show the image in the legend area")
            role = "wizard"
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "add_legend",
                        "base": INSTRUCTIONS[role],
                        "extra": {"name": board_info["legendname"]["objectname"], "image": board_info["legend_image_base64"]},
                    },
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )                          


    def close_room(self, room_id):
        self.dataloader.save_board_viewing_status()
        self.room_to_read_only(room_id)
        self.golmi_client.disconnect()
        self.timers_per_room.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        response = self.disable_chat_area(room_id)

        users = response.json()
        for user in users:
            if user["id"] != self.user:
                response = requests.get(
                    f"{self.uri}/users/{user['id']}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(f"Could not get user: {response.status_code}")
                    response.raise_for_status()
                etag = response.headers["ETag"]

                response = requests.delete(
                    f"{self.uri}/users/{user['id']}/rooms/{room_id}",
                    headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(
                        f"Could not remove user from task room: {response.status_code}"
                    )
                    response.raise_for_status()
                logging.debug("Removing user from task room was successful.")

    def disable_chat_area(self, room_id):
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

        response = requests.get(
            f"{self.uri}/rooms/{room_id}/users",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not get user: {response.status_code}")   

        return response



    def register_callbacks(self):
        @self.sio.event
        def text_message(data):
            if self.user == data["user"]["id"]:
                return
            else:
                room_id = data["room"]
                timer = self.timers_per_room.get(room_id)
                if timer is not None:
                    timer.reset()

            logging.debug(f"I got a message, let's send it back!: {data}")

            options = {}
            if data["private"]:
                logging.debug("It was actually a private message o.O")
                options["receiver_id"] = data["user"]["id"]

            message = data["message"]
            if message.lower() == "hello":
                message = "World!"
            elif message.lower() == "ping":
                message = "Pong!"

            self.sio.emit(
                "text",
                {
                    "room": data["room"],
                    "message": message,
                    **options
                },
                callback=self.message_callback,
            )

        @self.sio.event
        def image_message(data):
            if self.user == data["user"]["id"]:
                return
            else:
                room_id = data["room"]
                timer = self.timers_per_room.get(room_id)
                if timer is not None:
                    timer.reset()

            logging.debug(f"I got an image, let's send it back!: {data}")

            options = {}
            if data["private"]:
                logging.debug("It was actually a private image o.O")
                options["receiver_id"] = data["user"]["id"]

            self.sio.emit(
                "image",
                {
                    "room": data["room"],
                    "url": data["url"],
                    "width": data["width"],
                    "height": data["height"],
                    **options,
                },
                callback=self.message_callback,
            )

        @self.sio.event
        def mouse(data):
            """capture mouse clicks on the board"""
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process events from itself
            if user_id == self.user:
                return


            # don't react to mouse movements
            if data["type"] != "click":
                return

            this_client = self.golmi_client
            board = data["coordinates"]["board"]


            # the wizard picks an object from the selection board
            if board == "wizard_selection":
                this_client.grip_object(
                    x=data["coordinates"]["x"],
                    y=data["coordinates"]["y"],
                    block_size=data["coordinates"]["block_size"],
                    board="selector",
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

            # right click actions
            if data["coordinates"]["button"] == "right":
                selected = this_client.get_entire_cell(
                    x=data["coordinates"]["x"],
                    y=data["coordinates"]["y"],
                    block_size=data["coordinates"]["block_size"],
                    board="wizard_working",
                )

                if selected:
                    obj = selected.pop()
                    action, obj = this_client.delete_object(obj)

                    if action is not False:
                        '''
                        current_action = this_session.current_action
                        this_session.current_action = current_action.add_action(
                            action, obj
                        )
                        '''

                        # the state changes, log it
                        current_state = this_client.get_state("wizard_working")
                        self.log_event("working_board_log", current_state, room_id)
                return

            # select multiple cells with ctrl button
            if data["coordinates"]["ctrl"] is True:
                this_client.remove_selection("wizard_selection", "mouse")
                this_client.remove_selection("wizard_working", "mouse")

                gripper_on_board = this_client.get_gripper("cell", "wizard_working")
                current_state = this_client.get_state("wizard_working")

                # coordinates
                this_x = data["coordinates"]["x"]
                this_y = data["coordinates"]["y"]
                block_size = data["coordinates"]["block_size"]

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

                for gripper in current_state["grippers"].values():
                    if (
                        gripper["x"] == this_x // block_size
                        and gripper["y"] == this_y // block_size
                    ):
                        this_client.remove_gripper(gripper["id_n"], "wizard_working")
                        return

                this_client.add_gripper(
                    gripper=f"cell_{gripper_id}",
                    x=data["coordinates"]["x"],
                    y=data["coordinates"]["y"],
                    block_size=data["coordinates"]["block_size"],
                    board="wizard_working",
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
                return

            # left click actions
            # if data["coordinates"]["ctrl"] is False:
            # send typing message


            # check if the user selected an object on his selection board
            selected = this_client.get_gripped_object("selector")
            current_state = this_client.get_state("wizard_working")
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

                allowed_move, reason = self.move_evaluator.is_allowed(
                    obj, this_client, x, y, block_size
                )
                if allowed_move is False:
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                message=f"This move is not allowed: {reason}",
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
                    #current_action = this_session.current_action
                    #this_session.current_action = current_action.add_action(action, obj)

                    # the state changes, log it
                    current_state = this_client.get_state("wizard_working")
                    self.log_event("working_board_log", current_state, room_id)

                # ungrip any selected object
                this_client.remove_selection("wizard_selection", "mouse")
                this_client.remove_cell_grippers()

            else:
                # no object is selected
                current_state = this_client.get_state("wizard_working")

                # objects are selected with ctrl, cell deep copy
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

                    backup_state = this_client.get_state("wizard_working")

                    # start placing the selected objects from the bottom up
                    for i in range(highest_index):
                        for cell, position in zip(cells_to_copy, positions):
                            current_state = this_client.get_state("wizard_working")
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

                                (
                                    allowed_move,
                                    reason,
                                ) = self.move_evaluator.is_allowed(
                                    obj, this_client, obj["x"], obj["y"], 1
                                )
                                if allowed_move is False:
                                    self.sio.emit(
                                        "text",
                                        {
                                            "message": COLOR_MESSAGE.format(
                                                message=f"This move is not allowed: {reason}",
                                                color=WARNING_COLOR,
                                            ),
                                            "room": room_id,
                                            "receiver_id": user_id,
                                            "html": True,
                                        },
                                    )
                                    this_client.remove_cell_grippers()

                                    # load the state before positioning any object
                                    this_client.load_state(
                                        backup_state, "wizard_working"
                                    )
                                    return

                                action, obj = this_client.add_object(obj)
                                if action is not False:
                                    '''
                                    current_action = this_session.current_action
                                    this_session.current_action = (
                                        current_action.add_action(action, obj)
                                    )
                                    '''

                                    # the state changes, log it
                                    current_state = this_client.get_state(
                                        "wizard_working"
                                    )
                                    self.log_event(
                                        "working_board_log",
                                        current_state,
                                        room_id,
                                    )
                                else:
                                    # invalid positioning, stop (probably not needed)
                                    this_client.load_state(
                                        backup_state, "wizard_working"
                                    )
                                    return

                    this_client.remove_cell_grippers()
                    return

                # no deep copy, let's select this object
                this_client.grip_object(
                    x=data["coordinates"]["x"],
                    y=data["coordinates"]["y"],
                    block_size=data["coordinates"]["block_size"],
                    board="wizard_working",
                )


        @self.sio.event
        def command(data):
            """Parse user commands."""

            logging.debug(f"Received a user command: {data}")

            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if user_id == self.user:
                logging.debug(f"user_id == self.user, returning")
                return
            
            # commands from the user
            if isinstance(data["command"], dict):
                # commands received from the frontend
                event = data["command"]["event"]
                this_client = self.golmi_client
                # clear board
                if event == "clear_board":
                    this_client.clear_state("wizard_working")

                elif event == "next_board":
                    data_to_save = {
                        "message": f"user moved to next target board",
                    }
                    self.log_event("user_instruction", data_to_save, room_id)
                    message_color = STANDARD_COLOR

                    self.sio.emit(
                                    "text",
                                    {
                                        "room": room_id,
                                        "message": COLOR_MESSAGE.format(
                                            color=message_color, message=f"Taking you to next board.."
                                        ),
                                        "receiver_id": user_id,
                                        "html": True,
                                    },
                                    callback=self.message_callback,
                                )
                    logging.debug(f"Loading next target instruction for room_id: {room_id}, user_id: {user_id}")
                    self.load_target_instruction(room_id, user_id)                                       

if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = CCBTSReconstructionBot.create_argparser()
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
    ccbtsreconst_bot = CCBTSReconstructionBot(args.token, args.user, args.task, args.host, args.port)
    ccbtsreconst_bot.post_init(args.waiting_room, args.golmi_server, args.golmi_password)
    # connect to chat server
    ccbtsreconst_bot.run()
