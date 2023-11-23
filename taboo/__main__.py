from collections import defaultdict
from .config import *
import logging
import os
import string
import json

import requests

from typing import Dict
from templates import TaskBot
from time import sleep
from threading import Timer

import random

LOG = logging.getLogger(__name__)

TIMEOUT_TIMER = 1  # minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 3  # minutes if a user is alone in a room

STARTING_POINTS = 0


class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()
        self.left_room = dict()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER * 60, self.function, args=[self.room_id, "timeout"]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.info("reset timer")

    def cancel(self):
        self.timer.cancel()

    def cancel_all_timers(self):
        self.timer.cancel()
        for timer in self.left_room.values():
            timer.cancel()

    def user_joined(self, user):
        timer = self.left_room.get(user)
        if timer is not None:
            self.left_room[user].cancel()

    def user_left(self, user):
        self.left_room[user] = Timer(
            LEAVE_TIMER * 60, self.function, args=[self.room_id, "user_left"]
        )
        self.left_room[user].start()


class Session:
    def __init__(self):
        self.players = list()
        self.explainer = None
        self.word_to_guess = None
        self.game_over = False
        self.guesser = None
        self.timer = None
        self.points = {
            "score": STARTING_POINTS,
            "history": [
                {"correct": 0, "wrong": 0, "warnings": 0}
            ]
        }
        self.played_words = []
        self.rounds_left = 3

    def close(self):
        pass

    def pick_explainer(self):
        self.explainer = random.choice(self.players)["id"]

    def pick_guesser(self):
        for player in self.players:
            if player["id"] != self.explainer:
                self.guesser = player["id"]


class SessionManager(defaultdict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)


