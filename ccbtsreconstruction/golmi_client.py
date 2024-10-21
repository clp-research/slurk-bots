import logging
from dataclasses import dataclass, asdict

import requests
import socketio

from .config import EMPTYSTATE, SELECTIONSTATE


class GolmiClient:
    def __init__(self):
        logging.debug(f"Inside GolmiClient __init__")
        self.socket = socketio.Client()

    def run(self, address, room_id, auth):
        logging.debug(f"Inside GolmiClient run, address: {address}, room_id: {room_id}, auth: {auth}")
        self.socket.connect(address, auth={"password": auth})
        self.socket.call("join", {"room_id": room_id})

    def random_init(self, random_config):
        logging.debug(f"Inside GolmiClient random_init, random_config: {random_config}")
        self.socket.emit("random_init", random_config)

    def load_config(self, config):
        logging.debug(f"Inside GolmiClient load_config, config: {config}")
        self.socket.emit("load_config", config)

    def update_config(self, config):
        logging.debug(f"Inside GolmiClient update_config, config: {config}")
        self.socket.emit("update_config", config)

    def disconnect(self):
        logging.debug(f"Inside GolmiClient disconnect")
        self.socket.emit("disconnect")
        self.socket.disconnect()

    def load_state(self, state):
        logging.debug(f"Inside GolmiClient load_state, state: {state}")
        self.socket.emit("load_state", state)

    def emit(self, *args, **kwargs):
        logging.debug(f"Inside GolmiClient emit, args: {args}, kwargs: {kwargs}")
        self.socket.emit(*args, **kwargs)


@dataclass
class Rooms:
    target: str
    #player_working: str
    wizard_working: str
    selector: str

    @property
    def json(self):
        return asdict(self)


