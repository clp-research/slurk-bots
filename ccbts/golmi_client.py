import argparse
import json
import logging
from dataclasses import dataclass, asdict

import requests
import socketio

from .config import EMPTYSTATE, SELECTIONSTATE


@dataclass
class Rooms:
    target: str
    player_working:  str
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
        self.player_working = GolmiClient()
        self.wizard_working = GolmiClient()
        self.selector = GolmiClient()
        self.rooms = Rooms(
            target=f"{self.room_id}_t",
            player_working=f"{self.room_id}_pw",
            wizard_working=f"{self.room_id}_ww",
            selector=f"{self.room_id}_selector"
        )

    def run(self, auth):
        self.target.run(
            self.golmi_address,
            self.rooms.target,
            auth
        )
        self.player_working.run(
            self.golmi_address,
            self.rooms.player_working,
            auth
        )
        self.wizard_working.run(
            self.golmi_address,
            self.rooms.wizard_working,
            auth
        )
        self.selector.run(
            self.golmi_address,
            self.rooms.selector,
            auth
        )

    def disconnect(self):
        sockets = [
            self.target,
            self.wizard_working,
            self.player_working,
            self.selector
        ]
        for socket in sockets:
            socket.disconnect()

    def load_config(self, config):
        sockets = [
            self.target,
            self.wizard_working,
            self.player_working
        ]
        for socket in sockets:
            socket.load_config(config)

        self.selector.load_config(
            {
                "width": 10.0,
                "height": 10.0,
                "move_step": 1,
                "prevent_overlap": False
            }
        )

    def clear_working_state(self):
        self.wizard_working.load_state(EMPTYSTATE)

    def clear_working_states(self):
        self.wizard_working.load_state(EMPTYSTATE)
        self.player_working.load_state(EMPTYSTATE)

    def copy_working_state(self):
        state = self.get_working_state()
        self.player_working.load_state(state)

    def load_selector(self):
        self.selector.load_state(SELECTIONSTATE)

    def load_target_state(self, state):
        self.target.load_state(state)

    def load_working_state(self, state):
        self.wizard_working.load_state(state)

    def get_working_state(self):
        req = requests.get(
            f"{self.golmi_address}/slurk/{self.rooms.wizard_working}/state"
        )
        if req.ok is not True:
            print("Could not retrieve state")

        return req.json()

    def grip_object(self, x, y, block_size):
        req = requests.get(
            f'{self.golmi_address}/slurk/grip/{self.rooms.wizard_working}/{x}/{y}/{block_size}'
        )
        if req.ok is not True:
            print("Could not retrieve gripped piece")

        return req.json()

    def wizard_select_object(self, x, y, block_size):
        req = requests.get(
            f'{self.golmi_address}/slurk/grip/{self.rooms.selector}/{x}/{y}/{block_size}'
        )
        if req.ok is not True:
            print("Could not retrieve gripped piece")

    def get_gripped_object(self):
        req = requests.get(
            f'{self.golmi_address}/slurk/{self.rooms.wizard_working}/gripped'
        )
        return req.json() if req.ok else None

    def get_wizard_selection(self):
        req = requests.get(
            f'{self.golmi_address}/slurk/{self.rooms.selector}/gripped'
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

    def delete_object(self, obj):
        """
        only wizard can add an object to his working
        """
        response = requests.delete(
            f"{self.golmi_address}/slurk/{self.rooms.wizard_working}/object",
            json=obj,
        )
        if not response.ok:
            logging.error(f"Could not post new object: {response.status_code}")
            response.raise_for_status()

    def remove_selection(self):
        response = requests.delete(
            f"{self.golmi_address}/slurk/gripper/{self.rooms.selector}/mouse"
        )
        if not response.ok:
            logging.error(f"Could not post new object: {response.status_code}")
            response.raise_for_status()


class GolmiClient:
    def __init__(self):
        self.socket = socketio.Client()

    def run(self, address, room_id, auth):
        self.socket.connect(address, auth={"password": auth})
        self.socket.call("join", {"room_id": room_id})

    def random_init(self, random_config):
        self.socket.emit("random_init", random_config)

    def load_config(self, config):
        self.socket.emit("load_config", config)

    def update_config(self, config):
        self.socket.emit("update_config", config)

    def disconnect(self):
        self.socket.emit("disconnect")
        self.socket.disconnect()

    def load_state(self, state):
        self.socket.emit("load_state", state)

    def emit(self, *args, **kwargs):
        self.socket.emit(*args, **kwargs)