class TabooBot(TaskBot):
    """Bot that manages a taboo game.

    - Bot enters a room and starts a taboo game as soon as 2 participants are
      present.
    - Game starts: select a word to guess, assign one of the participants as
      explainer, present the word and taboo words to her
    - Game is in progress: check for taboo words or solutions
    - Solution has been said: end the game, record the winner, start a new game.
    - When new users enter while the game is in progress: make them guessers.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.sessions = SessionManager(Session)
        self.taboo_data = self.get_taboo_data()
        self.guesser_instructions = self.read_guesser_instructions()
        self.explainer_instructions = self.read_explainer_instructions()
        self.waiting_room = None


    def read_guesser_instructions(self):
        return guesser_task_description.read_text()

    def read_explainer_instructions(self):
        return explainer_task_description.read_text()

    def get_taboo_data(self, difficulty_level=None):
        # Get all instances
        all_taboo_data = json.loads(all_words.read_text())
        if difficulty_level is None:
            # select one random difficulty level
            random_level = random.randint(0, 2)
            print(random_level)
            experiment = all_taboo_data["experiments"][random_level]
        if difficulty_level == 'beginner':
            experiment = all_taboo_data["experiments"][0]
        elif difficulty_level == 'intermediate':
            experiment = all_taboo_data["experiments"][1]
        elif difficulty_level == 'advanced':
            experiment = all_taboo_data["experiments"][2]
        # Select one random experiment and instance
        index = random.randint(0, 18)
        game = experiment["game_instances"][index]
        # {'game_id': 0, 'target_word': 'length', 'related_word': ['stretch', 'plain', 'expansion']}
        # game_id = game['game_id']
        # target_word = game['target_word']
        # related_words = game['related_word']
        return game

    @staticmethod
    def message_callback(success, error_msg="Unknown Error"):
        if not success:
            LOG.error(f"Could not send message: {error_msg}")
            exit(1)
        LOG.debug("Sent message successfully.")

    def on_task_room_creation(self, data):
        room_id = data["room"]
        task_id = data["task"]

        logging.debug(f"A new task room was created with id: {data['task']}")
        logging.debug(f"This bot is looking for task id: {self.task_id}")

        if task_id is not None and task_id == self.task_id:
            # reduce height of sidebar
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/sidebar",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"attribute": "style", "value": f"height: 90%"}
            )

            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])

            # create session for these users
            # self.sessions.create_session(room_id)
            # timer = RoomTimer(self.timeout_close_game, room_id)
            # self.sessions[room_id].timer = timer

            for usr in data["users"]:
                self.sessions[room_id].players.append(
                    {**usr, "role": None, "status": "joined"}
                )

            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "letting task bot join room")

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

                # self.images_per_room.get_image_pairs(room_id)
                # self.players_per_room[room_id] = []
                # for usr in data["users"]:
                #     self.players_per_room[room_id].append(
                #         {**usr, "msg_n": 0, "status": "joined"}
                #     )
                # self.last_message_from[room_id] = None
                #
                # # register ready timer for this room
                # self.timers_per_room[room_id] = RoomTimers()
                # self.timers_per_room[room_id].ready_timer = Timer(
                #     TIME_READY * 60,
                #     self.sio.emit,
                #     args=[
                #         "text",
                #         {
                #             "message": "Are you ready? "
                #                        "Please type **/ready** to begin the game.",
                #             "room": room_id,
                #             "html": True,
                #         },
                #     ],
                # )
                self.sio.emit(
                    "text",
                        {
                            "message": "Are you ready? "
                                       "Please type **/ready** to begin the game.",
                            "room": room_id,
                            "html": True,
                        },
                )
                # self.timers_per_room[room_id].ready_timer.start()

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    LOG.error(
                        f"Could not let taboo bot join room: {response.status_code}"
                    )
                    response.raise_for_status()
                LOG.debug("Sending taboo bot to new room was successful.")

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            # if room_id in self.sessions:
            #     # read out task greeting #todo: read from file
            #     message = "Type 'ready' to start the game!"
            #     self.sio.emit(
            #             "text", {"message": message, "room": room_id, "html": True}
            #         )
        @self.sio.event
        def user_message(data):
            LOG.debug("Received a user_message.")
            LOG.debug(data)

            user = data["user"]
            message = data["message"]
            room_id = data["room"]
            self.sio.emit(
                "text", {"message": message, "room": room_id, }
            )

        @self.sio.event
        def command(data):
            """
            Parse user commands, which are either messages,intercepted
            and returned as commands or actual commands (typed with a preceding '/').
            """
            LOG.debug(f"Received a command from {data['user']['name']}.")

            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if user_id == self.user:
                return

            this_session = self.sessions[room_id]
            # this_session.timer.reset()
            word_to_guess = this_session.word_to_guess

            if 'ready' in data['command']:
                # self.sio.emit(
                #     "text",
                #     {
                #         "message": f"You typed READY.",
                #         "room": room_id,
                #     },
                # )
                self._command_ready(room_id, user_id)
                return

            # explainer
            if this_session.explainer == user_id:
                LOG.debug(f"{data['user']['name']} is the explainer.")
                command = data['command']
                logging.debug(
                    f"Received a command from {data['user']['name']}: {data['command']}"
                )

                # check whether the user used a forbidden word
                forbidden_words = self.taboo_data['related_word']
                # self.sio.emit(
                #     "text",
                #     {
                #         "message": f"the taboo words are {forbidden_words}",
                #         "room": room_id,
                #         "receiver_id": this_session.explainer,
                #     },
                # )
                for taboo_word in forbidden_words:
                    if taboo_word.lower() in command.lower():
                        self.sio.emit(
                            "text",
                            {
                                "message": f"You used the taboo word '{taboo_word}'! GAME OVER :(",
                                "room": room_id,
                                "receiver_id": this_session.explainer,
                            },
                        )
                        self.sio.emit(
                            "text",
                            {
                                "message": f"{data['user']['name']} used a taboo word. You both lose!",
                                "room": room_id,
                                "receiver_id": this_session.guesser,
                            },
                        )
                        self.process_move(room_id, -1)
                        return
                    else:
                        self.sio.emit(
                            "text",
                            {
                                "message": f"CLUE: {command}",
                                "room": room_id,
                                "receiver_id": this_session.guesser,
                            },
                        )
                        return

                # check whether the user used the word to guess
                if word_to_guess.lower() in command:
                    self.sio.emit(
                        "text",
                        {
                            "message": f"You used the word to guess '{word_to_guess}'! GAME OVER",
                            "room": room_id,
                            "receiver_id": this_session.explainer,
                        },
                    )
                    self.sio.emit(
                        "text",
                        {
                            "message": f"{data['user']['name']} used the word to guess. You both lose!",
                            "room": room_id,
                            "receiver_id": this_session.guesser,
                        },
                    )
                    self.process_move(room_id, -1)
                    return

            # Check if user is guesser
            elif this_session.guesser == user_id:
                LOG.debug(f"{data['user']['name']} is the guesser.")
                command = data['command'].lower()
                logging.debug(
                    f"Received a command from {data['user']['name']}: {data['command']}"
                )

                # Check that only one-word guesses are used
                # if len(command.split()) > 1:
                #     self.sio.emit(
                #         "text",
                #         {
                #             "message": "You need to use one word only. You lost your turn",
                #             "room": room_id,
                #             "receiver_id": this_session.guesser
                #         },
                #     )
                #     self.sio.emit(
                #         "text",
                #         {
                #             "message": "Invalid guess (it contained more than one word).",
                #             "room": room_id,
                #             "receiver_id": this_session.explainer
                #         },
                #     )
                #     self.process_move(room_id, 0)

                if word_to_guess.lower() in command:
                    self.sio.emit(
                        "text",
                        {
                            "message": f"GUESS: '{command}' was correct. You both win!",
                            "room": room_id,
                        },
                    )
                    self.process_move(room_id, 1)
                else:
                    self.sio.emit(
                        "text",
                        {
                            "message": f"GUESS: {command}",
                            "room": room_id,
                            "receiver_id": this_session.explainer
                        },
                    )
                    self.sio.emit(
                        "text",
                        {
                            "message": f"'{command}' was not correct.",
                            "room": room_id,
                            "receiver_id": this_session.guesser
                        },
                    )
                    self.process_move(room_id, 0)

        @self.sio.event
        def status(data):
            """Triggered when a user enters or leaves a room."""
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

            # someone joined waiting room
            if room_id == self.waiting_room:
                if data["type"] == "join":
                    self.sio.emit(
                        "text",
                        {
                            "message": "Somebody joined the waiting room",
                            "room": room_id,
                        },
                    )
            else:
                # automatically creates a new session if not present
                this_session = self.sessions[room_id]

                # don't do this for the bot itself
                if user["id"] == self.user:
                    return

                # someone joined a task room
                if event == "join":
                    # inform everyone about the join event
                    self.sio.emit(
                        "text",
                        {
                            "message": f"{user['name']} has joined the game.",
                            "room": room_id,
                        },
                    )

                    # this_session.players.append({**user, "status": "joined", "wins": 0})

                    if len(this_session.players) < 2:
                        self.sio.emit(
                            "text",
                            {"message": "Let's wait for more players.", "room": room_id},
                        )
                    else:
                        # start a game
                        # 1) Choose a word
                        this_session.word_to_guess = self.taboo_data['target_word']
                        # 2) Choose an explainer and a guesser
                        this_session.pick_explainer()
                        this_session.pick_guesser()
                        self.show_instructions(room_id)
                        self.sio.emit(
                            "text",
                            {
                                "message": "Type 'ready' to begin the game.",
                                "room": room_id,
                            },
                        )

                        # # 3) Tell the explainer about the word
                        # word_to_guess = this_session.word_to_guess
                        # taboo_words = ", ".join(self.taboo_data['related_word'])
                        # self.sio.emit(
                        #     "text",
                        #     {
                        #         "message": f"Your task is to explain the word '{word_to_guess}'. You cannot use the following words: {taboo_words}",
                        #         "room": room_id,
                        #         "receiver_id": this_session.explainer,
                        #     },
                        # )
                        # # 4) Tell everyone else that the game has started
                        # for player in this_session.players:
                        #     if player["id"] != this_session.explainer:
                        #         self.sio.emit(
                        #             "text",
                        #             {
                        #                 "message": "The game has started. Try to guess the word!",
                        #                 "room": room_id,
                        #                 "receiver_id": this_session.guesser,
                        #             },
                        #         )
                elif event == "leave":
                    self.sio.emit(
                        "text",
                        {"message": f"{user['name']} has left the game.", "room": room_id},
                    )

                    # remove this user from current session
                    this_session.players = list(
                        filter(
                            lambda player: player["id"] != user["id"], this_session.players
                        )
                    )

                    if len(this_session.players) < 2:
                        self.sio.emit(
                            "text",
                            {
                                "message": "You are alone in the room, let's wait for some more players.",
                                "room": room_id,
                            },
                        )

        @self.sio.event
        def text_message(data):
            """Triggered when a text message is sent.
            Check that it didn't contain any forbidden words if sent
            by explainer or whether it was the correct answer when sent
            by a guesser.
            """
            LOG.debug(f"Received a message from {data['user']['name']}.")

            room_id = data["room"]
            user_id = data["user"]["id"]

            this_session = self.sessions[room_id]
            # this_session.timer.reset()
            word_to_guess = this_session.word_to_guess

            # do not process commands from itself
            if user_id == self.user:
                return

            # explainer
            if this_session.explainer == user_id:
                LOG.debug(f"{data['user']['name']} is the explainer.")
                message = data["message"]
                # check whether the user used a forbidden word
                for taboo_word in self.taboo_data['related_word']:
                    if taboo_word.lower() in message.lower():
                        self.sio.emit(
                            "text",
                            {
                                "message": f"You used the taboo word {taboo_word}! GAME OVER :(",
                                "room": room_id,
                                "receiver_id": this_session.explainer,
                            },
                        )
                        self.sio.emit(
                            "text",
                            {
                                "message": f"{data['user']['name']} used a taboo word. You both lose!",
                                "room": room_id,
                                "receiver_id": this_session.guesser,
                            },
                        )
                        self.process_move(room_id, 0)

                # check whether the user used the word to guess
                if word_to_guess.lower() in message:
                    self.sio.emit(
                        "text",
                        {
                            "message": f"You used the word to guess '{word_to_guess}'! GAME OVER",
                            "room": room_id,
                            "receiver_id": this_session.explainer,
                        },
                    )
                    self.sio.emit(
                        "text",
                        {
                            "message": f"{data['user']['name']} used the word to guess. You both lose!",
                            "room": room_id,
                            "receiver_id": this_session.guesser,
                        },
                    )

                    self.process_move(room_id, 0)
            # Guesser guesses word
            elif word_to_guess.lower() in data["message"].lower():
                self.sio.emit(
                    "text",
                    {
                        "message": f"{word_to_guess} was correct! YOU WON :)",
                        "room": room_id,
                        "receiver_id": this_session.guesser
                    },
                )
                self.sio.emit(
                    "text",
                    {
                        "message": f"{data['user']['name']} guessed the word. You both win :)",
                        "room": room_id,
                        "receiver_id": this_session.explainer,
                    },
                )
                self.process_move(room_id, 1)

    def _command_ready(self, room_id, user_id):
        """Must be sent to begin a conversation."""
        # ex_players =  [{'id': 19, 'name': 'user_0', 'role': None, 'status': 'joined'},
        # {'id': 20, 'name': 'user_1', 'role': None, 'status': 'joined'}, {'id': 20, 'name': 'user_1', 'status': 'joined', 'wins': 0}]
        # self.sio.emit(
        #     "text",
        #     {
        #         "message": f"_command_ready is triggered",
        #         "room": room_id,
        #     },
        # )

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
            # Remind the other user
            self.sio.emit(
                "text",
                    {
                        "message": "Your partner is ready. Please, type 'ready'!",
                        "room": room_id,
                        "receiver_id": other_usr["id"],
                    },
            )
        # the other player was already ready
        else:
            # both users are ready and the game begins
            self.sio.emit(
                "text",
                {"message": "Woo-Hoo! The game will begin now.", "room": room_id},
            )
            sleep(1)
            self.start_game(room_id)

    def start_game(self, room_id):
        this_session = self.sessions[room_id]
        # self.sio.emit(
        #     "text",
        #     {"message": "start_game was triggered.", "room": room_id},
        # )
        # 3) Tell the explainer about the word
        word_to_guess = this_session.word_to_guess
        taboo_words = ", ".join(self.taboo_data['related_word'])
        self.sio.emit(
            "text",
            {
                "message": f"Your task is to explain the word '{word_to_guess}'. You cannot use the following words: {taboo_words}",
                "room": room_id,
                "receiver_id": this_session.explainer,
            },
        )
        # 4) Tell everyone else that the game has started
        for player in this_session.players:
            if player["id"] != this_session.explainer:
                self.sio.emit(
                    "text",
                    {
                        "message": "The game has started. Try to guess the word!",
                        "room": room_id,
                        "receiver_id": this_session.guesser,
                    },
                )

    def remove_punctuation(text: str) -> str:
        text = text.translate(str.maketrans("", "", string.punctuation))
        return text

    def timeout_close_game(self, room_id, status):
        while self.sessions[room_id].game_over is False:
            self.sio.emit(
                "text",
                {"message": "The room is closing because of inactivity", "room": room_id},
            )
            # self.confirmation_code(room_id, status)
            self.close_game(room_id)

    def close_game(self, room_id):
        """Erase any data structures no longer necessary."""
        self.sio.emit(
            "text",
            {"message": "This room is closing, see you next time 👋", "room": room_id},
        )

        self.sessions[room_id].game_over = True
        # self.room_to_read_only(room_id)
        self.sessions.clear_session(room_id)

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
        # was this the last game round?
        if self.sessions[room_id].rounds_left < 1:
            self.sio.emit(
                "text",
                {"message": "The experiment is over! Thank you for participating :)",
                 "room": room_id},
            )
            self.close_game(room_id)
        else:
            self.sio.emit(
                "text",
                {"message": "Give a new hint",
                 "room": room_id,
                 "receiver_id": this_session.explainer}
            )
            self.sio.emit(
                "text",
                {"message": "Wait for a new hint",
                 "room": room_id,
                 "receiver_id": this_session.guesser}
            )

    def validate_input(self, room_id):
        pass

    def process_move(self, room_id, reward: int):
        this_session = self.sessions[room_id]
        this_session.played_words.append(this_session.word_to_guess)
        if reward == 0:
            this_session.rounds_left -= 1
        elif reward == 1 or reward == -1:
            this_session.rounds_left = 0
        self.update_reward(room_id, reward)
        self.update_title_points(room_id, reward)
        self.next_round(room_id)

    def show_instructions(self, room_id):
        """Update the task description for the players."""
        LOG.debug("Update the task description for the players.")
        # guarantee fixed user order - necessary for update due to rejoin
        users = sorted(self.sessions[room_id].players, key=lambda x: x["id"])

        if self.guesser_instructions and self.explainer_instructions is not None:
            self.send_individualised_instructions(room_id)
            # self.send_same_instructions(room_id)

        else:
            # Print task title for everyone
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr_title",
                json={"text": TASK_TITLE},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                LOG.error(
                    f"Could not set task instruction title: {response.status_code}"
                )
                response.raise_for_status()
            # Print no-guesser_instructions for everyone
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr",
                json={"text": "No guesser_instructions provided"},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                LOG.error(
                    f"Could not set task guesser_instructions: {response.status_code}"
                )
                response.raise_for_status()

    def send_same_instructions(self, room_id):
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr_title",
            json={"text": TASK_TITLE},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(
                f"Could not set task instruction title: {response.status_code}"
            )
            response.raise_for_status()

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr",
            json={"text": self.guesser_instructions},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction: {response.status_code}")
            response.raise_for_status()

    def send_individualised_instructions(self, room_id):
        this_session = self.sessions[room_id]

        # Send explainer_ instructions to explainer
        response = requests.patch(f"{self.uri}/rooms/{room_id}/text/instr_title",
                                  json={"text": "Explain the taboo word", "receiver_id": this_session.explainer},
                                  headers={"Authorization": f"Bearer {self.token}"},
                                  )
        if not response.ok:
            LOG.error(
                f"Could not set task instruction title: {response.status_code}"
            )
            response.raise_for_status()

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr",
            json={"text": f"{self.explainer_instructions}", "receiver_id": this_session.explainer},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction: {response.status_code}")
            response.raise_for_status()

        # Send guesser_instructions to guesser
        response = requests.patch(f"{self.uri}/rooms/{room_id}/text/instr_title",
                                  json={"text": "Guess the taboo word", "receiver_id": this_session.guesser},
                                  headers={"Authorization": f"Bearer {self.token}"},
                                  )
        if not response.ok:
            LOG.error(
                f"Could not set task instruction title: {response.status_code}"
            )
            response.raise_for_status()

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr",
            json={"text": f"{self.guesser_instructions}", "receiver_id": this_session.guesser},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction: {response.status_code}")
            response.raise_for_status()


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = TabooBot.create_argparser()

    if "WAITING_ROOM" in os.environ:
        waiting_room = {"default": os.environ["WAITING_ROOM"]}
    else:
        waiting_room = {"required": True}

    parser.add_argument(
        "--taboo_data",
        help="json file containing words",
        default=os.environ.get("TABOO_DATA"),
    )
    parser.add_argument(
        "--waiting_room",
        type=int,
        help="room where users await their partner",
        **waiting_room
    )
    args = parser.parse_args()

    # create bot instance
    taboo_bot = TabooBot(args.token, args.user, args.task, args.host, args.port)
    taboo_bot.waiting_room = args.waiting_room
    # taboo_bot.taboo_data = args.taboo_data
    # connect to chat server
    taboo_bot.run()
