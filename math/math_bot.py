import ast
import argparse
import logging
import os
from pathlib import Path
import re
from threading import Timer

import requests
import socketio


LOG = logging.getLogger(__name__)


TASK_TITLE = "Let's solve some math!"
TASK_DESCR = Path("task_description.txt").read_text()
IMG_LINK = "https://upload.wikimedia.org/wikipedia/commons/a/a2/Nuvola_Math_and_Inf.svg"
TIMEOUT_TIMER = 60  # minutes


class RoomTimer:
    def __init__(self, time, function, room_id):
        self.function = function
        self.time = time
        self.room_id = room_id
        self.start_timer()

    def start_timer(self):
        self.timer = Timer(self.time*60, self.function, args=[self.room_id])
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.debug("reset timer")

    def cancel(self):
        self.timer.cancel()


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

        self.room_to_q = dict()
        self.timers_per_room = dict()

        LOG.info(f"Running math bot on {self.uri} with token {self.token}")
        # register all event handlers
        self.register_callbacks()

    def run(self):
        """Establish a connection to the server."""
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": str(self.user)},
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
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    LOG.error(
                        f"Could not let math bot join room: {response.status_code}"
                    )
                    response.raise_for_status()
                LOG.debug("Math bot joins new task room", data)

                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr",
                    json={"text": TASK_DESCR},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr_title",
                    json={"text": TASK_TITLE},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/current-image",
                    json={"attribute": "src", "value": IMG_LINK},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.timers_per_room[room_id] = RoomTimer(
                    TIMEOUT_TIMER, self.close_game, room_id
                )

        @self.sio.event
        def text_message(data):
            """load next state after the user enters a description"""
            if self.user == data["user"]["id"]:
                return

            room_id = data["room"]
            self.timers_per_room[room_id].reset()

        @self.sio.event
        def command(data):
            """Process question and answer turns for both parties."""

            room_id = data["room"]
            user_id = data["user"]["id"]
            cmd = data["command"]

            # reset timer
            if self.user != data["user"]["id"]:
                self.timers_per_room[room_id].reset()

            if cmd.startswith("question"):
                self._set_question(room_id, user_id, cmd)
            elif cmd.startswith("answer"):
                self._give_answer(room_id, user_id, cmd)
            else:
                # inform the user in case of an invalid command
                self.sio.emit(
                    "text",
                    {
                        "message": f"`{cmd}` is not a valid command.",
                        "room": room_id,
                        "receiver_id": user_id,
                    },
                    callback=self.message_callback,
                )

    def _set_question(self, room_id, user_id, cmd):
        question = re.sub(r"^question\s*", "", cmd)
        solution = self._eval(question)

        if solution is None:
            self.sio.emit(
                "text",
                {
                    "message": "Questions must be mathematical expressions.",
                    "room": room_id,
                    "receiver_id": user_id,
                },
                callback=self.message_callback,
            )
        else:
            self.room_to_q[room_id] = {
                "question": question,
                "solution": solution,
                "sender": user_id,
            }
            self.sio.emit(
                "text",
                {
                    "message": f"A new question has been created:\n{question}",
                    "room": room_id,
                },
                callback=self.message_callback,
            )

    def _give_answer(self, room_id, user_id, cmd):
        answer = re.sub(r"^answer\s*", "", cmd)
        prop_solution = self._eval(answer, answer=True)

        if room_id not in self.room_to_q:
            self.sio.emit(
                "text",
                {
                    "message": "Oops, no question found you could answer!",
                    "room": room_id,
                    "receiver_id": user_id,
                },
                callback=self.message_callback,
            )
        elif self.room_to_q[room_id]["sender"] == user_id:
            self.sio.emit(
                "text",
                {
                    "message": "Come on! Don't answer your own question.",
                    "room": room_id,
                    "receiver_id": user_id,
                },
                callback=self.message_callback,
            )
        elif prop_solution is None:
            self.sio.emit(
                "text",
                {
                    "message": "What? Sure that's a number?",
                    "room": room_id,
                    "receiver_id": user_id,
                },
                callback=self.message_callback,
            )
        else:
            self.sio.emit(
                "text",
                {"message": f"The proposed answer is: {answer}", "room": room_id},
                callback=self.message_callback,
            )
            if prop_solution == self.room_to_q[room_id]["solution"]:
                self.sio.emit(
                    "text",
                    {"message": "Wow! That's indeed correct.", "room": room_id},
                    callback=self.message_callback,
                )
                self.room_to_q.pop(room_id)
            else:
                self.sio.emit(
                    "text",
                    {"message": "Naahh. Try again!", "room": room_id},
                    callback=self.message_callback,
                )

    @staticmethod
    def _eval(expr, answer=False):
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError:
            return
        # verify the expression
        for node in ast.walk(tree.body):
            if not isinstance(
                node,
                (
                    ast.Num,
                    ast.Sub,
                    ast.Add,
                    ast.Mult,
                    ast.BinOp,
                    ast.USub,
                    ast.UnaryOp,
                    ast.Div,
                    ast.FloorDiv,
                    ast.Pow,
                ),
            ):
                return
            # an answer should not be a complex formula
            if answer and not isinstance(node, (ast.Num, ast.USub, ast.UnaryOp)):
                return
        return eval(expr)

    def close_game(self, room_id):
        self.room_to_read_only(room_id)
        self.timers_per_room.pop(room_id)
        if room_id in self.room_to_q:
            self.room_to_q.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()

        response = requests.get(
            f"{self.uri}/rooms/{room_id}/users",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not get user: {response.status_code}")

        users = response.json()
        for user in users:
            response = requests.get(
                f"{self.uri}/users/{user['id']}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                logging.error(f"Could not get user: {response.status_code}")
                response.raise_for_status()
            etag = response.headers["ETag"]

            response = requests.delete(
                f"{self.uri}/users/{user['id']}/rooms/{room_id}",
                headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                logging.error(
                    f"Could not remove user from task room: {response.status_code}"
                )
                response.raise_for_status()
            logging.debug("Removing user from task room was successful.")

    def close_game(self, room_id):
        self.room_to_read_only(room_id)
        self.timers_per_room.pop(room_id)
        if room_id in self.room_to_q:
            self.room_to_q.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()

        response = requests.get(
            f"{self.uri}/rooms/{room_id}/users",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not get user: {response.status_code}")

        users = response.json()
        for user in users:
            response = requests.get(
                f"{self.uri}/users/{user['id']}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                logging.error(f"Could not get user: {response.status_code}")
                response.raise_for_status()
            etag = response.headers["ETag"]

            response = requests.delete(
                f"{self.uri}/users/{user['id']}/rooms/{room_id}",
                headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                logging.error(
                    f"Could not remove user from task room: {response.status_code}"
                )
                response.raise_for_status()
            logging.debug("Removing user from task room was successful.")


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
    parser.add_argument("-u", "--user", type=int, help="user id for the bot", **user)
    parser.add_argument("-u", "--user", type=int, help="user id for the bot", **user)
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
