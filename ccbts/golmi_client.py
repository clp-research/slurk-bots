import argparse
import json
import logging
import requests
import socketio


class DoubleClient:
    def __init__(self, room_id, golmi_address):
        self.golmi_address = golmi_address
        self.room_id = room_id
        self.target = GolmiClient()
        self.working = GolmiClient()

    def run(self, auth):
        self.target.run(self.golmi_address, f"{self.room_id}_t", auth)
        self.working.run(self.golmi_address, f"{self.room_id}_w", auth)

    def disconnect(self):
        for socket in [self.target, self.working]:
            socket.disconnect()

    def load_config(self, config):
        for socket in [self.target, self.working]:
            socket.load_config(config)

    def load_target_state(self, state):
        self.target.load_state(state)

    def load_working_state(self, state):
        self.working.load_state(state)

    def get_working_state(self):
        req = requests.get(
            f"{self.golmi_address}/slurk/{self.room_id}_w/state"
        )
        if req.ok is not True:
            print("Could not retrieve state")

        return req.json()

    def grip_object(self, x, y, block_size):
        req = requests.get(
            f'{self.golmi_address}/slurk/grip/{self.room_id}_w/{x}/{y}/{block_size}'
        )
        if req.ok is not True:
            print("Could not retrieve gripped piece")

        return req.json()

    def get_gripped_object(self):
        req = requests.get(
            f'{self.golmi_address}/slurk/{self.room_id}_w/gripped'
        )
        return req.json() if req.ok else None




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