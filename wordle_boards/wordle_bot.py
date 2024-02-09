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

from templates import TaskBot
from .dataloader import Dataloader
from .config import (
    COLOR_MESSAGE,
    SEED,
    STANDARD_COLOR,
    WARNING_COLOR,
    TASK_GREETING,
    TASK_TITLE,
    LEAVE_TIMER,
    # TIME_ROUND,
    TIMEOUT_TIMER,
    TIME_WAITING_ROOM,
    VALID_WORDS,
    WORDLE_WORDS,
    WORDS_PER_ROOM,

    GUESSER_HTML,
    CRITIC_HTML,
    CLUE_MODE,
    CRITIC_MODE,

    INPUT_FIELD_UNRESP_CRITIC,
    INPUT_FIELD_UNRESP_GUESSER


)


LOG = logging.getLogger(__name__)

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
        self.words = Dataloader(WORDLE_WORDS, WORDS_PER_ROOM)
        self.word_to_guess = None
        self.players = list()

        self.points = {
            "score": 0,
            "history": [
                {"correct": 0, "wrong": 0, "warnings": 0}
            ]
        }
        self.game_over = False

        self.guesser = None
        self.critic = None

        self.turn = None
        self.critic_provided = False
        self.proposal_submitted = False

        self.timer = None

        self.round_guesses_history = []

        self.button_number = 0

    def close(self):
        self.timer.cancel_all_timers()


class SessionManager(dict):
    waiting_room_timers = dict()

    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)


