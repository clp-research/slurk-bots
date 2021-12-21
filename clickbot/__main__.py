import argparse
import json
import logging
import os
import random

import requests

from templates import TaskBot


class Game:
    def __init__(self, items):
        self.running = False
        self.correct_answers = 0
        self.total_answers = len(items)

        self.items = items
        self.current_item = None


class ClickBot(TaskBot):
    def __init__(self, token, user, task, host, port, data):
        super().__init__(token, user, task, host, port)

        self.game_per_room = dict()
        self.all_items = json.load(data)

    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            room_id = data["room"]
            if room_id in self.game_per_room:
                return

            # create new game instance
            item_ids = list(self.all_items.keys())
            random.shuffle(item_ids)
            self.game_per_room[room_id] = Game(item_ids)

        @self.sio.event
        def status(data):
            room_id = data["room"]
            user_id = data["user"]["id"]

            if data["type"] == "join" and user_id != self.user:
                self.sio.emit(
                    "text",
                    {
                        "message": "Hello player. Please click "
                                   "on <Start> once you are ready!",
                        "room": room_id,
                    },
                    callback=self.message_callback,
                )
                self.sio.emit(
                    "text",
                    {
                        "message": "Your task will be to click on the object "
                                   "that matches the audio description.",
                        "room": room_id,
                    },
                    callback=self.message_callback,
                )

        @self.sio.event
        def command(data):
            room_id = data["room"]
            game = self.game_per_room.get(room_id)

            if game is None:
                return

            if data["command"] == "start":
                self.start_game(room_id, game)
            elif data["command"] == "next":
                if not game.running:
                    self.sio.emit(
                        "text",
                        {"message": "Start the game first.", "room": room_id},
                        callback=self.message_callback,
                    )
                    return
            else:
                self.sio.emit(
                    "text",
                    {"message": "I do not understand.", "room": room_id},
                    callback=self.message_callback,
                )
                return

            self.get_new_item(game)

            if game.current_item is not None:
                self.display_item(room_id, game.current_item)
            else:
                self.close_game(room_id, game)

        @self.sio.event
        def mouse(data):
            room_id = data["room"]
            game = self.game_per_room.get(room_id)

            if game is None or game.current_item is None:
                return

            # check if player selected the correct area
            if data["type"] == "click":
                if self.is_click_on_target(game.current_item, data["coordinates"]):
                    game.correct_answers += 1
                    game.current_item = None
                    self.sio.emit(
                        "text",
                        {"message": "That was correct!", "room": room_id},
                        callback=self.message_callback
                    )
                    response = requests.patch(
                        f"{self.uri}/rooms/{room_id}/text/next-button",
                        json={"text": "Next>"},
                        headers={"Authorization": f"Bearer {self.token}"}
                    )
                    self.request_feedback(response, "set text of button")
                else:
                    self.sio.emit(
                        "text",
                        {"message": "Try again!", "room": room_id},
                        callback=self.message_callback
                    )

    def get_new_item(self, game):
        # select new item if any remaining
        if game.items:
            item_id = game.items.pop()
            item = self.all_items[item_id]
            game.current_item = item
        else:
            game.current_item = None

    def display_item(self, room_id, item):
        # set image
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/tracking-area",
            json={
                "attribute": "src",
                "value": item.get("image_filename", "")
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.request_feedback(response, "set image")
        # set audio
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/audio-file",
            json={
                "attribute": "src",
                "value": item.get("audio_filename", "")
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.request_feedback(response, "set audio")
        # set button text to 'skip' for new item
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/next-button",
            json={"text": "Skip>"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.request_feedback(response, "set text of button")

    def start_game(self, room_id, game):
        game.running = True
        # hide start button
        response = requests.post(
            f"{self.uri}/rooms/{room_id}/class/start-button",
            json={"class": "dis-button"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.request_feedback(response, "hide start button")
        # enable next button
        response = requests.delete(
            f"{self.uri}/rooms/{room_id}/class/next-button",
            json={"class": "dis-button"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.request_feedback(response, "enable next button")

    def close_game(self, room_id, game):
        game.running = False
        # clear display area
        self.sio.emit(
            "text",
            {"message": "You have answered all items.", "room": room_id},
            callback=self.message_callback
        )
        self.sio.emit(
            "text",
            {
                "message": f"You got {game.correct_answers} "
                f"out of {game.total_answers} correct.",
                "room": room_id
            },
            callback=self.message_callback
        )
        self.display_item(room_id, {})
        # hide button
        response = requests.post(
            f"{self.uri}/rooms/{room_id}/class/next-button",
            json={"class": "dis-button"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.request_feedback(response, "hide button")

    def is_click_on_target(self, item, pos):
        left, top, right, bottom = item["bb"]
        if left <= pos["x"] <= right and bottom >= pos["y"] >= top:
            return True
        return False


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    default_parser = ClickBot.create_argparser()
    parser = argparse.ArgumentParser(
        description="Run ClickBot.", parents=[default_parser], add_help=False
    )
    if "CLICK_DATA" in os.environ:
        data = {"default": os.environ["CLICK_DATA"]}
    else:
        data = {"required": True}

    parser.add_argument(
        "-d", "--data", type=argparse.FileType("r", encoding="utf-8"),
        **data, help="json file containing experiment items",
    )
    args = parser.parse_args()

    # create bot instance
    click_bot = ClickBot(
        args.token, args.user, args.task, args.host, args.port, args.data
    )
    # connect to chat server
    click_bot.run()
