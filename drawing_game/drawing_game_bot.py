# -*- coding: utf-8 -*-
# Sandra Sánchez Páez
# Bachelorarbeit Computerlinguistik 2024
# University of Potsdam
import logging
import random
import string
from collections import defaultdict
from threading import Timer
from time import sleep

import requests
import socketio

from .config import TASK_GREETING, COMPACT_GRID_INSTANCES, RANDOM_GRID_INSTANCES, \
    INSTRUCTIONS_A, INSTRUCTIONS_B, KEYBOARD_INSTRUCTIONS, ROOT, STARTING_POINTS, \
    TIMEOUT_TIMER, LEAVE_TIMER, WAITING_PARTNER_TIMER, PLATFORM, PROLIFIC_URL

from .gridmanager import GridManager
from templates import TaskBot

LOG = logging.getLogger(__name__)


class Session:
    def __init__(self):
        self.players = list()
        self.player_a = None  # Instruction giver
        self.player_b = None  # Instruction follower
        self.task_greeting = TASK_GREETING.read_text()
        self.player_a_instructions = INSTRUCTIONS_A
        self.player_b_instructions = INSTRUCTIONS_B
        self.keyboard_instructions = KEYBOARD_INSTRUCTIONS
        self.all_compact_grids = GridManager(COMPACT_GRID_INSTANCES)
        self.all_random_grids = GridManager(RANDOM_GRID_INSTANCES)
        self.grid_type = None
        self.target_grid = None  # Looks like this  X ▢ ▢ ▢ ▢\n▢ X ▢ ▢ ▢\n▢ ▢ X ▢ ▢\n▢ ▢ ▢ X ▢\n▢ ▢ ▢ ▢ X
        self.drawn_grid = None
        self.current_turn = 0
        self.game_round = 0
        self.timer = None # RoomTimer()
        self.left_room_timer = dict()
        self.points = {
            "score": STARTING_POINTS,
            "history": [
                {"correct": 0, "wrong": 0, "warnings": 0}
            ]
        }
        self.game_over = False

    def pick_player_a(self):
        self.player_a = random.choice(self.players)

    def pick_player_b(self):
        for player in self.players:
            if player != self.player_a:
                self.player_b = player


