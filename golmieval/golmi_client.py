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
    def __init__(self, address, slurk_socket, room_id):
        self.socket = socketio.Client()
        self.address = address
        self.room_id = room_id
        self.slurk_socket = slurk_socket
        self.history = list()

    # def call_backs(self):
    #     @self.socket.on("joined_room")
    #     def receive(data):
    #         self.slurk_socket.emit(
    #             "text", {"message": "joined", "room": self.room_id, "html": True}
    #         )

    #     @self.socket.on("update_config")
    #     def update_config(data):
    #         self.slurk_socket.emit(
    #             "text", {"message": "update config", "room": self.room_id, "html": True}
    #         )

    #     @self.socket.on("update_state")
    #     def update_state(data):
    #         self.state = data
    #         self.slurk_socket.emit(
    #             "text", {"message": "update_state", "room": self.room_id, "html": True}
    #         )

    #     @self.socket.on("update_objs")
    #     def update_objs(data):
    #         self.state["objs"] = data

    #     @self.socket.on("update_grippers")
    #     def update_grippers(data):
    #         self.state["grippers"] = data

    #         for gripper in data.values():
    #             if gripper["gripped"] != None:
    #                 for idn, obj in gripper["gripped"].items():
    #                     self.state["objs"][idn] = obj

    def run(self, auth):
        # self.call_backs()
        self.socket.connect(self.address, auth={"password": auth})
        self.socket.call("join", {"room_id": self.room_id})

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
