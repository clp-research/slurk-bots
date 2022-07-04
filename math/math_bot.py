import ast
import argparse
import logging
from math import *
import os
from pathlib import Path
import re

import requests
import socketio


LOG = logging.getLogger(__name__)


TASK_TITLE = "Let's solve some math!"
TASK_DESCR = Path("task_description.txt").read_text()
IMG_LINK = "https://upload.wikimedia.org/wikipedia/commons/a/a2/Nuvola_Math_and_Inf.svg"


class MathBot:
    sio = socketio.Client(logger=True)
    task_id = None

    def __init__(self, token, user, host, port):
        """
        Two parties ask each other simple math questions
        and the bot checks the correct answer.
        """
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"

        self.questions = dict()

        LOG.info(f"Running math bot on {self.uri} with token {self.token}")
        # register all event handlers
        self.register_callbacks()

    def run(self):
        """Establish a connection to the server."""
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": self.user},
            namespaces="/",
        )
        # wait until the connection with the server ends
        self.sio.wait()

    @staticmethod
    def message_callback(success, error_msg="Unknown Error"):
        """Verify whether an emit was succesful."""
        if not success:
            LOG.error(f"Could not send message: {error_msg}")
            exit(1)
        LOG.debug("Sent message successfully.")

    def register_callbacks(self):
        @self.sio.event
        def new_task_room(data):
            """Join the room when the task matches the ID."""
            room_id = data["room"]
            task_id = data["task"]
            if self.task_id is None or task_id == self.task_id:
                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if not response.ok:
                    LOG.error(f"Could not let math bot join room: {response.status_code}")
                    response.raise_for_status()
                LOG.debug("Math bot joins new task room", data)

                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr",
                    json={"text": TASK_DESCR},
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr_title",
                    json={"text": TASK_TITLE},
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/current-image",
                    json={"attribute": "src", "value": IMG_LINK},
                    headers={"Authorization": f"Bearer {self.token}"}
                )

        @self.sio.event
        def command(data):
            """Process question and answer turns for both parties."""
            room_id = data["room"]
            user_id = data["user"]["id"]
            if data["command"].startswith("question"):
                self.sio.emit(
                    "text",
                    {"message": "You have sent a question.",
                     "room": room_id,
                     "receiver_id": user_id},
                    callback=self.message_callback
                )
                self._command_question(user_id, room_id, data["command"])
            elif data["command"].startswith("answer"):
                self.sio.emit(
                    "text",
                    {"message": "You have sent an answer.",
                     "room": room_id,
                     "receiver_id": user_id},
                    callback=self.message_callback
                )
                self._command_answer(user_id, room_id, data["command"])
            else:
                self.sio.emit(
                    "text",
                    {"message": f"`{data['command']}` is not a valid command.",
                     "room": room_id,
                     "receiver_id": user_id},
                    callback=self.message_callback
                )

    def _command_question(self, user_id, room_id, command):
        """Broadcast math question to the room."""
        query = re.sub(r"^question\s*", "", command)

        try:
            # try to parse the input from user into a math formula
            tree = ast.parse(query, mode='eval')
            if not isinstance(tree.body, ast.BinOp):
                raise SyntaxError

            co = compile(tree, filename='<string>', mode='eval')
            self.questions[room_id] = co
            self.questions["sender"] = user_id

            self.sio.emit(
                "text",
                {"message": "A math question has been created!",
                "room": room_id},
                callback=self.message_callback
            )
            self.sio.emit(
                "text",
                {"message": query,
                "room": room_id},
                callback=self.message_callback
            )

        except (SyntaxError, NameError):
            # user input is malformed, inform user
            self.sio.emit(
                "text",
                {"message": "Your question is malformed, please try again",
                 "room": room_id,
                 "receiver_id": user_id},
                callback=self.message_callback
            )

    def _command_answer(self, user_id, room_id, command):
        """Check if the provided answer is correct."""
        answer = re.sub(r"^answer\s*", "", command)

        try:
            # only proceed if the user entered a number as an answer
            answer = float(answer)
            if room_id not in self.questions:
                self.sio.emit(
                    "text",
                    {"message": "Oops, no question found that you could answer!",
                    "room": room_id,
                    "receiver_id": user_id},
                    callback=self.message_callback
                )
                return
            if self.questions["sender"] != user_id:
                self.sio.emit(
                    "text",
                    {"message": f"The proposed answer is: {answer}",
                    "room": room_id},
                    callback=self.message_callback
                )
                if eval(self.questions[room_id]) == answer:
                    self.sio.emit(
                        "text",
                        {"message": "Turns out the answer is correct!",
                        "room": room_id},
                        callback=self.message_callback
                    )
                else:
                    self.sio.emit(
                        "text",
                        {"message": "Unfortunately the answer is wrong.",
                        "room": room_id},
                        callback=self.message_callback
                    )
                    self.sio.emit(
                        "text",
                        {"message": "Please try again!",
                        "room": room_id,
                        "receiver_id": user_id},
                        callback=self.message_callback
                    )
            else:
                self.sio.emit(
                    "text",
                    {"message": "Come on! Don't answer your own question.",
                    "room": room_id,
                    "receiver_id": user_id},
                    callback=self.message_callback
                )

        # invalid input, inform the user the input is malformed
        except ValueError:
            self.sio.emit(
                "text",
                {"message": "Your answer is malformed, please try again",
                 "room": room_id,
                 "receiver_id": user_id},
                callback=self.message_callback
            )



if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = argparse.ArgumentParser(description="Run Math Bot.")

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
    task_id = {"default": os.environ.get("MATH_TASK_ID")}

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
    math_bot = MathBot(args.token, args.user, args.host, args.port)
    math_bot.task_id = args.task_id
    # connect to chat server
    math_bot.run()
