import argparse
import logging
import os

import requests
import socketio


LOG = logging.getLogger(__name__)


class EchoBot:
    sio = socketio.Client(logger=True)
    task_id = None

    def __init__(self, token, user, host, port):
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"

        LOG.info(f"Running echo bot on {self.uri} with token {self.token}")
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

    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            self.user = data["user"]

        @self.sio.event
        def new_task_room(data):
            room_id = data["room"]
            task_id = data["task"]
            if self.task_id is None or task_id == self.task_id:
                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if not response.ok:
                    LOG.error(f"Could not let echo bot join room: {response.status_code}")
                    response.raise_for_status()
                LOG.debug("Echo bot joins new task room", data)

        @self.sio.event
        def text_message(data):
            sender_id = data["user"]["id"]
            if self.user is not None and self.user == sender_id:
                return

            LOG.debug(f"I got a message, let's send it back!: {data}")

            message = data["message"]
            if message.lower() == "hello":
                message = "World!"
            if message.lower() == "ping":
                message = "Pong!"

            if not data["private"]:
                self.sio.emit(
                    "text",
                    {"room": data["room"], "message": message},
                    callback=self.message_callback
                )
            else:
                LOG.debug("It was actually a private message o.O")
                self.sio.emit(
                    "text",
                    {
                        "room": data["room"],
                        "receiver_id": data["user"]["id"],
                        "message": message
                    },
                    callback=self.message_callback
                )

        @self.sio.event
        def image_message(data):
            sender_id = data["user"]["id"]
            if self.user is not None and self.user == sender_id:
                return

            LOG.debug(f"I got an image, let's send it back!: {data}")

            if not data["private"]:
                self.sio.emit(
                    "image",
                    {
                        "room": data["room"],
                        "url": data["url"],
                        "width": data["width"],
                        "height": data["height"]
                    },
                    callback=self.message_callback
                )
            else:
                LOG.debug("It was actually a private message o.O")
                self.sio.emit(
                    "image",
                    {
                        "room": data["room"],
                        "receiver_id": data["user"]["id"],
                        "url": data["url"],
                        "width": data["width"],
                        "height": data["height"]
                    },
                    callback=self.message_callback
                )


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = argparse.ArgumentParser(description="Run Echo Bot.")

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
    task_id = {"default": os.environ.get("ECHO_TASK_ID")}

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
    echo_bot = EchoBot(args.token, args.user, args.host, args.port)
    echo_bot.task_id = args.task_id
    # connect to chat server
    echo_bot.run()
