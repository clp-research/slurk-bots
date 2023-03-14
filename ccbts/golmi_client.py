import argparse
import json
import logging
import requests
import socketio


class DoubleClient:
    def __init__(self):
        self.target = GolmiClient()
        self.working = GolmiClient()

    def run(self, address, room_id, auth):
        self.target.run(address, f"{room_id}_t", auth)
        self.working.run(address, f"{room_id}_s", auth)

    def disconnect(self):
        for socket in [self.target, self.working]:
            socket.disconnect()

    def load_config(self, config):
        for socket in [self.target, self.working]:
            socket.load_config(config)

    def load_state(self, state):
        # only source can load a state
        self.target.load_state(state)
        # self.target.load_state(state)


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