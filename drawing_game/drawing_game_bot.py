import json
import logging
import os
import random
from collections import defaultdict
from pathlib import Path
from threading import Timer
from time import sleep

import requests
import socketio

import config
from config import TASK_GREETING, TASK_DESCR_A, TASK_DESCR_B, \
    GAME_INSTANCE, COMPACT_GRID_INSTANCES, RANDOM_GRID_INSTANCES, INSTRUCTIONS_A, INSTRUCTIONS_B

LOG = logging.getLogger(__name__)
ROOT = Path(__file__).parent.resolve()

STARTING_POINTS = 0


class GridManager:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.json_files = self._get_json_files()
        self.all_grids = self._load_all_grids()

    def _get_json_files(self):
        return [file for file in os.listdir(self.root_path) if file.endswith('.json')]

    def _load_all_grids(self):
        all_grids = []
        for json_file in self.json_files:
            file_path = self.root_path / json_file
            with open(file_path, 'r') as file:
                json_content = json.load(file)
                target_grid = json_content.get('target_grid')
                if target_grid:
                    all_grids.append(target_grid)
        return all_grids

    def get_random_grid(self):
        if self.all_grids:
            random_grid = random.choice(self.all_grids)
            index = self.all_grids.index(random_grid)
            random_file = self.json_files[index]
            LOG.debug(f"Randomly Chosen File: {random_file}, randomly Chosen Grid: {random_grid}")
            return random_grid
        else:
            LOG.debug("No JSON files found in the directory.")
            return None

    def remove_grid(self, grid):
        if grid in self.all_grids:
            index = self.all_grids.index(grid)
            random_file = self.json_files[index]
            LOG.debug(f"File {random_file} has been removed.")
            # Remove the chosen grid from the list
            self.all_grids.pop(index)
        else:
            LOG.debug("Grid not found in the list.")


class Session:
    def __init__(self):
        self.players = list()
        self.player_a = None
        self.player_b = None
        self.player_a_instructions = TASK_DESCR_A.read_text()
        self.player_b_instructions = TASK_DESCR_B.read_text()
        self.all_grids = GridManager(COMPACT_GRID_INSTANCES)
        self.target_grid = None  # Looks like this  ▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢\n▢ ▢ ▢ ▢ ▢
        self.drawn_grid = None
        self.game_round = None
        self.timer = None
        self.points = {
            "score": STARTING_POINTS,
            "history": [
                {"correct": 0, "wrong": 0, "warnings": 0}
            ]
        }
        self.rounds_left = None

    def close(self):
        pass

    def pick_player_a(self):
        self.player_a = random.choice(self.players)["id"]

    def pick_player_b(self):
        for player in self.players:
            if player["id"] != self.player_a:
                self.player_b = player["id"]

    def get_grid(self):
        instance = json.loads(GAME_INSTANCE.read_text())['target_grid']
        return instance


class SessionManager(defaultdict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)


