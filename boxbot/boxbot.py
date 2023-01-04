import argparse
import json
import logging
import os
import random
from threading import Timer

import requests
import socketio


ROOT = os.path.dirname(os.path.abspath(__file__))
TIMEOUT_TIMER = 60  # minutes
LOG = logging.getLogger(__name__)


class RoomTimer:
    def __init__(self, function, room_id, game):
        self.function = function
        self.room_id = room_id
        self.game = game
        self.start_timer()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER*60,
            self.function,
            args=[self.room_id, self.game]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        LOG.info("reset timer")

    def cancel(self):
        self.timer.cancel()


class Game:
    def __init__(self, items):
        self.running = False
        self.correct_answers = 0
        self.total_answers = len(items)

        self.items = items
        self.current_item = None


class BoxBot:
    sio = socketio.Client(logger=True)
    task_id = None

    def __init__(self, token, user, host, port, data_path):
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"

        self.game_per_room = dict()
        with open(data_path, "r", encoding="utf-8") as f:
            self.all_items = json.load(f)

        LOG.info(f"Running box bot on {self.uri} with token {self.token}")
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

    @staticmethod
    def request_feedback(response, action):
        if not response.ok:
            LOG.error(f"Could not {action}: {response.status_code}")
            response.raise_for_status()

    def register_callbacks(self):
        @self.sio.event
        def new_task_room(data):
            room_id = data["room"]

            if self.task_id is None or data["task"] == self.task_id:
                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "let box bot join room")

                # create new game instance
                item_ids = list(self.all_items.keys())
                random.shuffle(item_ids)
                self.game_per_room[room_id] = Game(item_ids)
                game = self.game_per_room.get(room_id)
                self.timers_per_room[room_id] = RoomTimer(
                    self.close_game, room_id, game
                )

                # greet user
                for usr in data["users"]:
                    self.sio.emit(
                        "text",
                        {
                            "message": f"Hello {usr['name']}. Please click "
                            "on <Start> once you are ready!",
                            "room": room_id,
                        },
                        callback=self.message_callback,
                    )
                    self.sio.emit(
                        "text",
                        {
                            "message": "Your task will be to draw a box around "
                            "the object that matches the audio "
                            "description.",
                            "room": room_id,
                        },
                        callback=self.message_callback,
                    )

        @self.sio.event
        def command(data):
            room_id = data["room"]
            game = self.game_per_room.get(room_id)

            # reset if the command does not come from the bot
            if self.user != data["user"]["id"]:
                self.timers_per_room[room_id].reset()

            if game is None:
                return
            if data["command"] not in {"start", "next"}:
                self.sio.emit(
                    "text",
                    {"message": "I do not understand this command.", "room": room_id},
                    callback=self.message_callback,
                )
                return
            if data["command"] == "next" and not game.running:
                self.sio.emit(
                    "text",
                    {"message": "You should start the game first", "room": room_id},
                    callback=self.message_callback,
                )
                return

            if data["command"] == "start":
                game.running = True
                # hide start button
                response = requests.post(
                    f"{self.uri}/rooms/{room_id}/class/start-button",
                    json={"class": "dis-button"},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "hide start button")

                # enable next button
                response = requests.delete(
                    f"{self.uri}/rooms/{room_id}/class/next-button",
                    json={"class": "dis-button"},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "enable next button")

            self.get_new_item(room_id, game)

            if game.current_item is not None:
                self.display_item(room_id, game.current_item)
                # set text to 'skip' while item unanswered
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/next-button",
                    json={"text": "Skip>"},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "set text of button")
            else:
                self.close_game(room_id, game)

        @self.sio.event
        def bounding_box(data):
            room_id = data["room"]
            game = self.game_per_room.get(room_id)

            if game is None or game.current_item is None:
                return

            # check if player selected the correct area
            if data["type"] == "add":
                if self.is_box_around_target(game.current_item, data["coordinates"]):
                    game.correct_answers += 1
                    game.current_item = None
                    self.sio.emit(
                        "text",
                        {"message": "That was correct!", "room": room_id},
                        callback=self.message_callback,
                    )
                    response = requests.patch(
                        f"{self.uri}/rooms/{room_id}/text/next-button",
                        json={"text": "Next>"},
                        headers={"Authorization": f"Bearer {self.token}"},
                    )
                    self.request_feedback(response, "set text of button")
                else:
                    self.sio.emit(
                        "text",
                        {"message": "Try again!", "room": room_id},
                        callback=self.message_callback,
                    )

    def get_new_item(self, room_id, game):
        # select new item if some remaining
        if game.items:
            item_id = game.items.pop()
            item = self.all_items[item_id]
            game.current_item = item
        else:
            game.current_item = None

    def display_item(self, room_id, item):
        # set image
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/drawing-area",
            json={"attribute": "src", "value": item.get("image_filename", "")},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set image")
        # set audio
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/audio-file",
            json={"attribute": "src", "value": item.get("audio_filename", "")},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set audio")

    def close_game(self, room_id, game):
        game.running = False
        # clear display area
        self.sio.emit(
            "text",
            {"message": "You have answered all items.", "room": room_id},
            callback=self.message_callback,
        )
        self.sio.emit(
            "text",
            {
                "message": f"You got {game.correct_answers} "
                f"out of {game.total_answers} correct.",
                "room": room_id,
            },
            callback=self.message_callback,
        )
        self.display_item(room_id, {})
        # hide button
        response = requests.post(
            f"{self.uri}/rooms/{room_id}/class/next-button",
            json={"class": "dis-button"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "hide button")
        self.room_to_read_only(room_id)
        self.timers_per_room.pop(room_id)
        self.game_per_room.pop(room_id)

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
            if user["id"] != self.user:
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

    def is_box_around_target(self, item, box):
        left_item, top_item, right_item, bottom_item = item["bb"]

        # works reasonably well for the shape task but might have to be adjusted
        # for other comparisons, maybe implement overlap instead of inclusion
        if (
            left_item <= box["left"]
            and right_item >= box["right"]
            and top_item <= box["top"]
            and bottom_item >= box["bottom"]
        ):
            return True
        return False


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = argparse.ArgumentParser(description="Run Box Bot.")

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

    if "BOX_DATA" in os.environ:
        data = {"default": os.environ["BOX_DATA"]}
    else:
        data = {"required": True}
    task_id = {"default": os.environ.get("BOX_TASK_ID")}

    # register commandline arguments
    parser.add_argument(
        "-t", "--token", help="token for logging in as bot", **token
    )
    parser.add_argument("-u", "--user", type=int, help="user id for the bot", **user)
    parser.add_argument(
        "-c", "--host", help="full URL (protocol, hostname) of chat server", **host
    )
    parser.add_argument("-p", "--port", type=int, help="port of chat server", **port)

    parser.add_argument("--data", help="json file containing experiment items", **data)
    parser.add_argument("--task_id", type=int, help="task to join", **task_id)

    args = parser.parse_args()

    # create bot instance
    box_bot = BoxBot(args.token, args.user, args.host, args.port, args.data)
    box_bot.task_id = args.task_id

    # connect to chat server
    box_bot.run()
