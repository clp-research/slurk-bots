import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import pickle
import socketio
import time
import logging


class MyCustomNamespace(socketio.AsyncNamespace):
    async def trigger_event(self, event_name, sid, *args):
        print(f"{event_name=}, {sid=}")
        if args:
            print(f"data is {args[0]}")



class GolmiClient:
    def __init__(self, slurk_socket):
        self.socket = socketio.Client()
        self.slurk_socket = slurk_socket

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
