import argparse
import json
import logging
import requests
import socketio


class GolmiClient:
    def __init__(self, slurk_socket, bot, room_id):
        self.socket = socketio.Client()
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
            if piece is None:
                # record movement, no object was gripped
                gripper = list(grippers.values())[0]
                self.bot.add_to_log(
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
                logging.debug("-------------")
                logging.debug(piece)
                logging.debug(grippers)
                self.bot.piece_selection(self.room_id, piece)

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
