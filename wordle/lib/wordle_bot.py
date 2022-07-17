# -*- coding: utf-8 -*-

# University of Potsdam
"""Wordle bot logic including dialog and game phases."""

import logging
import os
import random
import string
from threading import Timer
from time import sleep

import requests
import socketio

from lib.image_data import ImageData
from lib.config import *


LOG = logging.getLogger(__name__)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class WordleBot:
    sio = socketio.Client(logger=True)
    """The ID of the task the bot is involved in."""
    task_id = None
    """The ID of the room where users for this task are waiting."""
    waiting_room = None

    def __init__(self, token, user, host, port):
        """This bot allows two players to play wordle together

        :param token: A uuid; a string following the same pattern
            as `0c45b30f-d049-43d1-b80d-e3c3a3ca22a0`
        :type token: str
        :param user: ID of a `User` object that was created with
        the token.
        :type user: int
        :param uri: Full URL including protocol and hostname,
            followed by the assigned port if any.
        :type uri: str
        :param images_per_room: Each room is mapped to a list
            of pairs with two image urls. Each participant
            is presented exactly one image per pair and round.
        :type images_per_room: dict
        :param timers_per_room: Each room is mapped to
            an instance of RoomTimers.
        :type timers_per_room: dict
        :param players_per_room: Each room is mapped to a list of
            users. Each user is represented as a dict with the
            keys 'name', 'id', 'msg_n' and 'status'.
        :type players_per_room: dict
        :param last_message_from: Each room is mapped to the user
            that has answered last. A user is represented as a
            dict with the keys 'name' and 'id'.
        :type last_message_from: dict
        :param guesses_per_room: each room is mapped to a current guess.
            this is used to make sure that both users sent the same
            guess for the current wordle, only so it is possible to
            advance in the game
        :type guesses_per_room: dict
        :param points_per_room: a dictionary that saves for each room
            the current point stand
        :type points_per_room: dict
        """
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"

        self.url = self.uri
        self.uri += "/slurk/api"

        self.images_per_room = ImageData(DATA_PATH, 3, SHUFFLE, SEED)
        self.players_per_room = dict()
        self.last_message_from = dict()
        self.guesses_per_room = dict()
        self.points_per_room = dict()

        # maps number of guesses to points
        self.point_system = dict(zip(
            [6, 5, 4, 3, 2, 1], [100, 50, 25, 10, 5, 1]
        ))

        # read wordlist
        with open(WORD_LIST) as infile:
            self.wordlist = set(
                (line.strip()) for line in infile
            )

        self.waiting_timer = None
        self.received_waiting_token = set()

        LOG.info(f"Running wordle bot on {self.uri} with token {self.token}")
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

    def register_callbacks(self):
        @self.sio.event
        def new_task_room(data):
            """Triggered after a new task room is created.

            An example scenario would be that the concierge
            bot emitted a room_created event once enough
            users for a task have entered the waiting room.
            """
            room_id = data["room"]
            task_id = data["task"]

            LOG.debug(f"A new task room was created with id: {data['task']}")
            LOG.debug(f"This bot is looking for task id: {self.task_id}")

            if task_id is not None and task_id == self.task_id:
                for usr in data['users']:
                    self.received_waiting_token.discard(usr['id'])

                # create image items for this room
                LOG.debug("Create data for the new task room...")

                self.images_per_room.get_image_pairs(room_id)
                self.players_per_room[room_id] = []
                for usr in data["users"]:
                    self.players_per_room[room_id].append(
                        {**usr, "msg_n": 0, "status": "joined"}
                    )
                self.last_message_from[room_id] = None

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if not response.ok:
                    LOG.error(f"Could not let wordle bot join room: {response.status_code}")
                    response.raise_for_status()
                LOG.debug("Sending wordle bot to new room was successful.")

                word, _ = self.images_per_room[room_id][0]
                logging.info(room_id)
                self.sio.emit("message_command",
                    {"command": f"wordle_init {word}", "room": room_id}
                )

                self.guesses_per_room[room_id] = dict()
                self.points_per_room[room_id] = 0
                self.show_item(room_id)

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            if room_id in self.images_per_room:
                # read out task greeting
                for line in TASK_GREETING:
                    self.sio.emit(
                        "text",
                        {"message": line,
                         "room": room_id,
                         "html": True}
                    )
                    sleep(.5)
                # ask players to send \ready
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr_title",
                    json={"text": line},
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if not response.ok:
                    LOG.error(f"Could not set task instruction title: {response.status_code}")
                    response.raise_for_status()

        @self.sio.event
        def status(data):
            """Triggered if a user enters or leaves a room."""
            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{data['user']['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if not task.ok:
                LOG.error(f"Could not set task instruction title: {task.status_code}")
                task.raise_for_status()
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

            room_id = data["room"]
            # someone joined waiting room
            if room_id == self.waiting_room:
                if data["type"] == "join":
                    LOG.debug("Waiting Timer restarted.")

            # some joined a task room
            elif room_id in self.images_per_room:
                curr_usr, other_usr = self.players_per_room[room_id]
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr

                if data["type"] == "join":
                    # inform game partner about the rejoin event
                    self.sio.emit(
                        "text",
                        {"message": f"{curr_usr['name']} has joined the game. ",
                         "room": room_id,
                         "receiver_id": other_usr["id"]}
                    )

                    # shuffle remaining words and start over with a new one
                    random.shuffle(self.images_per_room[room_id])

                    wordle, _ = self.images_per_room[room_id][0]
                    self.sio.emit("message_command",
                        {"command": f"wordle_init {wordle}", "room": room_id}
                    )
                    self.show_item(room_id)

                elif data["type"] == "leave":
                    # send a message to the user that was left alone
                    self.sio.emit(
                        "text",
                        {"message": f"{curr_usr['name']} has left the game. "
                                    "Please wait a bit, your partner may rejoin.",
                         "room": room_id,
                         "receiver_id": other_usr["id"]}
                    )

        @self.sio.event
        def text_message(data):
            """Triggered once a text message is sent (no leading /).

            Count user text messages.
            If encountering something that looks like a command
            then pass it on to be parsed as such.
            """
            LOG.debug(f"Received a message from {data['user']['name']}.")
            room_id = data["room"]
            user_id = data["user"]["id"]

            # filter irrelevant messages
            if room_id not in self.images_per_room or user_id == self.user:
                return

            # if the message is part of the main discussion count it
            for usr in self.players_per_room[room_id]:
                if usr["id"] == user_id and usr["status"] == "ready":
                    usr["msg_n"] += 1

        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(f"Received a command from {data['user']['name']}: {data['command']}")

            room_id = data["room"]
            user_id = data["user"]["id"]

            LOG.debug(data)

            if room_id in self.images_per_room:
                if data["command"] == "guess":
                    self.sio.emit(
                         "text",
                         {"message": "You need to provide a guess!",
                          "room": room_id,
                          "receiver_id": user_id}
                    )
                elif data["command"].startswith("guess"):
                    self._command_guess(room_id, user_id, data['command'])
                elif data["command"].startswith("end_round"):
                    self._command_end_round(room_id, user_id, data["command"])
                elif data["command"] in {"noreply", "no reply"}:
                    self.sio.emit(
                        "text",
                        {"message": "Please wait some more for an answer.",
                         "room": room_id,
                         "receiver_id": user_id}
                    )
                else:
                    self.sio.emit(
                        "text",
                        {"message": "Sorry, but I do not understand this command.",
                         "room": room_id,
                         "receiver_id": user_id}
                    )

    def _command_guess(self, room_id, user_id, command):
        """Must be sent to end a game round."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.players_per_room[room_id]
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        LOG.debug(command)

        # get the wordle for this room and the guess from the user
        wordle, _ = self.images_per_room[room_id][0]
        guess, remaining_guesses = command.split()[1:]

        # make sure it's a good guess
        if guess not in self.wordlist:
            self.sio.emit(
                "text",
                {
                    "message": (
                        "Unfortunately this word is not valid. "
                        "Make sure that there aren't any typos."
                    ),
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                    "html": True
                }
            )
            return

        # make sure the guess has the right length
        if len(wordle) != len(guess):
            self.sio.emit(
                "text",
                {
                    "message": (
                        "Unfortunately this word is not valid. "
                        f"Your guess needs to have {len(wordle)} letters."
                    ),
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                    "html": True
                }
            )
            return

        # add the guess to the current guess_dictionary
        # guess_dictionary = {
        #     room_id : {user_id: guess, other_user_id: guess},
        #     ...
        # }
        self.guesses_per_room[room_id][curr_usr["id"]] = guess

        # only one entry in dict, notify other user he should send a guess
        if len(self.guesses_per_room[room_id]) == 1:
            self.sio.emit(
                "text",
                {"message": "Let's wait for your partner "
                            "to also enter a guess.",
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                    "html": True}
            )
            self.sio.emit(
                "text",
                {"message": "Your partner thinks that you "
                            "have found the right word. "
                            "Enter your guess.",
                    "receiver_id": other_usr["id"],
                    "room": room_id,
                    "html": True}
            )
            return

        # 2 users sent different words, notify them
        if ((len(self.guesses_per_room[room_id]) == 2)
                and (len(set(self.guesses_per_room[room_id].values())) == 2)):
            self.sio.emit(
                "text",
                {"message": (
                    "You and your partner sent a different word, "
                    "please discuss and enter the same guess."
                ),
                "room": room_id}
            )
            self.guesses_per_room[room_id] = dict()
            return

        # both users think they are done with the game
        # conditions: 2 users already sent their guess and it's the same word
        if ((len(self.guesses_per_room[room_id]) == 2)
                and (len(set(self.guesses_per_room[room_id].values())) == 1)):
            # reset guess and send it to client to check
            self.guesses_per_room[room_id] = dict()
            self.sio.emit("message_command",
                {"command": f"wordle_guess {guess}", "room": room_id}
            )

            if ((wordle == guess) or (remaining_guesses == "1")):
                sleep(2)

                result = "LOST"
                points = 0

                if wordle == guess:
                    result = "WON"
                    points = self.point_system[int(remaining_guesses)]

                # update points for this room
                self.points_per_room[room_id] += points

                #self.timers_per_room[room_id].done_timer.cancel()
                self.images_per_room[room_id].pop(0)

                self.sio.emit(
                    "text",
                    {
                        "message": (
                            f"YOU {result}! For this round you get {points} points. "
                            f"Your total score is: {self.points_per_room[room_id]}"
                        ),
                        "room": room_id
                    }
                )

                # was this the last game round?
                if not self.images_per_room[room_id]:
                    self.sio.emit(
                        "text",
                        {"message": f"The game is over! Thank you for participating!",
                        "room": room_id}
                    )
                    sleep(1)

                    self.sio.emit(
                        "text",
                        {
                            "message": (
                                "Please share the following text on social media: "
                                "I played slurdle and helped science! "
                                f"Together with {other_usr['name']}, I got {self.points_per_room[room_id]} "
                                f"points for {self.images_per_room.n} puzzle(s). "
                                f"Play here: {self.url}. #slurdle"
                            ),
                            "receiver_id": curr_usr["id"],
                            "room": room_id,
                            "html": True
                        }
                    )
                    self.sio.emit(
                        "text",
                        {
                            "message": (
                                "Please share the following text on social media: "
                                "I played slurdle and helped science! "
                                f"Together with {curr_usr['name']}, I got {self.points_per_room[room_id]} "
                                f"points for {self.images_per_room.n} puzzle(s). "
                                f"Play here: {self.url}. #slurdle"
                            ),
                            "receiver_id": other_usr["id"],
                            "room": room_id,
                            "html": True
                        }
                    )

                    self.confirmation_code(room_id, "success")
                    sleep(1)
                    self.close_game(room_id)
                else:
                    # load the next image
                    self.sio.emit(
                        "text",
                        {"message": f"Ok, let's get both of you the next image. "
                                    f"{len(self.images_per_room[room_id])} to go!",
                        "room": room_id}
                    )

                    wordle, _ = self.images_per_room[room_id][0]
                    self.sio.emit("message_command",
                        {"command": f"wordle_init {wordle}", "room": room_id}
                    )

                    # reset attributes for the new round
                    for usr in self.players_per_room[room_id]:
                        usr["status"] = "ready"
                        usr["msg_n"] = 0

                    self.show_item(room_id)

    def _not_done(self, room_id, user_id):
        """One of the two players was not done."""
        for usr in self.players_per_room[room_id]:
            if usr["id"] == user_id:
                usr["status"] = "ready"
        self.sio.emit(
            "text",
            {"message": "Your partner seems to still want to discuss some more. "
                        "Send /difference again once you two are really finished.",
             "receiver_id": user_id,
             "room": room_id}
        )

    def show_item(self, room_id):
        """Update the image of the players."""
        LOG.debug("Update the image and task description of the players.")
        # guarantee fixed user order - necessary for update due to rejoin
        users = sorted(self.players_per_room[room_id], key=lambda x: x["id"])

        if self.images_per_room[room_id]:
            word, image = self.images_per_room[room_id][0]
            # show a different image to each user
            for usr in users:
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/current-image",
                    json={"attribute": "src", "value": image, "receiver_id": usr["id"]},
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if not response.ok:
                    LOG.error(f"Could not set image: {response.status_code}")
                    response.raise_for_status()

            # the task for both users is the same - no special receiver
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr_title",
                json={"text": TASK_TITLE},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if not response.ok:
                LOG.error(f"Could not set task instruction title: {response.status_code}")
                response.raise_for_status()

            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr",
                json={"text": TASK_DESCR},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if not response.ok:
                LOG.error(f"Could not set task instruction: {response.status_code}")
                response.raise_for_status()

    def _no_partner(self, room_id, user_id):
        """Handle the situation that a participant waits in vain."""
        if user_id not in self.received_waiting_token:
            self.sio.emit(
                "text",
                {"message": "Unfortunately we could not find a partner for you!",
                 "room": room_id, "receiver_id": user_id}
            )
            # create token and send it to user
            self.confirmation_code(room_id, "no_partner", receiver_id=user_id)
            sleep(5)
            self.sio.emit(
                "text",
                {"message": "You may also wait some more:)",
                 "room": room_id, "receiver_id": user_id}
             )

            self.received_waiting_token.add(user_id)
        else:
            self.sio.emit(
                "text",
                {"message": "You won't be remunerated for further waiting time.",
                 "room": room_id, "receiver_id": user_id}
            )
            sleep(2)
            self.sio.emit(
                "text",
                {"message": "Please check back at another time of the day.",
                 "room": room_id, "receiver_id": user_id}
            )

    def _noreply(self, room_id, user_id):
        """One participant did not receive an answer for a while."""
        curr_usr, other_usr = self.players_per_room[room_id]
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        self.sio.emit(
            "text",
            {"message": "The game ended because you were gone for too long!",
             "room": room_id,
             "receiver_id": other_usr["id"]}
        )
        self.sio.emit(
            "text",
            {"message": "Your partner seems to be away for a long time!",
             "room": room_id,
             "receiver_id": curr_usr["id"]}
        )
        # create token and send it to user
        self.confirmation_code(room_id, "no_reply", receiver_id=curr_usr["id"])
        self.close_game(room_id)

    def confirmation_code(self, room_id, status, receiver_id=None):
        """Generate AMT token that will be sent to each player."""
        kwargs = dict()
        # either only for one user or for both
        if receiver_id is not None:
            kwargs["receiver_id"] = receiver_id

        amt_token = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=6
        ))
        # post AMT token to logs
        response = requests.post(
            f"{self.uri}/logs",
            json={"event": "confirmation_log",
                  "room_id": room_id,
                  "data": {"status_txt": status, "amt_token": amt_token},
                  **kwargs},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(
                f"Could not post AMT token to logs: {response.status_code}"
            )
            response.raise_for_status()

        self.sio.emit(
            "text",
            {"message": "Please enter the following token into the field on "
                        "the HIT webpage, and close this browser window. ",
             "room": room_id, **kwargs}
        )
        self.sio.emit(
            "text",
            {"message": f"Here is your token: {amt_token}",
             "room": room_id, **kwargs}
        )
        return amt_token

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        self.sio.emit(
            "text",
            {"message": "You will be moved out of this room "
                        f"in {TIME_CLOSE*2*60}-{TIME_CLOSE*3*60}s.",
             "room": room_id}
        )
        sleep(2)
        self.sio.emit(
            "text",
            {"message": "Make sure to save your token before that.",
             "room": room_id}
        )
        self.room_to_read_only(room_id)

        # remove any task room specific objects
        self.images_per_room.pop(room_id)
        # self.timers_per_room.pop(room_id)
        self.players_per_room.pop(room_id)
        self.last_message_from.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if not response.ok:
            LOG.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()

    def rename_users(self, user_id):
        """Give all users in a room a new random name."""
        names_f = os.path.join(ROOT, "data", "names.txt")
        with open(names_f, 'r', encoding="utf-8") as f:
            names = [line.rstrip() for line in f]

            new_name = random.choice(names)

            response = requests.get(
                f"{self.uri}/users/{user_id}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if not response.ok:
                LOG.error(
                    f"Could not get user: {response.status_code}"
                )
                response.raise_for_status()

            response = requests.patch(
                f"{self.uri}/users/{user_id}",
                json={"name": new_name},
                headers={"If-Match": response.headers["ETag"],
                         "Authorization": f"Bearer {self.token}"}
            )
            if not response.ok:
                LOG.error(
                    f"Could not rename user: {response.status_code}"
                )
                response.raise_for_status()
            LOG.debug(f"Successfuly renamed user to '{new_name}'.")
