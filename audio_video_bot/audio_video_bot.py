import argparse
import json
import logging
import os
import random
import time

import requests
import socketio


ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = logging.getLogger(__name__)


class AudioVideoBot:
    sio = socketio.Client(logger=True)
    task_id = None

    def __init__(self, token, user, host, port):
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"

        LOG.info(f"Running audio video bot on {self.uri} with token {self.token}")
        # register all event handlers
        self.register_callbacks()

    def run(self):
        # establish a connection to the server
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": self.user},
            namespaces="/",
        )
        # wait until the connection with the server ends
        self.sio.wait()

    @staticmethod
    def message_callback(success, error_msg="Unknown Error"):
        if not success:
            LOG.error(f"Could not send message: {error_msg}")
            exit(1)
        LOG.debug("Sent message successfully.")

    @staticmethod
    def request_feedback(response, action):
        if not response.ok:
            LOG.error(f"Could not {action}: {response.status_code}")
            response.raise_for_status()

    def register_callbacks(self):
        @self.sio.event
        def new_task_room(data):
            LOG.debug(f"This bot is looking for task id: {self.task_id}")

            room_id = data["room"]
            task_id = data["task"]

            if self.task_id is None or task_id == self.task_id:
                LOG.debug("Sending bot to task room")
                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                self.request_feedback(response, "let audio video bot join room")

                # greet users
                for usr in data['users']:
                    self.sio.emit(
                        "text",
                        {"message": f"Hello {usr['name']}. Please click "
                                    "on <Start> once you are ready!",
                         "room": room_id,
                         "receiver_id": usr["id"]},
                        callback=self.message_callback
                    )

                self.sio.emit(
                    "text",
                    {"message": "A video and audio connection should "
                                "be established now. "
                                "If you are connecting both users from "
                                "the same computer and you have only one "
                                "camera, you might only be seeing one of "
                                "the users ",
                     "room": room_id},
                    callback=self.message_callback
                )

        @self.sio.event
        def command(data):
            room_id = data["room"]

            if data["command"] not in {"start"}:
                self.sio.emit(
                    "text",
                    {"message": "I do not understand this command.",
                     "room": room_id},
                    callback=self.message_callback
                )
                return

            if data["command"] == "start":
                # hide start button
                response = requests.post(
                    f"{self.uri}/rooms/{room_id}/class/start-button",
                    json={
                        "class": "dis-button",
                        "receiver_id": data['user']['id']
                        },
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                self.request_feedback(response, "hide start button")
                self.sio.emit(
                    "text",
                    {"message": f"Ok, let's start!",
                     "room": room_id,
                     "receiver_id": data['user']['id']},
                    callback=self.message_callback
                )

                session_id = requests.get(
                    f"{self.uri}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                ).json().get('openvidu_session_id')
                response = requests.post(
                    f"{self.uri}/openvidu/recordings/start/{session_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                self.request_feedback(response, "start a recording")
                file = response.json().get('')

        @self.sio.event
        def status(data):
            if data["type"] == "leave":
                # stop recording when a user leaves
                room_id = data["room"]
                session_id = requests.get(
                    f"{self.uri}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                ).json().get('openvidu_session_id')

                response = requests.post(
                    f"{self.uri}/openvidu/recordings/stop/{session_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                self.request_feedback(response, "stop the recording")

                # response = requests.get(
                #     f"{self.uri}/openvidu/recordings/download/{session_id}",
                #     headers={"Authorization": f"Bearer {self.token}"}
                # )
                # self.request_feedback(response, "download the recording")

if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = argparse.ArgumentParser(description="Run Audio Video Bot.")

    # collect environment variables as defaults
    if "SLURK_TOKEN" in os.environ:
        token = {"default": os.environ["SLURK_TOKEN"]}
    else:
        token = {"required": True}
    if "SLURK_USER" in os.environ:
        user = {"default": os.environ["SLURK_USER"]}
    else:
        user = {"required": True}
    host = {"default": os.environ.get("SLURK_HOST", "http://localhost")}
    port = {"default": os.environ.get("SLURK_PORT")}

    task_id = {"default": os.environ.get("AV_TASK_ID")}

    # register commandline arguments
    parser.add_argument(
        "-t", "--token", help="token for logging in as bot", **token
    )
    parser.add_argument("-u", "--user", help="user id for the bot", **user)
    parser.add_argument(
        "-c", "--host", help="full URL (protocol, hostname) of chat server", **host
    )
    parser.add_argument("-p", "--port", type=int, help="port of chat server", **port)

    parser.add_argument("--task_id", type=int, help="task to join", **task_id)

    args = parser.parse_args()

    # create bot instance
    bot = AudioVideoBot(args.token, args.user, args.host, args.port)
    bot.task_id = args.task_id

    # connect to chat server
    bot.run()