class SessionManager(defaultdict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self.pop(room_id)


class DrawingBot(TaskBot):
    sio = socketio.Client(logger=True)
    """The ID of the task the bot is involved in."""
    task_id = None
    """The ID of the room where users for this task are waiting."""
    waiting_room = None

    def __init__(self, *args, **kwargs):
        """
        This bot allows two players to play a game in which the instruction-giver
        instructs the instruction-follower how to draw a given 5x5 grid.
        When the instruction-giver is done giving instructions, the drawn grid is
        compared against the target grid.
        :param token: A uuid; a string following the same pattern
            as `0c45b30f-d049-43d1-b80d-e3c3a3ca22a0`
        :type token: str
        :param user: ID of a `User` object that was created with
        the token.
        :type user: int
        :param uri: Full URL including protocol and hostname,
            followed by the assigned port if any.
        :type uri: str
        """
        super().__init__(*args, **kwargs)
        self.sessions = SessionManager(Session)
        self.received_waiting_token = set()
        self.waiting_timer = None
        self.left_room_timer = dict()
        self.data_collection = PLATFORM
        self.interactions = {
            "players": {},
            "turns": []
        }
        self.scores = {
            "turn scores": {},
            "episode scores": {},
        }

    def run(self):
        # establish a connection to the server
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": self.user},
            namespaces="/",
        )
        # wait until the connection with the server ends
        self.sio.wait()

    def timeout_close_game(self, room_id):
        self.sio.emit(
            "text",
            {"message": "Closing session because of inactivity", "room": room_id},
        )
        self.confirmation_code(room_id, status='timeout')
        self.close_game(room_id)

    def user_joined(self, user):
        timer = self.left_room_timer.get(user)
        if timer is not None:
            self.left_room_timer[user].cancel()
        else:
            pass

    def user_did_not_rejoin(self, room_id):
        self.sio.emit(
            "text",
            {"message": "Your partner didn't rejoin, you will receive a token so you can get paid for your time",
             "room": room_id},
        )
        self.confirmation_code(room_id, status='user_left')
        self.close_game(room_id)

    def _no_partner(self, room_id, user_id):
        """Handle the situation that a participant waits in vain."""
        if user_id not in self.received_waiting_token:
            self.sio.emit(
                "text",
                {"message": "Unfortunately we could not find a partner for you!",
                 "room": room_id,
                 "receiver_id": user_id,
                 },
            )
            #todo:display messages?

            # create token and send it to user
            self.confirmation_code(room_id, status="no_partner")
            sleep(2)
            self.received_waiting_token.add(user_id)
            self.close_game(room_id)
            return
        else:
            self.sio.emit(
                "text",
                {"message": "You won't be remunerated for further waiting time.",
                 "room": room_id,
                 "receiver_id": user_id,
                 },
            )
            self.close_game(room_id)

    def on_task_room_creation(self, data):
        room_id = data["room"]
        task_id = data["task"]

        LOG.debug(f"A new task room was created with id: {data['task']}")
        LOG.debug(f"This bot is looking for task id: {self.task_id}")

        if task_id is not None and task_id == self.task_id:
            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])

            # create image items for this room
            LOG.debug("Create data for the new task room...")
            LOG.debug(data)

            # create a new session for these users
            self.sessions.create_session(room_id)
            timer = Timer(
                TIMEOUT_TIMER * 60, self.timeout_close_game, args=[room_id]
            )
            timer.start()
            self.sessions[room_id].timer = timer

            # add players
            self.sessions[room_id].players = []
            for usr in data["users"]:
                self.sessions[room_id].players.append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )
            LOG.debug(f"The players are {self.sessions[room_id].players}")

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

    @staticmethod
    def request_feedback(response, action):
        if not response.ok:
            LOG.error(f"Could not {action}: {response.status_code}")
            response.raise_for_status()
        else:
            LOG.debug(f"Successfully did {action}.")

    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]
            LOG.debug(f"Triggered joined_room for room_id {room_id}")

            if room_id in self.sessions:
                # read out task greeting
                message = self.sessions[room_id].task_greeting
                self.sio.emit(
                    "text",
                    {
                        "message": message, "room": room_id, "html": True,
                    }
                )

        @self.sio.event
        def status(data):
            """Triggered if a user enters or leaves a room."""
            LOG.debug(f"Triggered status: {data['user']} did {data['type']} the room {data['room']}")
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
            event = data["type"]
            user = data["user"]

            # don't do this for the bot itself
            if user["id"] == self.user:
                return

            # someone joined waiting room
            if room_id == self.waiting_room:
                if self.waiting_timer is not None:
                    LOG.debug("Waiting Timer stopped.")
                    self.waiting_timer.cancel()
                if data["type"] == "join":
                    LOG.debug("Waiting Timer started.")
                    self.waiting_timer = Timer(
                        WAITING_PARTNER_TIMER * 60,
                        self._no_partner,
                        args=[room_id, data["user"]["id"]],
                    )
                    self.waiting_timer.start()
                    sleep(10)
                    self.sio.emit(
                        "text",
                        {
                            "message": f"If nobody shows up within "
                                        f"{WAITING_PARTNER_TIMER} minutes, I will give "
                                        f"you a submission link, so that you "
                                        f"can get paid for your waiting time."
                            ,
                            "room": room_id,
                            "receiver_id": data['user']['id'],
                            "html": True,
                        },
                    )

            # someone joined a task room
            elif room_id in self.sessions:
                LOG.debug(f"The players in task room are {self.sessions[room_id].players}")
                curr_usr, other_usr = self.sessions[room_id].players
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

                    # cancel leave timers if any
                    LOG.debug("Cancel timer: user joined")
                    self.user_joined(curr_usr["id"])

                elif data["type"] == "leave":
                    if room_id in self.sessions:
                        if self.sessions[room_id].game_over is False:
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
                            # cancel round timer and start left_user timer
                            LOG.debug("Start timer: user left")
                            self.sessions[room_id].left_room_timer[curr_usr["id"]] = Timer(
                                LEAVE_TIMER * 60, self.user_did_not_rejoin,
                                args=[room_id],
                            )
                            self.sessions[room_id].left_room_timer[curr_usr["id"]].start()
            else:
                pass

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
            if room_id not in self.sessions or user_id == self.user:
                return

            this_session = self.sessions[room_id]
            # Reset timer
            LOG.debug("Reset timeout timer")
            if this_session.timer:
                this_session.timer.cancel()
            timer = Timer(
                TIMEOUT_TIMER * 60, self.timeout_close_game, args=[room_id]
            )
            timer.start()
            self.sessions[room_id].timer = timer

        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]
            this_session = self.sessions[room_id]

            # do not process commands from itself
            if str(user_id) == self.user:
                return

            # Reset timer
            LOG.debug("Reset timeout timer")
            if this_session.timer:
                this_session.timer.cancel()
            timer = Timer(
                TIMEOUT_TIMER * 60, self.timeout_close_game, args=[room_id]
            )
            timer.start()
            self.sessions[room_id].timer = timer

            if isinstance(data["command"], str):
                command = data['command'].lower()

            if isinstance(data["command"], dict):
                if "guess" in data["command"]:
                    if data["command"]["guess"].strip() == "":
                        self.log_event("invalid format", '', room_id)
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
                        this_session.drawn_grid = data["command"]["guess"].strip()
                        # self.log_event('guess', this_session.drawn_grid, room_id) is logged through plugin
                        LOG.debug(f"The drawn grid is {this_session.drawn_grid}")
                        self.sio.emit(
                            "text",
                            {
                                "message": "You saved your current drawn grid successfully.",
                                "room": room_id,
                                "receiver_id": user_id
                            },
                        )

                        if 0 < this_session.current_turn < 25:
                            self.sio.emit(
                                "text",
                                {
                                    "message": "What is your next instruction?",
                                    "room": room_id,
                                    "receiver_id": this_session.player_a["id"]
                                },
                            )
                            self.update_rights(room_id, True, False)
                            return
                        elif this_session.current_turn == 25:
                            self.sio.emit(
                                "text",
                                {
                                    "message": "You ran out of turns!",
                                    "room": room_id,
                                    "receiver_id": this_session.player_a["id"]
                                },
                            )
                            self._command_done(room_id, user_id, data['command'])
                            return

            # If the game hasn't actually started, check for ready_command
            if this_session.current_turn == 0:
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

            # If player_a is done, compare target grid and drawn grid
            if "done" in command:
                self._command_done(room_id, user_id, command)
                return

            # player_a
            if this_session.player_a["id"] == user_id:
                # means that new turn began
                # self.log_event("turn", [], room_id)
                # log event
                self.log_event("clue", {"content": data['command']}, room_id)

                self.sio.emit(
                    "text",
                    {
                        "message": command,
                        "room": room_id,
                        "receiver_id": this_session.player_b["id"],
                    },
                )
                LOG.debug(f"This is turn number  {this_session.current_turn}.")
                this_session.current_turn += 1
                self.log_event('turn', dict(), room_id)
                self.update_rights(room_id, False, True)
                sleep(1)

            # player_b
            elif this_session.player_b["id"] == user_id:
                self.log_event("guess", {"content": data['command']}, room_id)

                # In case the grid is returned as string on the chat area
                if '▢' in command:
                    drawn_grid = self.reformat_drawn_grid(command)
                    this_session.drawn_grid = drawn_grid
                    sleep(1)
                    if this_session.current_turn < 25:
                        self.sio.emit(
                            "text",
                            {
                                "message": "What is your next instruction?",
                                "room": room_id,
                                "receiver_id": this_session.player_a["id"],
                            },
                        )
                        self.update_rights(room_id, True, False)
                        sleep(1)
                        return
                    else:
                        self.log_event("max turns reached", {"content": str(25)}, room_id)
                        self._command_done(room_id, user_id, command)
                else:
                    self.log_event("invalid format", {"content": data['command']}, room_id)
                    self.sio.emit(
                        "text",
                        {
                            "message": "Sorry, but I do not understand this command. Try again.",
                            "room": room_id,
                            "receiver_id": user_id,
                        },
                    )

    def _command_ready(self, room_id, user_id):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.sessions[room_id].players
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

    def start_game(self, room_id):
        this_session = self.sessions[room_id]

        # 1) Set rounds
        this_session.current_turn = 1
        LOG.debug(f"Starting first turn out of 25.")
        self.log_event("round", {"number": this_session.game_round}, room_id)

        # 2) Choose players A and B
        self.sessions[room_id].pick_player_a()
        self.sessions[room_id].pick_player_b()
        for user in this_session.players:
            if user["id"] == this_session.player_a["id"]:
                LOG.debug(f'{user["name"]} is player A.')
            else:
                LOG.debug(f'{user["name"]} is player B.')
        self.log_event('players', {
            "GM": "DrawingBot",
            "Player_1": self.sessions[room_id].player_a["name"],
            "Player_2": self.sessions[room_id].player_b["name"]},
            room_id
        )

        # 3) Load grid
        grid_type = random.choice(['compact', 'random'])
        this_session.grid_type = grid_type
        if grid_type == 'compact' and this_session.all_compact_grids:
            random_grid = this_session.all_compact_grids.get_random_grid()
            this_session.target_grid = random_grid
        else:
            this_session.grid_type = 'random'
            random_grid = this_session.all_random_grids.get_random_grid()
            this_session.target_grid = random_grid
        self.log_event("target grid", {"content": this_session.target_grid}, room_id)
        self.log_event("grid type", {"content": this_session.grid_type}, room_id)

        # 4) Prepare interface
        # Resize screen
        self.move_divider(room_id, 30, 70)
        self.sio.emit(
            "message_command",
            {"command": {"command": "drawing_game_init"}, "room": room_id, "receiver_id": this_session.player_b["id"]},
        )

        # Restart timer
        if this_session.timer:
            this_session.timer.cancel()
        timer = Timer(
            TIMEOUT_TIMER * 60, self.timeout_close_game, args=[room_id]
        )
        timer.start()
        this_session.timer.timer = timer
        self.send_individualised_instructions(room_id)
        self.update_rights(room_id, True, False)
        self.show_item(room_id)

    def send_individualised_instructions(self, room_id):
        this_session = self.sessions[room_id]

        # Display  instructions for player_a
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr_title",
            json={"text": "You are the describer", "receiver_id": this_session.player_a["id"]},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set task instruction title")
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "send_instr",
                    "message": f"{INSTRUCTIONS_A}"
                },
                "room": room_id,
                "receiver_id": this_session.player_a["id"],
            }
        )
        # Display  instructions for player_b
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr_title",
            json={"text": "You have to draw the grid", "receiver_id": this_session.player_b["id"]},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set task instruction title")
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "send_instr",
                    "message": f"{INSTRUCTIONS_B}"
                },
                "room": room_id,
                "receiver_id": this_session.player_b["id"],
            }
        )

    def move_divider(self, room_id, chat_area=50, task_area=50):
        """
        Move the central divider and resize chat and task area
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

    def show_item(self, room_id):
        """
        Display the target grid to player_a and
        keyboard instructions to player_b.
        Hide game board to player_a
        """
        LOG.debug("Show item: Display the grid and task description to the players.")

        this_session = self.sessions[room_id]

        if this_session.target_grid:
            # Display on chat area
            grid = this_session.target_grid.replace('\n', '<br>')
            self.sio.emit(
                "text",
                {
                    "message": f"This is the target grid: <br>{grid}<br><br>You have 25 turns "
                               f"to describe it to the other player.<br><br>Give the first instruction.",
                    "receiver_id": this_session.player_a["id"],
                    "room": room_id,
                    "html": True
                },
            )

            # Display on display area
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/grid_title",
                json={"text": "Target grid", "receiver_id": this_session.player_a["id"]},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "set grid title")
            grid = this_session.target_grid.replace('\n', '<br>')
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "send_grid",
                        "message": f"<br><br>{grid}",
                    },
                    "room": room_id,
                    "receiver_id": this_session.player_a["id"],
                }
            )

            # Display keyboard instructions for player_b
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/grid_title",
                json={"text": "ATTENTION! How to type", "receiver_id": this_session.player_b["id"]},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "set typing instructions title")
            keyboard_instructions = this_session.keyboard_instructions
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "send_keyboard_instructions",
                        "message": f"{keyboard_instructions}",
                    },
                    "room": room_id,
                    "receiver_id": this_session.player_b["id"],
                }
            )

            # Hide game board for player a
            # self._hide_game_board(room_id, this_session.player_a)

            # enable the grid
            response = requests.delete(
                f"{self.uri}/rooms/{room_id}/class/grid-area",
                json={"class": "dis-area", "receiver_id": this_session.player_a["id"]},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "enable grid")

    def update_rights(self, room_id, player_a: bool, player_b: bool):
        this_session = self.sessions[room_id]
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr['id'] != this_session.player_a["id"]:
            curr_usr, other_usr = other_usr, curr_usr
        # update writing rights to player_a (assign or revoke)
        self.set_message_privilege(this_session.player_a["id"], player_a)
        self.check_writing_right(room_id, curr_usr, player_a)
        # update writing rights to other user (assign or revoke)
        self.set_message_privilege(this_session.player_b["id"], player_b)
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

    def process_move(self, room_id, reward: int):
        """Compare grids at the end of each episode and update score."""
        this_session = self.sessions[room_id]
        self.update_reward(room_id, reward)
        self.update_title_points(room_id, reward)
        this_session.game_round += 1
        self.next_round(room_id)

    def update_reward(self, room_id, reward):
        """Compute and keep track of score"""
        score = self.sessions[room_id].points["score"]
        score += reward
        score = round(score, 2)
        self.sessions[room_id].points["score"] = max(0, score)

    def update_title_points(self, room_id, reward):
        """Update displayed score"""
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
        """
        Before a new round starts, remove played instance from list,
        pick a new grid instance and show_item if there are rounds left.
        Otherwise, end the experiment.
        """
        this_session = self.sessions[room_id]
        LOG.debug(f"Starting game round {this_session.game_round}")
        self.log_event("round", {"number": this_session.game_round}, room_id)

        # Remove grid so one instance is not played several times
        if this_session.grid_type == 'compact':
            this_session.all_compact_grids.remove_grid(this_session.target_grid)
        elif this_session.grid_type == 'random':
            this_session.all_random_grids.remove_grid(this_session.target_grid)

        # Get new grid
        this_session.target_grid = this_session.all_compact_grids.get_random_grid()

        # Was this the last game round?
        if self.sessions[room_id].game_round >= 4:
            self.sio.emit(
                "text",
                {
                    "room": room_id,
                    "message": (
                        "The experiment is over 🎉 🎉 thank you very much for your time!"
                    ),
                    "html": True,
                },
            )
            self.confirmation_code(room_id, status='success')
            self.close_game(room_id)
            return
        elif 0 < self.sessions[room_id].game_round < 4:
            # Reset and send keyboard to only player_b
            self.sio.emit(
                "message_command",
                {"command": {"command": "drawing_game_init"}, "room": room_id,
                 "receiver_id": this_session.player_b["id"]}
            )
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
                 "receiver_id": this_session.player_b["id"]}
            )

            # restart round_timer #todo: simplify in function
            LOG.debug("Reset timeout timer")
            if this_session.timer:
                this_session.timer.cancel()
            timer = Timer(
                TIMEOUT_TIMER * 60, self.timeout_close_game, args=[room_id]
            )
            timer.start()
            this_session.timer.timer = timer
            this_session.current_turn = 1

            # Show new grid instance to player_a
            self.show_item(room_id)
            self.update_rights(room_id, player_a=True, player_b=False)

            # reset attributes for the new round
            for usr in self.sessions[room_id].players:
                usr["status"] = "ready"
                usr["msg_n"] = 0

    @staticmethod
    def transform_string_in_grid(string):
        """
        Reformats string returned from player B into a displayable grid
        to be emitted as message (html=true)
        Example:
            formatted_grid = self.transform_string_in_grid(this_session.drawn_grid.upper())
            self.sio.emit(
                "text",
                {
                    "message": f"**CURRENT DRAWN GRID**:<br>{formatted_grid}",
                    "room": room_id,
                    "receiver_id": this_session.player_a,
                    "html": True,
                },
            )
        """
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

    def reformat_drawn_grid(self, grid):
        """Reformat grid so the image is clear"""
        grid = grid.lower()
        grid = grid.replace('\n', ' ')
        return grid

    def _hide_game_board(self, room_id, user_id):
        response = requests.post(
            f"{self.uri}/rooms/{room_id}/class/game-board",
            json={"class": "dis-area", "receiver_id": user_id},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "hide game board")

    def _command_done(self, room_id, user_id, command):
        """Must be sent to end a game round."""
        LOG.debug(command)
        this_session = self.sessions[room_id]

        self.sio.emit(
            "text",
            {
                "message":
                    "Let's check how well you did...",
                "room": room_id,
                "html": True,
            },
        )

        # get the grid for this room and the grid drawn by player_b
        target_grid = this_session.target_grid

        if this_session.drawn_grid:
            drawn_grid = self.transform_string_in_grid(this_session.drawn_grid.upper()).replace('<br>', '\n')
            this_session.drawn_grid = drawn_grid
        else:
            LOG.debug(f"DRAWN GRID is EMPTY")

        LOG.debug(f"TARGET GRID is {this_session.target_grid}")
        LOG.debug(f"DRAWN GRID is {this_session.drawn_grid}")

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

        if target_grid != drawn_grid:
            result = 'LOST'
            points = 0

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
            self.log_event("correct guess", {"content": drawn_grid}, room_id)
            result = 'WON'
            points = 1

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

    def confirmation_code(self, room_id, status):
        """Generate token that will be sent to each player."""
        LOG.debug("Triggered confirmation_code")
        confirmation_token = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        points = self.sessions[room_id].points
        # post confirmation token to logs
        self.log_event(
            "confirmation_log",
            {"status_txt": status, "token": confirmation_token, "reward": points},
            room_id,
        )

        # Or check in wordle how the user is given the link to prolific
        #todo: why is the message not always displayed?
        self.sio.emit(
            "text",
            {
                "message": f"This is your token:  **{confirmation_token}** <br>"
                           "Please remember to save it"
                           "before you close this browser window. "
                ,
                "room": room_id,
                "html": True
            },
        )

    def _show_prolific_link(self, room, receiver, token=None):

        if token is None:
            # use the username
            response = requests.get(
                f"{self.uri}/users/{receiver}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "get user")
            token = response.json().get("name", f"{room}–{receiver}")

        url = f"{PROLIFIC_URL}{token}"
        self.sio.emit(
            "text",
            {"message": f"Please return to <a href='{url}'>{url}</a> to complete your submission.",
             "room": room,
             "html": True,
             "receiver_id": receiver
             }
        )

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        LOG.debug(f"Triggered close game for room {room_id}")

        #todo: why is the message not always displayed?
        self.sio.emit(
            "text",
            {
                "message": "The room is closing, see you next time 👋",
                "room": room_id
            }
        )

        self.sessions[room_id].game_over = True
        self.room_to_read_only(room_id)
        self.sessions.clear_session(room_id)

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

        # remove users from room to repeated avoid timeout call
        if room_id in self.sessions:
            for usr in self.sessions[room_id].players:
                response = requests.get(
                    f"{self.uri}/users/{usr['id']}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(f"Could not get user: {response.status_code}")
                    response.raise_for_status()
                etag = response.headers["ETag"]

                response = requests.delete(
                    f"{self.uri}/users/{usr['id']}/rooms/{room_id}",
                    headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(
                        f"Could not remove user from task room: {response.status_code}"
                    )
                    response.raise_for_status()
                logging.debug("Removing user from task room was successful.")

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