class QuadrupleClient:
    def __init__(self, room_id, golmi_address):
        self.golmi_address = golmi_address
        self.room_id = room_id
        self.target = GolmiClient()
        #self.player_working = GolmiClient()
        self.wizard_working = GolmiClient()
        self.selector = GolmiClient()
        self.rooms = Rooms(
            target=f"{self.room_id}_t",
            #player_working=f"{self.room_id}_pw",
            wizard_working=f"{self.room_id}_ww",
            selector=f"{self.room_id}_selector",
        )
        logging.debug(f"Inside QuadrupleClient __init__, room_id: {room_id}, golmi_address: {golmi_address}")

    def get_client(self, board):
        mapping = {
            "target": self.target,
            #"player_working": self.player_working,
            "wizard_working": self.wizard_working,
            "selector": self.selector
        }
        return mapping[board]

    def get_room_id(self, board):
        return asdict(self.rooms)[board]

    def run(self, auth):
        self.target.run(self.golmi_address, self.rooms.target, auth)
        #self.player_working.run(self.golmi_address, self.rooms.player_working, auth)
        self.wizard_working.run(self.golmi_address, self.rooms.wizard_working, auth)
        self.selector.run(self.golmi_address, self.rooms.selector, auth)
        logging.debug(f"Inside QuadrupleClient run, room_id: {self.room_id}, golmi_address: {self.golmi_address}")

    def disconnect(self):
        #sockets = [self.target, self.wizard_working, self.player_working, self.selector]
        sockets = [self.target, self.wizard_working, self.selector]
        for socket in sockets:
            socket.disconnect()

    def load_config(self, config):
        logging.debug(f"Inside QuadrupleClient load_config, config: {config}")
        sockets = [self.target, self.wizard_working]#, self.player_working]
        for socket in sockets:
            socket.load_config(config)

        self.selector.load_config(
            {"width": 10.0, "height": 10.0, "move_step": 1, "prevent_overlap": False}
        )

    def load_state(self, state, board):
        room = self.get_client(board)
        room.load_state(state)

    def clear_state(self, board):
        room = self.get_client(board)
        room.load_state(EMPTYSTATE)

    def get_state(self, board):
        room = self.get_room_id(board)
        req = requests.get(
            f"{self.golmi_address}/slurk/{room}/state"
        )
        if req.ok is not True:
            print("Could not retrieve state")

        return req.json()

    def copy_working_state(self):
        state = self.get_state("wizard_working")
        state["grippers"] = dict()
        #self.player_working.load_state(state)

    def grip_object(self, x, y, block_size, board):
        room = self.get_room_id(board)
        req = requests.get(
            f"{self.golmi_address}/slurk/grip/{room}/{x}/{y}/{block_size}"
        )
        if req.ok is not True:
            print("Could not retrieve gripped piece")

        return req.json()

    def get_gripped_object(self, board):
        room = self.get_room_id(board)
        req = requests.get(
            f"{self.golmi_address}/slurk/{room}/gripped"
        )
        return req.json() if req.ok else None

    def get_entire_cell(self, x, y, block_size, board):
        mapping = {
            "wizard_working": self.rooms.wizard_working,
            "target": self.rooms.target,
        }

        room = mapping[board]

        req = requests.get(
            f"{self.golmi_address}/slurk/cell/{room}/{x}/{y}/{block_size}"
        )
        return req.json() if req.ok else None

    def add_object(self, obj):
        """
        only wizard can add an object to his working
        """
        response = requests.post(
            f"{self.golmi_address}/slurk/{self.rooms.wizard_working}/object",
            json=obj,
        )
        if not response.ok:
            logging.error(f"Could not post new object: {response.status_code}")
            response.raise_for_status()
            return False, None

        return "add", obj

    def get_gripper(self, gripper_id, board):
        room = self.get_room_id(board)
        req = requests.get(
            f"{self.golmi_address}/slurk/gripper/{room}/{gripper_id}"
        )
        return req.json() if req.ok else None

    def remove_gripper(self, gripper_id, board):
        room = self.get_room_id(board)
        req = requests.delete(
            f"{self.golmi_address}/slurk/gripper/{room}/{gripper_id}"
        )
        return req.json() if req.ok else None

    def add_gripper(self, gripper, x, y, block_size, board):
        room = self.get_room_id(board)
        req = requests.post(
            f"{self.golmi_address}/slurk/gripper/{room}/{gripper}",
            json={"x": x, "y": y, "block_size": block_size}
        )
        return req.json() if req.ok else None

    def remove_cell_grippers(self):
        current_state = self.get_state("wizard_working")
        for gr_id in current_state["grippers"].keys():
            if "cell" in gr_id:
                req = requests.delete(
                    f"{self.golmi_address}/slurk/gripper/{self.rooms.wizard_working}/{gr_id}"
                )

    def delete_object(self, obj):
        """
        remove an object from the wizard working board
        """
        # bridges can span over 2 blocks, make sure that no
        # other piece is placed on this bridge
        if obj["type"] in {"vbridge", "hbridge"}:
            state = self.get_state("wizard_working")
            this_obj = obj["id_n"]
            for tile in state["objs_grid"].values():
                if this_obj in tile:
                    if tile[-1] != this_obj:
                        return False, None

        response = requests.delete(
            f"{self.golmi_address}/slurk/{self.rooms.wizard_working}/object",
            json=obj,
        )
        if not response.ok:
            logging.error(f"Could not post new object: {response.status_code}")
            response.raise_for_status()
            return False, None

        if "gripped" in obj:
            obj.pop("gripped")
        return "delete", obj

    def remove_selection(self, room, gripper_id):
        rooms = {
            "wizard_selection": self.rooms.selector,
            "wizard_working": self.rooms.wizard_working,
        }

        response = requests.delete(
            f"{self.golmi_address}/slurk/gripper/{rooms[room]}/{gripper_id}"
        )
        if not response.ok:
            logging.error(f"Could not post new object: {response.status_code}")
            response.raise_for_status()

    def get_mouse_gripper(self):
        req = requests.get(
            f"{self.golmi_address}/slurk/gripper/{self.rooms.wizard_working}/mouse"
        )
        return req.json() if req.ok else None
