import argparse
import json
import logging
import requests
import socketio

from .config import *


class GolmiClient:
    def __init__(self, slurk_socket, bot, room_id):
        self.socket = socketio.Client()
        self.demo_socket = socketio.Client()
        self.slurk_socket = slurk_socket
        self.room_id = room_id
        self.bot = bot
        if bot.version == "show_gripper":
            self.register_callbacks()

    def register_callbacks(self):
        @self.socket.event
        def update_state(data):
            grippers = data["grippers"]
            if not grippers:
                return

            piece = list(grippers.values())[0]["gripped"]
            gripper = list(grippers.values())[0]
            if piece is None:
                # record movement, no object was gripped
                self.bot.log_event(
                    "gripper_movement",
                    {
                        "coordinates": {
                            "x": gripper["x"],
                            "y": gripper["y"]
                        }
                    },
                    self.room_id
                )
            else:
                coordinates = dict(
                    type="gripper",
                    x=gripper["x"],
                    y=gripper["y"]
                )
                self.bot.piece_selection(self.room_id, piece, coordinates)

    def run(self, address, room_id, auth):
        self.socket.connect(address, auth={"password": auth})
        self.socket.call("join", {"room_id": room_id})

        self.demo_socket.connect(address, auth={"password": auth})
        self.socket.call("join", {"room_id": f"{room_id}_demo"})
        self.socket.emit("load_config", DEMO_BOARD["config"])
        self.socket.emit("load_state", DEMO_BOARD["state"])

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