class WordleBot2 (TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sessions = SessionManager()

        # ensure all the words from the initial image file are guessable
        # with open(DATA_PATH) as infile:
        #     self.wordlist.update(line.split("\t")[0] for line in infile)

        # WHAT IS THIS?
        self.received_waiting_token = set()

        # self.waiting_timer = None

    def post_init(self, waiting_room, version):
        """save extra variables after the __init__() method has been called"""
        self.waiting_room = waiting_room
        self.version = version

    def on_task_room_creation(self, data):
        """Triggered after a new task room is created."""
        room_id = data["room"]
        task_id = data["task"]

        LOG.debug(f"A new task room was created with id: {data['task']}")
        LOG.debug(f"This bot is looking for task id: {self.task_id}")

        if task_id is not None and task_id == self.task_id:
            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])

            self.log_event("bot_version_log", {"version": self.version}, room_id)

            # create image items for this room
            LOG.debug("Create data for the new task room...")
            LOG.debug(data)

            self.move_divider(room_id, 20, 80)

            self.sessions.create_session(room_id)

            timer = RoomTimer(self.timeout_close_game, room_id)
            self.sessions[room_id].timer = timer

            LOG.debug(self.sessions[room_id].words)

            for usr in data["users"]:
                self.sessions[room_id].players.append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )
                # cancel waiting-room-timers
                if usr["id"] in self.sessions.waiting_room_timers:
                    logging.debug(f"Cancelling waiting room timer for user {usr['id']}")
                    self.sessions.waiting_room_timers[usr["id"]].cancel()
                    self.sessions.waiting_room_timers.pop(usr["id"])

            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "let wordle bot join room")

            # Assign roles
            self.assign_roles(room_id)

            self.send_instr(room_id)

            # Guesser can't send messages
            self.set_message_privilege(room_id, self.sessions[room_id].guesser, False)
            self.make_input_field_unresponsive(room_id, self.sessions[room_id].guesser)

            if self.version == "critic":
                self.set_message_privilege(room_id, self.sessions[room_id].critic, False)
                self.make_input_field_unresponsive(room_id, self.sessions[room_id].critic)

    def assign_roles(self, room_id):
        # assuming there are 1/2 players
        session = self.sessions[room_id]

        guesser_index = random.randint(0, len(session.players) - 1)
        if self.version == "critic":
            critic_index = 1 - guesser_index
            session.players[critic_index]["role"] = "critic"
            session.critic = session.players[critic_index]["id"]
            self.log_event("player_critic", session.players[critic_index], room_id)

        session.players[guesser_index]["role"] = "guesser"
        session.guesser = session.players[guesser_index]["id"]
        self.log_event("player_guesser", session.players[guesser_index], room_id)

    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]
            if room_id in self.sessions:

                # read out task greeting
                for line in TASK_GREETING:
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                color=STANDARD_COLOR, message=line
                            ),
                            "room": room_id,
                            "html": True,
                        },
                    )
                    sleep(0.5)

                self.send_message_to_user(STANDARD_COLOR, "Are you ready?"
                                                              " Once you click on 'yes', you will see the board. <br> <br>"
                                                              "<button class='message_button' onclick=\"confirm_ready('yes')\">YES</button> "
                                                              "<button class='message_button' onclick=\"confirm_ready('no')\">NO</button>",
                                              room_id)

        @self.sio.event
        def status(data):
            """Triggered if a user enters or leaves a room."""
            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{data['user']['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(task, "get task")
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

            room_id = data["room"]
            # someone joined waiting room
            if room_id == self.waiting_room:
                if data["type"] == "join":
                    # hotfix by Sebastiano
                    if data['user']['id'] not in self.sessions.waiting_room_timers:
                        # start no_partner timer
                        timer = Timer(
                            TIME_WAITING_ROOM * 60,
                            self.timeout_waiting_room,
                            args=[data["user"]],
                        )
                        timer.start()
                        logging.debug(f"Started a waiting room/no partner timer: {TIME_WAITING_ROOM}")
                        self.sessions.waiting_room_timers[data['user']['id']] = timer
                return

                    # Pay for waiting time?
                    # self.send_message_to_user(STANDARD_COLOR,
                    #                     f"If nobody shows up within"
                    #                     f"{TIME_WAITING_ROOM} minutes, I will give"
                    #                     f"you a token, so that you "
                    #                     f"can get paid for your waiting time.", room_id, data['user']['id'])


            # someone joined a task room
            elif room_id in self.sessions:
                if self.version == "critic":
                    this_session = self.sessions[room_id]
                    curr_usr, other_usr = this_session.players
                    if curr_usr["id"] != data["user"]["id"]:
                        curr_usr, other_usr = other_usr, curr_usr
                    if data["type"] == "join":
                        if self.sessions[room_id].game_over is False:
                            # if data['user']["status"] != "ready":
                            if curr_usr["status"] != "ready":
                                self.reload_state(room_id, data["user"]["id"], only_instr=True)
                            else:
                                self.reload_state(room_id, data["user"]["id"])

                            # inform the other user about join event
                            self.send_message_to_user(STANDARD_COLOR,
                                                  f"{data['user']['name']} has joined the game.", room_id, other_usr["id"]
                                                  )

                            self.sessions[room_id].timer.user_joined(curr_usr["id"])
                            # cancel timer
                            logging.debug(
                                f"Cancelling Timer: left room for user {curr_usr['name']}"
                            )
                            timer = this_session.timer.left_room.get(curr_usr["id"])
                            if timer is not None:
                                timer.cancel()

                    elif data["type"] == "leave":
                        if self.sessions[room_id].game_over is False:
                            self.send_message_to_user(STANDARD_COLOR,
                                f"{data['user']['name']} has left the game. "
                                f"Please wait a bit, your partner may rejoin.", room_id, other_usr["id"])

                            # start timer since user left the room
                            logging.debug(
                                f"Starting Timer: left room for user {curr_usr['name']}"
                            )
                            self.sessions[room_id].timer.user_left(curr_usr["id"])

                else:
                    # standard/clue version -> only 1 player
                    # timers needed for 1 user??
                    if data["type"] == "join":
                        # if data['user']["status"] != "ready":
                        if self.sessions[room_id].players[0]["status"] != "ready":
                            self.reload_state(room_id, data["user"]["id"], only_instr=True)
                        else:
                            self.reload_state(room_id, data["user"]["id"])
                        self.sessions[room_id].timer.user_joined(data["user"]["id"])
                    elif data["type"] == "leave":
                        self.sessions[room_id].timer.user_left(data["user"]["id"])

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

            self.sessions[room_id].timer.reset()

            # if the message is part of the main discussion count it
            for usr in self.sessions[room_id].players:
                if usr["id"] == user_id and usr["status"] == "ready":
                    usr["msg_n"] += 1

            if user_id == self.sessions[room_id].critic:
                self.log_event("CRITIC_RATIONALE", {"content": data['message']}, room_id)
                self.sessions[room_id].turn = self.sessions[room_id].guesser
                self.sessions[room_id].proposal_submitted = False
                self.sessions[room_id].critic_provided = True
                self.set_message_privilege(room_id, self.sessions[room_id].critic, False)
                self.make_input_field_unresponsive(room_id, self.sessions[room_id].critic)

                self.set_message_privilege(room_id, self.sessions[room_id].guesser, True)


        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if str(user_id) == self.user:
                return

            if room_id in self.sessions:
                # only accept commands from the javascript
                # frontend (commands are dictionaries)
                if isinstance(data["command"], dict):
                    if "guess" in data["command"]:
                        if data["command"]["guess"].strip() == "":
                            self.log_event("EMPTY_GUESS", {}, room_id)
                            self.send_message_to_user(WARNING_COLOR, "**You need to provide a guess!**",
                                                      room_id,
                                                      user_id,
                                                      )
                        else:
                            if not self.sessions[room_id].proposal_submitted:

                                self._command_guess(room_id, user_id, data["command"])
                            else:
                                self.send_message_to_user(WARNING_COLOR,
                                                          "You have already submitted a proposal! "
                                                          "Let's wait for the critic.",
                                                          room_id,
                                                          user_id,
                                                          )


                    elif data["command"]["event"] == "confirm_ready":
                        if data["command"]["answer"] == "yes":
                            self._command_ready(room_id, user_id)
                        elif data["command"]["answer"] == "no":
                            self.send_message_to_user(STANDARD_COLOR,
                            "OK, read the instructions carefully and click on <yes> once you are ready.",
                                                      room_id,
                                                      user_id,
                                                      )
                        return
                    elif data["command"]["event"] == "critic_feedback":
                        if data["command"]["answer"] == "agree":
                            self.send_message_to_user(STANDARD_COLOR, "Critic agrees with the proposed guess, wait for his rationale.",
                                                      room_id, self.sessions[room_id].guesser
                                                      )
                            self.log_event("CRITIC_AGREEMENT", {"content": True}, room_id)

                        elif data["command"]["answer"] == "disagree":
                            self.send_message_to_user(STANDARD_COLOR, "Critic doesn't agree with the proposed guess, wait for his rationale.",
                                                      room_id, self.sessions[room_id].guesser
                                                      )
                            self.log_event("CRITIC_AGREEMENT", {"content": False}, room_id)

                        self.send_message_to_user(STANDARD_COLOR, f"Ok! Please, provide your critic"
                        f"<script> document.getElementById('Button{self.sessions[room_id].button_number}').disabled = true;</script>"
                        f"<script> document.getElementById('Button{self.sessions[room_id].button_number + 1}').disabled = true;</script>",
                                                  room_id, self.sessions[room_id].critic)

                        self.sessions[room_id].button_number += 2


                        # self.set_message_privilege(room_id, self.sessions[room_id].critic, True)
                        # self.give_writing_rights(room_id, self.sessions[room_id].critic)
                        #
                        # self.sessions[room_id].turn = self.sessions[room_id].critic


                # bot has no user defined commands
                else:
                    self.send_message_to_user(STANDARD_COLOR,
                                              "Sorry, but I do not understand this command.",
                                              room_id,
                                              user_id,
                                              )

    def _command_guess(self, room_id, user_id, command):

        LOG.debug(command)

        self.sessions[room_id].timer.reset()

        # get the wordle for this room and the guess from the user
        word = self.sessions[room_id].word_to_guess

        guess = command["guess"]

        remaining_guesses = command["remaining"]

        # make sure the guess has the right length
        if len(word) != len(guess):
            self.log_event("INVALID_LENGTH", {"content": guess},  room_id)
            self.send_message_to_user(WARNING_COLOR,
                                      f"Unfortunately this word is not valid. "
                                      f"Your guess needs to have {len(word)} letters.",
                                      room_id,
                                      user_id,
                                      )

            self.sio.emit(
                "message_command",
                {
                    "command": {"command": "unsubmit"},
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )
            return

        # make sure it's a good guess
        if guess not in VALID_WORDS:
            self.log_event("INVALID_WORD", {"content": guess},  room_id)
            self.send_message_to_user(WARNING_COLOR,
                        "**Unfortunately this word is not valid. "
                        "Make sure that there aren't any typos**",
                                      room_id,
                                      user_id,
                                      )
            self.sio.emit(
                "message_command",
                {
                    "command": {"command": "unsubmit"},
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )
            return

        if not self.sessions[room_id].critic_provided and self.version == "critic":
            self.sessions[room_id].proposal_submitted = True
            self.send_message_to_user(STANDARD_COLOR, f"PROPOSAL: <b> {guess.upper()} </b>", room_id, self.sessions[room_id].critic)

            self.send_message_to_user(STANDARD_COLOR, f"Your proposal <b> {guess.upper()} </b> was submitted.", room_id,
                                      self.sessions[room_id].guesser)
            self.send_message_to_user(STANDARD_COLOR, f"Now let's wait for the critic!", room_id, self.sessions[room_id].guesser)

            self.set_message_privilege(room_id, self.sessions[room_id].critic, True)
            self.give_writing_rights(room_id, self.sessions[room_id].critic)

            self.sessions[room_id].turn = self.sessions[room_id].critic

            self.log_event("PROPOSAL", {"content": guess},  room_id)

            self.sio.emit(
                "message_command",
                {
                    "command": {"command": "unsubmit"},
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )

            LOG.debug(f"Button{self.sessions[room_id].button_number}")
            self.send_message_to_user(STANDARD_COLOR,
                                      f" Do you agree with the proposed guess? Click on the corresponding button. <br> <br>"
                                      f"<button class='message_button' id='Button{self.sessions[room_id].button_number}' onclick=\"critic_feedback('agree')\">agree</button> "
                                      f"<button class='message_button' id='Button{self.sessions[room_id].button_number + 1}' onclick=\"critic_feedback('disagree')\">disagree</button>",
                                      room_id, self.sessions[room_id].critic)
            return

        self.log_event("turn", dict(), room_id)
        self.log_event("GUESS", {"content": guess}, room_id)
        self.sessions[room_id].round_guesses_history.append(guess)
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "command": "wordle_guess",
                    "guess": guess,
                    "correct_word": word,
                },
                "room": room_id,
            },
        )
        if self.version == "critic":
            self.sessions[room_id].critic_provided = False
            self.set_message_privilege(room_id, self.sessions[room_id].critic,True)

        if word != guess:
            self.log_event("FALSE_GUESS", {"content": guess}, room_id)

        elif (word == guess) or (remaining_guesses == 1):
            sleep(2)
            result, points = ("lose", 0)

            if word == guess:
                result, points = ("win", 1)
                self.log_event("CORRECT_GUESS", {"content": guess}, room_id)

            # self.timers_per_room[room_id].done_timer.cancel()

            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message=(
                            f"**You {result} this round!**"
                        ),
                    ),
                    "room": room_id,
                    "html": True,
                },
            )
            self.update_reward(room_id, points)
            self.load_next_game(room_id)

    def load_next_game(self, room_id):
        """
        Load the next word if possible
        """
        self.sessions[room_id].words.pop(0)

        if not self.sessions[room_id].words:
            self.terminate_experiment(room_id)
            return

        # load the next word
        # not necessary to reset timer but like in coco?
        self.sessions[room_id].timer.reset()
        self.start_round(room_id)

    def terminate_experiment(self, room_id):
        self.send_message_to_user(STANDARD_COLOR, "The game is over 🎉 🎉, thank you for participating!",
                                  room_id)
        for player in self.sessions[room_id].players:
            self.confirmation_code(room_id, "success", player["id"])
        self.close_game(room_id)

    def reload_state(self, room_id, user_id, only_instr = False):
        if not self.sessions[room_id].words:
            self.terminate_experiment(room_id)
            return

        self.send_instr(room_id)
        if not only_instr:
            LOG.debug(f'Reload state for {user_id}')
            init_command = "wordle_init"
            if user_id == self.sessions[room_id].critic:
                if self.sessions[room_id].turn == self.sessions[room_id].critic:
                    self.set_message_privilege(room_id, self.sessions[room_id].critic, True)
                    self.give_writing_rights(room_id, self.sessions[room_id].critic)
                # else:
                #     self.set_message_privilege(room_id, self.sessions[room_id].critic, False)
                #     self.make_input_field_unresponsive(room_id, self.sessions[room_id].critic)


                init_command = "wordle_init_critic"

            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "command": f"{init_command}",
                    },
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )
            LOG.debug(f'Init {init_command }')
            # enter all the guesses that this user sent to the bot
            # to catch up with the other user
            word = self.sessions[room_id].words[0]["target_word"].lower()
            for guess in self.sessions[room_id].round_guesses_history:
                self.sio.emit(
                    "message_command",
                    {
                        "command": {
                            "command": "wordle_guess",
                            "guess": guess,
                            "correct_word": word,
                        },
                        "room": room_id,
                        "receiver_id":  user_id,
                    },
                )

    def start_round(self, room_id):
        if not self.sessions[room_id].words:
            self.terminate_experiment(room_id)
            return

        else:
            round_n = (WORDS_PER_ROOM - len(self.sessions[room_id].words)) + 1
            self.log_event("round", {"number": round_n}, room_id)

            self.sessions[room_id].round_guesses_history = []
            if self.version == "critic":
                self.set_message_privilege(room_id, self.sessions[room_id].critic, False)
                self.make_input_field_unresponsive(room_id, self.sessions[room_id].critic)

            self.sessions[room_id].word_to_guess = self.sessions[room_id].words[0][
                "target_word"].lower()

            self.log_event("TARGET_WORD", {"content": self.sessions[room_id].word_to_guess,
                                           "word_level" : self.sessions[room_id].words[0]["level"]},
                                            room_id)
            # log clue here as well?


            self.send_message_to_user(STANDARD_COLOR,
                                      f"Let's start round {round_n}",
                                      room_id)

            self.send_message_to_user(STANDARD_COLOR, f"{self.sessions[room_id].word_to_guess}", room_id, self.sessions[room_id].guesser)
            if self.version == "clue" or self.version == "critic":
                self.send_message_to_user(STANDARD_COLOR, f"CLUE: <b> {self.sessions[room_id].words[0]['target_word_clue'].lower()} </b>",
                                          room_id)
                self.log_event("CLUE", {"content": self.sessions[room_id].words[0]['target_word_clue'].lower()}, room_id)

            sleep(2)

            if self.version == "critic":
                self.sio.emit(
                "message_command",
                {"command": {"command": "wordle_init_critic"}, "room": room_id,  "receiver_id": self.sessions[room_id].critic},
                )

            self.sio.emit(
                "message_command",
                {"command": {"command": "wordle_init"}, "room": room_id, "receiver_id": self.sessions[room_id].guesser},
            )
            # reset attributes for the new round
            for usr in self.sessions[room_id].players:
                usr["status"] = "ready"
                usr["msg_n"] = 0


            # restart next_round_timer
            # self.sessions[room_id].timer.start_round_timer(self.time_out_round, room_id)
            self.sessions[room_id].timer.reset()

    def send_instr(self, room_id):
        mode_message = ""
        if self.version == "clue":
            mode_message += CLUE_MODE
        elif self.version == "critic":
            mode_message += CRITIC_MODE

        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "send_instr",
                    "message": f"{GUESSER_HTML}"
                },
                "room": room_id,
                "receiver_id": self.sessions[room_id].guesser,
            }
        )
        # mode for the guesser (if version == clue, or critic)
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/mode",
            json={"text": mode_message, "receiver_id": self.sessions[room_id].guesser},
            headers={"Authorization": f"Bearer {self.token}"}
        )

        if self.version == "critic":
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "send_instr",
                        "message": f"{CRITIC_HTML}"
                    },
                    "room": room_id,
                    "receiver_id": self.sessions[room_id].critic,
                }
            )
    def _command_ready(self, room_id, user):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        if self.version == "critic":
            curr_usr, other_usr = self.sessions[room_id].players
            if curr_usr["id"] != user:
                curr_usr, other_usr = other_usr, curr_usr

            # only one user has sent /ready repetitively
            if check_ready(curr_usr):
                sleep(0.5)
                self.send_message_to_user(STANDARD_COLOR,
                    "You have already  clicked 'ready'.", room_id, curr_usr["id"]
                )
                return
            curr_usr["status"] = "ready"

            if check_ready(other_usr):
                # both ready
                self.send_message_to_user(STANDARD_COLOR, "Woo-Hoo! The game will begin now.", room_id)
                self.start_round(room_id)
            else:
                # one player ready
                self.send_message_to_user(STANDARD_COLOR,
                    "Now, waiting for your partner to click 'ready'.",
                    room_id,
                    curr_usr["id"],
                )

        else:
            # Standard/Clue version (1 player)

            # the user has sent /ready repetitively
            if check_ready(self.sessions[room_id].players[0]):
                self.send_message_to_user(STANDARD_COLOR,
                    "You have already typed 'ready'.", room_id, user
                )
                return
            self.sessions[room_id].players[0]["status"] = "ready"
            self.send_message_to_user(STANDARD_COLOR, "Woo-Hoo! The game will begin now.", room_id)
            self.start_round(room_id)

    def update_reward(self, room_id, reward):
        score = self.sessions[room_id].points["score"]
        score += reward
        score = round(score, 2)
        self.sessions[room_id].points["score"] = max(0, score)
        self.update_title_points(room_id, reward)

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
            json={
                "text": f"Score: {score} 🏆 | Correct: {correct} ✅ | Wrong: {wrong} ❌"
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.sessions[room_id].points["history"][0]["correct"] = correct
        self.sessions[room_id].points["history"][0]["wrong"] = wrong

        self.request_feedback(response, "setting point stand in title")

    def give_writing_rights(self, room_id, user_id):
        response = requests.delete(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "readonly",
                "value": "placeholder",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "placeholder",
                "value": "Enter your message here!",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def set_message_privilege(self, room_id, user_id, value):
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
        # if value:
        #     self.sessions[room_id].turn = user_id
        self.request_feedback(response, "changing user's message permission")

    def make_input_field_unresponsive(self, room_id, user_id):
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "readonly",
                "value": "true",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        message = INPUT_FIELD_UNRESP_GUESSER
        if user_id == self.sessions[room_id].critic:
            message = INPUT_FIELD_UNRESP_CRITIC

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "placeholder",
                "value": f"{message}",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def timeout_close_game(self, room_id, status):
        # added on febr 6 from coco (see note, room id is not found after 2 users disconnected)
        if room_id in self.sessions:

            self.send_message_to_user(STANDARD_COLOR, "The room is closing because of inactivity",
                                      room_id)
            for player in self.sessions[room_id].players:
                self.confirmation_code(room_id, status, player["id"])
            self.close_game(room_id)

    def timeout_waiting_room(self, user):
        # get layout_id
        response = requests.get(
            # f"{self.uri}/rooms/{self.waiting_room}",
            f"{self.uri}/tasks/{self.task_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        layout_id = response.json()["layout_id"]

        # create a new task room for this user
        room = requests.post(
            f"{self.uri}/rooms",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"layout_id": layout_id},
        )
        room = room.json()

        # remove user from waiting_room
        self.remove_user_from_room(user["id"], self.waiting_room)

        # move user to new task room
        response = requests.post(
            f"{self.uri}/users/{user['id']}/rooms/{room['id']}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not let user join room: {response.status_code}")
            exit(4)

        sleep(2)

        # requests.patch(
        #     f"{self.uri}/rooms/{room['id']}/attribute/id/current-image",
        #     json={
        #         "attribute": "src",
        #         "value": "https://expdata.ling.uni-potsdam.de/cocobot/sad_robot.jpg",
        #     },
        #     headers={"Authorization": f"Bearer {self.token}"},
        # )


        self.send_message_to_user(STANDARD_COLOR, "Unfortunately we were not able to find a partner for you, "
                                                  "you will now get a token.", room["id"], user["id"])

        self.confirmation_code(room["id"], "timeout_waiting_room", user["id"])
        self.remove_user_from_room(user["id"], room["id"])


    def send_message_to_user(self, color, message, room, receiver=None):
        if receiver:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                    message = (message), color = color,
                    ),
                    "room": room,
                    "receiver_id":receiver,
                    "html": True,
                },
            )
        else:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                    message = (message), color = color,
                    ),
                    "room": room,
                    "html": True,
                },
            )

    def confirmation_code(self, room_id, status, user_id):
        """Generate AMT token that will be sent to each player."""
        amt_token = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if room_id in self.sessions:
            points = self.sessions[room_id].points
        else:
            points = 0
        self.log_event(
            "confirmation_log",
            {"status_txt": status, "amt_token": amt_token, "receiver": user_id,
             "points": points},
            room_id,
        )

        self.send_message_to_user(STANDARD_COLOR, "Please remember to "
                        "save your token before you close this browser window. "
                        f"Your token: {amt_token}", room_id, user_id)

    def close_game(self, room_id):
        self.send_message_to_user(STANDARD_COLOR, "The room is closing, see you next time 👋",
                                  room_id)

        self.sessions[room_id].game_over = True

        self.room_to_read_only(room_id)

        # remove any task room specific objects
        self.sessions.clear_session(room_id)

    def remove_user_from_room(self, user_id, room_id):
        response = requests.get(
            f"{self.uri}/users/{user_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not get user: {response.status_code}")
            response.raise_for_status()
        etag = response.headers["ETag"]

        try:
            response = requests.delete(
                f"{self.uri}/users/{user_id}/rooms/{room_id}",
                headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
            )
            if not response.ok:
                logging.error(
                    f"Could not remove user from task room: {response.status_code}"
                )
                response.raise_for_status()
            logging.debug("Removing user from task room was successful.")
        except:
            logging.debug(f"User {user_id} not in room {room_id}")

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set room to read_only")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set room to read_only")

        # remove user from room
        if room_id in self.sessions:
            for usr in self.sessions[room_id].players:
                response = requests.get(
                    f"{self.uri}/users/{usr['id']}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "get user")
                etag = response.headers["ETag"]

                response = requests.delete(
                    f"{self.uri}/users/{usr['id']}/rooms/{room_id}",
                    headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "remove user from task room")

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


def check_ready(player):
    return player["status"] == "ready"