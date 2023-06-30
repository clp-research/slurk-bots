import argparse
import logging
import os
from threading import Timer

import requests
import socketio


LOG = logging.getLogger(__name__)
TIMEOUT_TIMER = 60  # minutes
LEAVE_TIMER = 5  # minutes


class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()
        self.left_room = dict()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER*60,
            self.function,
            args=[self.room_id]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        LOG.info("reset timer")

    def cancel(self):
        self.timer.cancel()

    def user_joined(self, user):
        timer = self.left_room.get(user)
        if timer is not None:
            self.left_room[user].cancel()

    def user_left(self, user):
        self.left_room[user] = Timer(
            LEAVE_TIMER*60,
            self.function,
            args=[self.room_id, self.game]
        )
        self.left_room[user].start()


class InterventionBot:
    sio = socketio.Client(logger=True)
    task_id = None

    def __init__(self, token, user, host, port):
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"

        LOG.info(f"Running intervention bot on {self.uri} with token {self.token}")

        self.players_per_room = dict()
        self.timers_per_room = dict()

        # register all event handlers
        self.register_callbacks()

    def run(self):
        # establish a connection to the server
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": str(self.user)},
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
        def status(data):
            room_id = data["room"]
            if room_id in self.players_per_room:
                curr_usr, other_usr = self.players_per_room[room_id]
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr

                if data["type"] == "join":
                    # cancel timer
                    LOG.debug(
                        f"Cancelling Timer: left room for user {curr_usr['name']}"
                    )
                    self.timers_per_room[room_id].user_joined(curr_usr["id"])

                elif data["type"] == "leave":
                    self.timers_per_room[room_id].user_left(curr_usr["id"])

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
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    LOG.error(
                        f"Could not let intervention bot join room: {response.status_code}"
                    )
                    response.raise_for_status()
                LOG.debug("Intervention bot joins new task room", data)

                # keep track of users per room
                self.players_per_room[room_id] = []
                for usr in data["users"]:
                    self.players_per_room[room_id].append(
                        {**usr, "msg_n": 0, "status": "joined"}
                    )

                self.timers_per_room[room_id] = RoomTimer(
                    self.close_game, room_id
                )

        @self.sio.event
        def command(data):
            """Intercepts the user messages

            Anything that a user types will be intercepted by the bot who
            decides whether to change anything, just forward, or swallow.
            """
            LOG.debug(f"Received text from {data['user']['name']}: {data['command']}")

            room_id = data["room"]
            user_id = data["user"]["id"]

            if user_id != self.user:
                timer = self.timers_per_room.get(room_id)
                timer.reset()

            message = data["command"]
            for user in self.players_per_room[room_id]:
                if user["id"] == user_id:
                    user["msg_n"] += 1
                    # Let's do some message mangling, but only to every second message
                    if user["msg_n"] % 2 == 0:
                        message = message[::-1]
                        message = message.upper()

            # emit the message to all other users
            # (the user who sent will see the original; has already seen it)
            for user in self.players_per_room[room_id]:
                if user["id"] != user_id:
                    self.sio.emit(
                        "text",
                        {
                            "room": data["room"],
                            "receiver_id": user["id"],
                            "message": message,
                            "impersonate": user_id,
                        },
                        callback=self.message_callback,
                    )

    def close_game(self, room_id):
        self.room_to_read_only(room_id)
        self.timers_per_room.pop(room_id)
        self.players_per_room.pop(room_id)

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

        for user in self.players_per_room[room_id]:
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
    parser = argparse.ArgumentParser(description="Run Intervention Bot.")

    # collect environment variables as defaults
    if "BOT_TOKEN" in os.environ:
        token = {"default": os.environ["BOT_TOKEN"]}
    else:
        token = {"required": True}
    if "BOT_ID" in os.environ:
        user = {"default": os.environ["BOT_ID"]}
    else:
        user = {"required": True}
    host = {"default": os.environ.get("SLURK_HOST", "http://localhost")}
    port = {"default": os.environ.get("SLURK_PORT")}
    task_id = {"default": os.environ.get("TASK_ID")}

    # register commandline arguments
    parser.add_argument(
        "-t", "--token", help="token for logging in as bot", **token
    )
    parser.add_argument("-u", "--user", type=int, help="user id for the bot", **user)
    parser.add_argument(
        "-c", "--host", help="full URL (protocol, hostname) of chat server", **host
    )
    parser.add_argument("-p", "--port", type=int, help="port of chat server", **port)
    parser.add_argument("--task_id", type=int, help="task to join", **task_id)
    args = parser.parse_args()

    # create bot instance
    intervention_bot = InterventionBot(args.token, args.user, args.host, args.port)
    intervention_bot.task_id = args.task_id
    # connect to chat server
    intervention_bot.run()