class DrawingBot:
    sio = socketio.Client(logger=True)
    """The ID of the task the bot is involved in."""
    task_id = None
    """The ID of the room where users for this task are waiting."""
    waiting_room = None

    def __init__(self, token, user, host, port):
        """This bot allows two players that are shown two different
        or equal pictures to discuss about what they see and decide
        whether there are differences.

        :param token: A uuid; a string following the same pattern
            as `0c45b30f-d049-43d1-b80d-e3c3a3ca22a0`
        :type token: str
        :param user: ID of a `User` object that was created with
        the token.
        :type user: int
        :param uri: Full URL including protocol and hostname,
            followed by the assigned port if any.
        :type uri: str
        :param players_per_room: Each room is mapped to a list of
            users. Each user is represented as a dict with the
            keys 'name', 'id', 'msg_n' and 'status'.
        :type players_per_room: dict
        """
        self.token = token
        self.user = user
        self.sessions = SessionManager(Session)
        self.uri = host
        if port is not None:
            self.uri += f":{port}"
        self.uri += "/slurk/api"

        self.players_per_room = dict()
        self.received_waiting_token = set()

        LOG.info(f"Running drawing game bot on {self.uri} with token {self.token}")
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
                for usr in data["users"]:
                    self.received_waiting_token.discard(usr["id"])

                # create image items for this room
                LOG.debug("Create data for the new task room...")

                # Resize screen
                self.move_divider(room_id, 30, 70)

                # create a new session for these users
                self.sessions.create_session(room_id)

                # self.images_per_room.get_image_pairs(room_id)
                self.players_per_room[room_id] = []
                for usr in data["users"]:
                    self.sessions[room_id].players.append(
                        {**usr, "msg_n": 0, "status": "joined"}
                    )
                    self.players_per_room[room_id].append(
                        {**usr, "msg_n": 0, "status": "joined"}
                    )

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    LOG.error(
                        f"Could not let drawing game bot join room: {response.status_code}"
                    )
                    response.raise_for_status()
                LOG.debug("Sending drawing game bot to new room was successful.")
                self.sio.emit(
                    "message_command",
                    {"command": {"command": "drawing_game_init"}, "room": room_id},
                )
                # self.start_game(room_id)

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            # read out task greeting
            message = TASK_GREETING.read_text()
            self.sio.emit(
                "text",
                {
                    "message": message, "room": room_id, "html": True,
                }
            )

        @self.sio.event
        def status(data):
            """Triggered if a user enters or leaves a room."""
            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{data['user']['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not task.ok:
                LOG.error(f"Could not set task instruction title: {task.status_code}")
                task.raise_for_status()
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

            room_id = data["room"]
            # someone joined waiting room
            if room_id == self.waiting_room:
                pass
                # if self.waiting_timer is not None:
                #     LOG.debug("Waiting Timer stopped.")
                #     self.waiting_timer.cancel()
                # if data["type"] == "join":
                #     LOG.debug("Waiting Timer restarted.")

            # some joined a task room
            else:
                curr_usr, other_usr = self.players_per_room[room_id]
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr

                if data["type"] == "join":
                    # inform game partner about the rejoin event
                    self.sio.emit(
                        "text",
                        {
                            "message": f"{curr_usr['name']} has joined the game. ",
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                        },
                    )
                elif data["type"] == "leave":
                    # send a message to the user that was left alone
                    self.sio.emit(
                        "text",
                        {
                            "message": f"{curr_usr['name']} has left the game. "
                                       "Please wait a bit, your partner may rejoin.",
                            "room": room_id,
                            "receiver_id": other_usr["id"],
                        },
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
            if user_id == self.user:
                return

            # if the message is part of the main discussion count it
            for usr in self.players_per_room[room_id]:
                if usr["id"] == user_id and usr["status"] == "ready":
                    usr["msg_n"] += 1

        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]
            this_session = self.sessions[room_id]
            if isinstance(data["command"], str):
                command = data['command'].lower()

            # do not process commands from itself
            if str(user_id) == self.user:
                return

            if isinstance(data["command"], dict):
                if "guess" in data["command"]:
                    if data["command"]["guess"].strip() == "":
                        self.sio.emit(
                            "text",
                            {
                                "message": "**You need to provide a guess!**",
                                "room": room_id,
                                "receiver_id": user_id,
                                "html": True,
                            },
                        )
                        return
                    else:
                        self.sio.emit(
                            "text",
                            {
                                "message": "You sent your drawn grid to the other player.",
                                "room": room_id,
                                "receiver_id": user_id,
                                "html": True,
                            },
                        )
                        this_session.drawn_grid = data["command"]["guess"].strip()
                        LOG.debug(f"the drawn grid {this_session.drawn_grid} was sent to the other player")
                        return

            if this_session.rounds_left is None:
                if "ready" in command:
                    self._command_ready(room_id, user_id)
                    return
                else:
                    self.sio.emit(
                        "text",
                        {
                            "message": "Sorry, but I do not understand this command.",
                            "room": room_id,
                            "receiver_id": user_id,
                        },
                    )
                    return
            if "done" in data["command"]:
                self._command_done(room_id, user_id, command)
                return
            # player_a
            if this_session.player_a == user_id:
                self.sio.emit(
                    "text",
                    {
                        "message": command,
                        "room": room_id,
                        "receiver_id": this_session.player_b,
                    },
                )
                this_session.rounds_left -= 1
                self.update_rights(room_id, False, True)
                sleep(1)

            # player_b
            elif this_session.player_b == user_id:
                if '▢' in command:
                    drawn_grid = self.reformat_drawn_grid(command)
                    this_session.drawn_grid = drawn_grid
                    dislayed_grid = self.transform_string_in_grid(drawn_grid.upper())
                    self.sio.emit(
                        "text",
                        {
                            "message": f"GRID: <br>{dislayed_grid}",
                            "room": room_id,
                            "receiver_id": this_session.player_a,
                            "html": True
                        },
                    )
                    sleep(1)
                    if this_session.rounds_left >= 1:
                        self.sio.emit(
                            "text",
                            {
                                "message": "What is your next instruction?",
                                "room": room_id,
                                "receiver_id": this_session.player_a,
                            },
                        )
                        self.update_rights(room_id, True, False)
                        sleep(1)
                        return
                    self._command_done(room_id, user_id, command)
                else:
                    self.sio.emit(
                        "text",
                        {
                            "message": "Sorry, but I do not understand this command. Try again.",
                            "room": room_id,
                            "receiver_id": user_id,
                        },
                    )

    def reformat_drawn_grid(self, grid):
        grid = grid.lower()
        grid = grid.replace('\n', ' ')
        return grid

    def process_move(self, room_id, reward: int):
        this_session = self.sessions[room_id]
        this_session.game_round += 1
        self.next_round(room_id)

    def update_reward(self, room_id, reward):
        score = self.sessions[room_id].points["score"]
        score += reward
        score = round(score, 2)
        self.sessions[room_id].points["score"] = max(0, score)

    def update_title_points(self, room_id, reward):
        score = self.sessions[room_id].points["score"]
        correct = self.sessions[room_id].points["history"][0]["correct"]
        wrong = self.sessions[room_id].points["history"][0]["wrong"]
        if reward == 0:
            wrong += 1
        elif reward == 1:
            correct += 1

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/title",
            json={"text": f"Score: {score} 🏆 | Correct: {correct} ✅ | Wrong: {wrong} ❌"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.sessions[room_id].points["history"][0]["correct"] = correct
        self.sessions[room_id].points["history"][0]["wrong"] = wrong

        self.request_feedback(response, "setting point stand in title")

    def next_round(self, room_id):
        this_session = self.sessions[room_id]
        # Remove grid so one instance is not played several times
        this_session.all_grids.remove_grid(this_session.target_grid)
        # Get new grid
        this_session.target_grid = this_session.all_grids.get_random_grid()
        # was this the last game round?
        if self.sessions[room_id].game_round >= 4:
            self.sio.emit(
                "text",
                {"message": "The experiment is over! Thank you for participating :)",
                 "room": room_id},
            )
            self.close_game(room_id)
        else:
            self.sio.emit(
                "text",
                {"message": f"You are starting round {this_session.game_round} out of 3",
                 "room": room_id,
                 }
            )
            self.sio.emit(
                "text",
                {"message": "Wait for a new instruction.",
                 "room": room_id,
                 "receiver_id": this_session.player_b}
            )
            self.show_item(room_id)
            self.update_rights(room_id, player_a=True, player_b=False)

    def update_rights(self, room_id, player_a: bool, player_b: bool):
        this_session = self.sessions[room_id]
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr['id'] != this_session.player_a:
            curr_usr, other_usr = other_usr, curr_usr
        # update writing rights to player_a (assign or revoke)
        self.set_message_privilege(this_session.player_a, player_a)
        self.check_writing_right(room_id, curr_usr, player_a)
        # update writing rights to other user (assign or revoke)
        self.set_message_privilege(this_session.player_b, player_b)
        self.check_writing_right(room_id, other_usr, player_b)

    def set_message_privilege(self, user_id, value):
        """
        change user's permission to send messages
        """
        # get permission_id based on user_id
        response = requests.get(
            f"{self.uri}/users/{user_id}/permissions",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "retrieving user's permissions")

        permission_id = response.json()["id"]
        requests.patch(
            f"{self.uri}/permissions/{permission_id}",
            json={"send_message": value},
            headers={
                "If-Match": response.headers["ETag"],
                "Authorization": f"Bearer {self.token}",
            },
        )
        self.request_feedback(response, "changing user's message permission")

    def check_writing_right(self, room_id, usr, writing_right):
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr['id'] != usr['id']:
            curr_usr, other_usr = other_usr, curr_usr
        if writing_right is True:
            # assign writing rights to the user
            response = requests.delete(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "readonly",
                    "value": "placeholder",
                    "receiver_id": other_usr["id"],
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "readonly",
                    "value": "true",
                    "receiver_id": other_usr["id"],
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "placeholder",
                    "value": "Enter your message here!",
                    "receiver_id": curr_usr["id"],
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )

        elif writing_right is False:
            # make input field unresponsive
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "readonly",
                    "value": "true",
                    "receiver_id": curr_usr["id"],
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "placeholder",
                    "value": "Wait for a message from your partner",
                    "receiver_id": curr_usr["id"],
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )

            response = requests.delete(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "readonly",
                    "value": "placeholder",
                    "receiver_id": other_usr["id"],
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "placeholder",
                    "value": "Enter your message here!",
                    "receiver_id": other_usr["id"],
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )

    def _command_done(self, room_id, user_id, command):
        """Must be sent to end a game round."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        LOG.debug(command)

        this_session = self.sessions[room_id]

        # get the grid for this room and the guess from the user
        grid = this_session.target_grid.lower()
        grid = grid.replace('\n', ' ')
        # guess = command["guess"]
        # LOG.debug(guess)
        # if command["guess"] is not None:
        #     this_session.drawn_grid = command["guess"]

        self.sio.emit(
            "message_command",
            {
                "command": {
                    "command": "drawing_game_guess",
                    "guess": this_session.drawn_grid,  # Or guess?
                    "correct_grid": grid,
                },
                "room": room_id,
            },
        )

        if this_session.drawn_grid is None:
            self.sio.emit(
                "text",
                {
                    "message":
                        f"**You didn't provide an answer. You lost this round**",
                    "room": room_id,
                    "html": True,
                },
            )
            self.process_move(room_id, 0)
            return

        if grid != this_session.drawn_grid:
            result = 'LOST'
            points = 0
            self.update_reward(room_id, points)
            self.update_title_points(room_id, points)
            self.sio.emit(
                "text",
                {
                    "message":
                        f"**YOU both {result}! For this round you get {points} points. "
                        f"Your total score is: {self.sessions[room_id].points['score']}**",
                    "room": room_id,
                    "html": True,
                },
            )
            self.process_move(room_id, 0)
        else:
            result = 'WON'
            points = 1
            self.update_reward(room_id, points)
            self.update_title_points(room_id, points)
            self.sio.emit(
                "text",
                {
                    "message":
                        f"**YOU both {result}! For this round you get {points} points. "
                        f"Your total score is: {self.sessions[room_id].points['score']}**",
                    "room": room_id,
                    "html": True,
                },
            )
            self.process_move(room_id, 1)

            # if (word == guess) or (remaining_guesses == 1):
            #     sleep(2)
            #
            #     result = "LOST"
            #     points = 0
            #
            #     if word == guess:
            #         result = "WON"
            #         points = self.point_system[int(remaining_guesses)]
            #
            #     # update points for this room
            #     self.sessions[room_id].points += points
            #
            #     # self.timers_per_room[room_id].done_timer.cancel()
            #     self.sio.emit(
            #         "text",
            #         {
            #             "message": COLOR_MESSAGE.format(
            #                 color=STANDARD_COLOR,
            #                 message=(
            #                     f"**YOU {result}! For this round you get {points} points. "
            #                     f"Your total score is: {self.sessions[room_id].points}**"
            #                 ),
            #             ),
            #             "room": room_id,
            #             "html": True,
            #         },
            #     )
            #
            #     self.next_round(room_id)

    def _command_ready(self, room_id, user_id):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.players_per_room[room_id]
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            sleep(0.5)
            self.sio.emit(
                "text",
                {
                    "message": "You have already typed 'ready'.",
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                },
            )
            return
        curr_usr["status"] = "ready"

        # self.timers_per_room[room_id].ready_timer.cancel()
        # a first ready command was sent
        if other_usr["status"] == "joined":
            sleep(0.5)
            # give the user feedback that his command arrived
            self.sio.emit(
                "text",
                {
                    "message": "Now, waiting for your partner to type 'ready'.",
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                },
            )
            self.sio.emit(
                "text",
                {
                    "message": "Your partner is ready. Please, type 'ready'!",
                    "room": room_id,
                    "receiver_id": other_usr["id"],
                },
            )
        else:
            # both users are ready and the game begins
            self.sio.emit(
                "text",
                {"message": "Woo-Hoo! The game will begin now.", "room": room_id},
            )
            sleep(1)
            self.sessions[room_id].game_round = 1
            LOG.debug(f"Game round {self.sessions[room_id].game_round}")
            self.start_game(room_id)
            # self.show_item(room_id)
            # self.sio.emit(
            #     "message_command",
            #     {"command": {"command": "drawing_game_init"}, "room": room_id},
            # )

    def send_individualised_instructions(self, room_id):
        this_session = self.sessions[room_id]

        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "send_instr",
                    "message": f"{INSTRUCTIONS_A}"
                },
                "room": room_id,
                "receiver_id": this_session.player_a,
            }
        )
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "send_instr",
                    "message": f"{INSTRUCTIONS_B}"
                },
                "room": room_id,
                "receiver_id": this_session.player_b,
            }
        )

        # # Send explainer_ instructions to player_a
        # response = requests.patch(f"{self.uri}/rooms/{room_id}/text/instr_title",
        #                           json={"text": "Describe the grid",
        #                                 "receiver_id": this_session.player_a},
        #                           headers={"Authorization": f"Bearer {self.token}"},
        #                           )
        # if not response.ok:
        #     LOG.error(
        #         f"Could not set task instruction title: {response.status_code}"
        #     )
        #     response.raise_for_status()
        #
        # instructions_a = this_session.player_a_instructions  # Loads instructions but non-collapsible
        # response_e = requests.patch(
        #     f"{self.uri}/rooms/{room_id}/text/instr",
        #     json={
        #         "text": instructions_a,
        #         "receiver_id": this_session.player_a,
        #     },
        #     headers={"Authorization": f"Bearer {self.token}"},
        # )
        #
        # if not response_e.ok:
        #     LOG.error(f"Could not set task instruction: {response_e.status_code}")
        #     response_e.raise_for_status()

        # # Send drawer_ instructions to player_b
        # response = requests.patch(f"{self.uri}/rooms/{room_id}/text/instr_title",
        #                           json={"text": "Draw the described grid",
        #                                 "receiver_id": this_session.player_b},
        #                           headers={"Authorization": f"Bearer {self.token}"},
        #                           )
        # if not response.ok:
        #     LOG.error(
        #         f"Could not set task instruction title: {response.status_code}"
        #     )
        #     response.raise_for_status()
        #
        # instructions_b = this_session.player_b_instructions
        # response_g = requests.patch(
        #     f"{self.uri}/rooms/{room_id}/text/instr",
        #     json={
        #         "class": "collapsible-content",
        #         "text": instructions_b,
        #         "receiver_id": this_session.player_b,
        #     },
        #     headers={"Authorization": f"Bearer {self.token}"},
        # )
        # if not response_g.ok:
        #     LOG.error(f"Could not set task instruction: {response_g.status_code}")
        #     response_g.raise_for_status()

    def start_game(self, room_id):
        this_session = self.sessions[room_id]

        # 1) Set rounds
        this_session.rounds_left = 3
        LOG.debug(f"Rounds left {this_session.rounds_left}")
        # 2) Choose players A and B
        self.sessions[room_id].pick_player_a()
        self.sessions[room_id].pick_player_b()
        for user in this_session.players:
            if user["id"] == this_session.player_a:
                LOG.debug(f'{user["name"]} is player A.')
            else:
                LOG.debug(f'{user["name"]} is player B.')

        # 3) Load grid
        # this_session.target_grid = this_session.get_grid()
        if this_session.all_grids:
            random_grid = this_session.all_grids.get_random_grid()
            this_session.target_grid = random_grid
        else:
            random_grids = GridManager(RANDOM_GRID_INSTANCES)
            this_session.all_grids = random_grids
            random_grid = this_session.all_grids.get_random_grid()
            this_session.target_grid = random_grid



        self.send_individualised_instructions(room_id)
        self.show_item(room_id)

    def transform_string_in_grid(self, string):
        rows = 5
        cols = 5

        # Split the input string into individual characters
        characters = [char for char in string if char != ' ']

        # Initialize an empty grid
        grid = [['▢' for _ in range(cols)] for _ in range(rows)]

        # Fill the grid with characters
        for i in range(rows):
            for j in range(cols):
                if characters:
                    grid[i][j] = characters.pop(0)

        # Convert the grid to a string representation
        grid_string = '<br>'.join([' '.join(row) for row in grid])

        return grid_string

    @staticmethod
    def request_feedback(response, action):
        if not response.ok:
            LOG.error(f"Could not {action}: {response.status_code}")
            response.raise_for_status()
        else:
            LOG.debug(f"Successfully did {action}.")

    def move_divider(self, room_id, chat_area=50, task_area=50):
        """move the central divider and resize chat and task area
        the sum of char_area and task_area must sum up to 100
        """
        if chat_area + task_area != 100:
            LOG.error("Could not resize chat and task area: invalid parameters.")
            raise ValueError("chat_area and task_area must sum up to 100")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/sidebar",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"attribute": "style", "value": f"width: {task_area}%"},
        )
        self.request_feedback(response, "resize sidebar")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/content",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"attribute": "style", "value": f"width: {chat_area}%"},
        )
        self.request_feedback(response, "resize content area")

    def _not_done(self, room_id, user_id):
        """One of the two players was not done."""
        for usr in self.players_per_room[room_id]:
            if usr["id"] == user_id:
                usr["status"] = "ready"
        self.sio.emit(
            "text",
            {
                "message": "Your partner seems to still want to discuss some more. "
                           "Send 'done' again once you two are really finished.",
                "receiver_id": user_id,
                "room": room_id,
            },
        )

    def show_item(self, room_id):
        """Update the image of the players."""
        LOG.debug("Update the image and task description of the players.")
        # guarantee fixed user order - necessary for update due to rejoin
        # users = sorted(self.sessions[room_id].players, key=lambda x: x["id"])
        # user_1 = users[0]
        # user_2 = users[1]

        this_session = self.sessions[room_id]
        this_session.rounds_left = 3

        if this_session.target_grid:
            # Display on chat area
            grid = this_session.target_grid.replace('\n', '<br>')
            self.sio.emit(
                "text",
                {
                    "message": f"This is the target grid: <br>{grid}<br><br>You have {this_session.rounds_left} turns "
                               f"to describe it to the other player.<br><br>Give the first instruction.",
                    "receiver_id": this_session.player_a,
                    "room": room_id,
                    "html": True
                },
            )

            # Display on display area
            grid = this_session.target_grid.replace('\n', '<br>')
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "send_grid",
                        "message": f"<br><br>{grid}",
                    },
                    "room": room_id,
                    "receiver_id": this_session.player_a,
                }
            )
            # Hide game board for player a
            self._hide_game_board(room_id, this_session.player_a)

            # response = requests.patch(
            #     f"{self.uri}/rooms/{room_id}/text/current-grid",
            #     json={
            #         "text": this_session.target_grid,
            #         "receiver_id": this_session.player_a,
            #     },
            #     headers={"Authorization": f"Bearer {self.token}"},
            # )
            # self.request_feedback(response, "set grid")
            # enable the grid
            response = requests.delete(
                f"{self.uri}/rooms/{room_id}/class/grid-area",
                json={"class": "dis-area", "receiver_id": this_session.player_a},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "enable grid")

    def _hide_game_board(self, room_id, user_id):  # Doesn't work
        response = requests.post(
            f"{self.uri}/rooms/{room_id}/class/game-board",
            json={"class": "dis-area", "receiver_id": user_id},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "hide game board")

    def _hide_image_desc(self, room_id):
        response = requests.post(
            f"{self.uri}/rooms/{room_id}/class/image-desc",
            json={"class": "dis-area"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "hide description")

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        self.sio.emit(
            "text",
            {
                "message": "You will be moved out of this room ",
                "room": room_id,
            },
        )
        self.room_to_read_only(room_id)

        for usr in self.players_per_room[room_id]:
            self.rename_users(usr["id"])

            response = requests.post(
                f"{self.uri}/users/{usr['id']}/rooms/{self.waiting_room}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                LOG.error(
                    f"Could not let user join waiting room: {response.status_code}"
                )
                response.raise_for_status()
            LOG.debug("Sending user to waiting room was successful.")

            response = requests.delete(
                f"{self.uri}/users/{usr['id']}/rooms/{room_id}",
                headers={
                    "If-Match": response.headers["ETag"],
                    "Authorization": f"Bearer {self.token}",
                },
            )
            if not response.ok:
                LOG.error(
                    f"Could not remove user from task room: {response.status_code}"
                )
                response.raise_for_status()
            LOG.debug("Removing user from task room was successful.")

        # remove any task room specific objects
        self.players_per_room.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set room to read_only: {response.status_code}")
            response.raise_for_status()

    def rename_users(self, user_id):
        """Give all users in a room a new random name."""
        names_f = os.path.join(ROOT, "data", "names.txt")
        with open(names_f, "r", encoding="utf-8") as f:
            names = [line.rstrip() for line in f]

            new_name = random.choice(names)

            response = requests.get(
                f"{self.uri}/users/{user_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                LOG.error(f"Could not get user: {response.status_code}")
                response.raise_for_status()

            response = requests.patch(
                f"{self.uri}/users/{user_id}",
                json={"name": new_name},
                headers={
                    "If-Match": response.headers["ETag"],
                    "Authorization": f"Bearer {self.token}",
                },
            )
            if not response.ok:
                LOG.error(f"Could not rename user: {response.status_code}")
                response.raise_for_status()
            LOG.debug(f"Successfuly renamed user to '{new_name}'.")

# class ImageGame:
#
#     def __init__(self, game_instance: Dict, player_backends: List[str]):
#         self.game_id = game_instance['game_id']
#         self.player_1_prompt_header = game_instance['player_1_prompt_header']
#         self.player_2_prompt_header = game_instance['player_2_prompt_header']
#         self.player_1_question = game_instance['player_1_question']
#         self.target_grid = game_instance['target_grid']
#         self.player_backends = player_backends
#         self.grid_dimension = game_instance['grid_dimension']
#         self.number_of_letters = game_instance['number_of_letters']
#         self.fill_row = game_instance['fill_row']
#         self.fill_column = game_instance['fill_column']
#
#
#         self.instruction_follower = InstructionFollower(player_backends[1])
#         self.instruction_giver = InstructionGiver(player_backends[0])
#
#         self.given_instruction = Instruction()
#         self.given_instruction.add_user_message(
#             self.player_1_prompt_header + '\n' + self.target_grid + '\n' + self.player_1_question + '\n')
#
#         self.next_turn_message = ''
#         self.followed_instruction = Instruction()
#
#         self.current_turn = 0
#         self.max_turns = self.grid_dimension * self.grid_dimension
#         self.terminate = False
