from collections import defaultdict
import logging
from threading import Timer

import requests
from time import sleep
import random
import os

import nltk
from nltk import SnowballStemmer
from nltk.corpus import stopwords
import string

nltk.download("stopwords", quiet=True)
EN_STOPWORDS = stopwords.words("english")
# nltk.download("wordnet")
nltk.download("stopwords", quiet=True)
EN_LEMMATIZER = nltk.stem.WordNetLemmatizer()
EN_STEMMER = SnowballStemmer("english")

from taboo.dataloader import Dataloader
from taboo.config import EXPLAINER_PROMPT, GUESSER_PROMPT, LEVEL_WORDS, WORDS_PER_ROOM, COLOR_MESSAGE, STANDARD_COLOR, \
    STARTING_POINTS, TIMEOUT_TIMER, LEAVE_TIMER, WAITING_PARTNER_TIMER
from templates import TaskBot

LOG = logging.getLogger(__name__)


class Session:
    # what happens between 2 players
    def __init__(self):
        self.players = list()
        self.words = Dataloader(LEVEL_WORDS, WORDS_PER_ROOM)
        LOG.debug(f"The words are {self.words}")
        self.word_to_guess = None
        self.guesses = 0
        self.explainer = None
        self.guesser = None
        self.points = {
            "score": STARTING_POINTS,
            "history": [
                {"correct": 0, "wrong": 0, "warnings": 0}
            ]
        }
        self.timer = None
        self.left_room_timer = dict()
        self._game_over = False

    @property
    def game_over(self):
        return self._game_over

    def set_game_over(self, new_value: bool):
        self._game_over = new_value

    def close(self):
        pass

    def pick_explainer(self):
        # assuming there are only 2 players
        self.explainer = random.choice(self.players)["id"]
        for player in self.players:
            if player["id"] != self.explainer:
                self.guesser = player["id"]


class SessionManager(defaultdict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].timer.cancel()
            for timer in self[room_id].left_room_timer.values():
                timer.cancel()
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
        # the next session then starts automatically?
        # self.sessions = SessionManager(Session)
        self.sessions = SessionManager()

    def post_init(self, waiting_room):
        """
        save extra variables after the __init__() method has been called
        and create the init_base_dict: a dictionary containing
        needed arguments for the init event to send to the JS frontend
        """
        self.waiting_room = waiting_room
        self.waiting_timer = None

    def on_task_room_creation(self, data):
        """This function is executed as soon as 2 users are paired and a new
        task took is created
        """
        nltk.download("wordnet")
        room_id = data["room"]

        task_id = data["task"]
        logging.debug(f"A new room was created with id: {data['room']}")
        logging.debug(f"A new task room was created with task id: {data['task']}")
        logging.debug(f"This bot is looking for task id: {self.task_id}")
        if task_id is not None and task_id == self.task_id:
            # modify layout
            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])
            logging.debug("Create data for the new task room...")
            # create a new session for these users
            # this_session = self.sessions[room_id]
            self.sessions.create_session(room_id)
            LOG.debug("Create timeout timer for this session")
            self.start_timeout_timer(room_id)

            # Cancel waiting timer if there is one
            if self.waiting_timer:
                LOG.debug('Cancel waiting timer')
                self.waiting_timer.cancel()

            for usr in data["users"]:
                self.sessions[room_id].players.append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )

            # join the newly created room
            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )

            # 2) Choose an explainer
            self.sessions[room_id].pick_explainer()
            for user in data["users"]:
                if user["id"] == self.sessions[room_id].explainer:
                    explainer_name = user["name"]
                    LOG.debug(f'{explainer_name} is the explainer.')
                else:
                    guesser_name = user["name"]
                    LOG.debug(f'{guesser_name} is the guesser.')
            self.log_event('players', {
                "GM": "TabooBot",
                "Explainer": f"user_id {self.sessions[room_id].explainer}, name {explainer_name}",
                "Guesser": f"user_id {self.sessions[room_id].guesser}, name {guesser_name}"},
                           room_id)
            self.send_individualised_instructions(room_id)
            # use sleep so that people first read the instructions!
            # sleep(2)
        self.sio.emit(
            "text",
            {
                "message": (
                    "Are you ready? <br>"
                    "<button class='message_button' onclick=\"confirm_ready('yes')\">YES</button> "
                    "<button class='message_button' onclick=\"confirm_ready('no')\">NO</button>"
                ),
                "room": room_id,
                # "receiver_id": player["id"],
                "html": True,
            },
        )

    @staticmethod
    def message_callback(success, error_msg="Unknown Error"):
        if not success:
            LOG.error(f"Could not send message: {error_msg}")
            exit(1)
        LOG.debug("Sent message successfully.")

    def register_callbacks(self):
        @self.sio.event
        def user_message(data):
            LOG.debug("Received a user_message.")
            LOG.debug(data)

            user = data["user"]
            message = data["message"]
            room_id = data["room"]
            # it sends to itself, user id = null, receiver if = null
            self.sio.emit("text", {"message": message, "room": room_id})

        @self.sio.event
        def status(data):
            """Triggered when a user enters or leaves a room."""
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

                if event == "join":
                    # inform everyone about the join event
                    self.send_message_to_user(
                        f"{user['name']} has joined the game.", room_id
                    )
                    sleep(0.5)
                    # cancel leave timers if any
                    LOG.debug("Cancel timer: user joined")
                    self.user_joined(room_id, curr_usr["id"])

                elif event == "leave":
                    if room_id in self.sessions:
                        if not self.sessions[room_id].game_over:
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
                            if self.sessions[room_id].timer:
                                self.sessions[room_id].timer.cancel()
                            LOG.debug("Start timer: user left")
                            self.sessions[room_id].left_room_timer[curr_usr["id"]] = Timer(
                                LEAVE_TIMER * 60, self.user_did_not_rejoin,
                                args=[room_id],
                            )
                            self.sessions[room_id].left_room_timer[curr_usr["id"]].start()

                    # # remove this user from current session
                    # this_session.players = list(
                    #     filter(
                    #         lambda player: player["id"] != user["id"], this_session.players
                    #     )
                    # )
                    #

        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )
            user_id = data["user"]['id']
            command = data["command"]
            room_id = data["room"]
            this_session = self.sessions[room_id]

            if user_id == self.user:
                return

            if this_session.game_over:
                LOG.debug("Game is over, do not reset timeout timer after sending command")
            else:
                # Reset timer
                LOG.debug("Reset timeout timer after sending command")
                if this_session.timer:
                    this_session.timer.cancel()
                self.start_timeout_timer(room_id)

            if isinstance(data["command"], dict):
                # commands from interface
                event = data["command"]["event"]
                LOG.debug(f"The event is {event}")
                LOG.debug(f"The command is is {data['command']}")
                if event == "confirm_ready":
                    answer = data["command"]["answer"]
                    LOG.debug(f"{answer}")
                    if data["command"]["answer"] == "yes":
                        self._command_ready(data["room"], data["user"]["id"])
                    elif data["command"]["answer"] == "no":
                        self.send_message_to_user(
                            "OK, read the instructions carefully and click on <yes> once you are ready.",
                            data["room"],
                            data["user"]["id"],
                        )
                return

            if data["command"].startswith("ready"):
                self._command_ready(room_id, user_id)
                return

            if this_session.explainer == user_id:
                # EXPLAINER sent a message

                # means that new turn began
                self.log_event("turn", dict(), room_id)
                # log event
                # self.log_event("clue", {"content": data['command']}, room_id)
                for user in this_session.players:
                    if user["id"] == user_id:
                        explainer_name = user['name']  # Since explainer and guesser ar user_ids, get name for logging
                self.log_event("clue", {"content": data['command'],
                                        "from": f"GM impersonated as {explainer_name}, the explainer",
                                        "to": this_session.guesser}, room_id)

                for user in this_session.players:
                    if user["id"] != user_id:
                        self.sio.emit(
                            "text",
                            {
                                "room": room_id,
                                "receiver_id": this_session.guesser,
                                "message": f"{command}",
                                "impersonate": user_id,
                            },
                            callback=self.message_callback,
                        )

                self.set_message_privilege(self.sessions[room_id].explainer, False)
                self.make_input_field_unresponsive(
                    room_id, self.sessions[room_id].explainer
                )

                # check whether the explainer used a forbidden word
                explanation_errors = check_clue(
                    data["command"].lower(),
                    this_session.word_to_guess,
                    this_session.words[0]["related_word"],
                )
                # log that send message

                if explanation_errors:
                    message = explanation_errors[0]["message"]
                    self.log_event("invalid clue", {"content": message}, room_id)
                    # for player in this_session.players:
                    self.send_message_to_user(
                        f"{message}",
                        room_id,
                    )
                    sleep(0.5)
                    self.update_reward(room_id, 0)
                    self.load_next_game(room_id)
                else:
                    self.set_message_privilege(self.sessions[room_id].guesser, True)
                    # assign writing rights to other user
                    self.give_writing_rights(room_id, self.sessions[room_id].guesser)

            else:
                # GUESSER sent the command
                for user in this_session.players:
                    if user["id"] == user_id:
                        guesser_name = user['name']  # Since explainer and guesser ar user_ids, get name for logging
                self.log_event("guess", {"content": data['command'],
                                         "from": f"GM impersonated as {guesser_name}, the guesser",
                                         "to": this_session.guesser}, room_id)

                for user in this_session.players:
                    if user["id"] != user_id:
                        self.sio.emit(
                            "text",
                            {
                                "room": room_id,
                                "receiver_id": this_session.explainer,
                                "message": f"{command}",
                                "impersonate": user_id,
                            },
                            callback=self.message_callback,
                        )

                self.set_message_privilege(self.sessions[room_id].explainer, True)
                # assign writing rights to other user
                self.give_writing_rights(room_id, self.sessions[room_id].explainer)

                self.set_message_privilege(self.sessions[room_id].guesser, False)
                self.make_input_field_unresponsive(
                    room_id, self.sessions[room_id].guesser
                )
                valid_guess = check_guess(data["command"].lower())

                if not valid_guess:
                    # self.update_interactions(room_id, "invalid format", "abort game")
                    self.log_event("invalid format", {"content": data['command']}, room_id)

                    # for player in this_session.players:
                    self.send_message_to_user(
                        f"INVALID GUESS: '{data['command'].lower()}' contains more than one word."
                        f"You both lose this round.",
                        room_id,
                        # player["id"],
                    )
                    sleep(0.5)
                    self.load_next_game(room_id)
                    return

                guess_is_correct = correct_guess(this_session.word_to_guess, data["command"].lower())
                #  before 2 guesses were made
                if this_session.guesses < 2:
                    this_session.guesses += 1
                    if guess_is_correct:

                        # self.update_interactions(room_id, "correct guess", data["message"].lower())
                        self.log_event("correct guess", {"content": data['command']}, room_id)

                        # for player in this_session.players:
                        self.send_message_to_user(
                            f"GUESS {this_session.guesses}: "
                            f"'{this_session.word_to_guess}' was correct! "
                            f"You both win this round.",
                            room_id,
                            # player["id"],
                        )
                        sleep(0.5)
                        self.update_reward(room_id, 1)
                        self.load_next_game(room_id)

                    else:
                        # guess is false
                        self.send_message_to_user(
                            f"GUESS {this_session.guesses} '{data['command']}' was false",
                            room_id,
                            # player["id"],
                        )

                        # if player["id"] == this_session.explainer:
                        sleep(0.5)
                        self.send_message_to_user(
                            f"Please provide a new description",
                            room_id,
                            this_session.explainer,
                        )
                        self.set_message_privilege(
                            self.sessions[room_id].explainer, True
                        )
                        # assign writing rights to other user
                        self.give_writing_rights(
                            room_id, self.sessions[room_id].explainer
                        )
                        self.set_message_privilege(
                            self.sessions[room_id].guesser, False
                        )
                        self.make_input_field_unresponsive(
                            room_id, self.sessions[room_id].guesser
                        )
                else:
                    # last guess (guess number 3)
                    this_session.guesses += 1
                    if guess_is_correct:
                        # self.update_interactions(room_id, "correct guess", data["message"].lower())
                        self.log_event("correct guess", {"content": data['command']}, room_id)
                        self.send_message_to_user(
                            f"GUESS {this_session.guesses}: {this_session.word_to_guess} was correct! "
                            f"You both win this round.",
                            room_id,
                        )
                        sleep(0.5)
                        self.update_reward(room_id, 1)

                    else:
                        # guess is false
                        # self.update_interactions(room_id, "max turns reached", str(3))
                        self.log_event("max turns reached", {"content": str(3)}, room_id)
                        self.send_message_to_user(
                            f"3 guesses have been already used. You lost this round.",
                            room_id,
                        )
                        sleep(0.5)
                        self.update_reward(room_id, 0)
                    # start new round (because 3 guesses were used)
                    self.load_next_game(room_id)

                # in any case update rights
                self.set_message_privilege(self.sessions[room_id].explainer, True)

                # assign writing rights to other user
                self.give_writing_rights(room_id, self.sessions[room_id].explainer)
                self.set_message_privilege(self.sessions[room_id].guesser, False)

                # make input field unresponsive
                self.make_input_field_unresponsive(
                    room_id, self.sessions[room_id].guesser
                )

        @self.sio.event
        def text_message(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a message from {data['user']['name']}: {data['message']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]

            if user_id == self.user:
                return

            self.sio.emit(
                "text", {"message": data['message'], "room": room_id, }
            )

            this_session = self.sessions[room_id]

            if this_session.game_over:
                LOG.debug("Game is over, do not reset timeout timer after sending command")
            else:
                # Reset timer
                LOG.debug("Reset timeout timer after sending message")
                if this_session.timer:
                    this_session.timer.cancel()
                self.start_timeout_timer(room_id)

    def _command_ready(self, room_id, user_id):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            sleep(0.5)
            self.send_message_to_user(
                "You have already typed 'ready'.", room_id, curr_usr["id"]
            )
            return
        curr_usr["status"] = "ready"

        # both
        if other_usr["status"] == "ready":
            self.send_message_to_user("Woo-Hoo! The game will begin now.", room_id)
            sleep(1)
            self.start_round(room_id)
        else:
            self.send_message_to_user(
                "Now, waiting for your partner to type 'ready'.",
                room_id,
                curr_usr["id"],
            )

    def start_round(self, room_id):
        if not self.sessions[room_id].words:
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
            self.confirmation_code(room_id, 'success')
            self.close_game(room_id)
        # send the instructions for the round
        round_n = (WORDS_PER_ROOM - len(self.sessions[room_id].words)) + 1

        # try to log the round number
        self.log_event("round", {"number": round_n}, room_id)

        self.send_message_to_user(f"Let's start round {round_n} of 6", room_id)
        sleep(1)
        self.send_message_to_user(
            "Wait a bit for the first hint about the word you need to guess",
            room_id,
            self.sessions[room_id].guesser,
        )

        self.sessions[room_id].word_to_guess = self.sessions[room_id].words[0][
            "target_word"
        ]
        self.log_event('target word', {'content': self.sessions[room_id].word_to_guess}, room_id)
        self.log_event('difficulty level', {'content': self.sessions[room_id].words[0][
            "level"]}, room_id)
        LOG.debug(
            f"The target word is {self.sessions[room_id].word_to_guess} with level {self.sessions[room_id].words[0]['level']}")
        taboo_words = ", ".join(self.sessions[room_id].words[0]["related_word"])
        self.sessions[room_id].guesses = 0

        self.send_message_to_user(
            f"Your task is to explain the word '{self.sessions[room_id].word_to_guess}'."
            f" You cannot use the following words: {taboo_words}",
            room_id,
            self.sessions[room_id].explainer,
        )

        # update writing_rights
        self.set_message_privilege(self.sessions[room_id].explainer, True)
        # assign writing rights to other user
        self.give_writing_rights(room_id, self.sessions[room_id].explainer)
        self.set_message_privilege(self.sessions[room_id].guesser, False)
        self.make_input_field_unresponsive(room_id, self.sessions[room_id].guesser)

    def load_next_game(self, room_id):
        LOG.debug(f"Triggered load_next_game for room {room_id}")
        # word list gets smaller, next round starts
        self.sessions[room_id].words.pop(0)
        if not self.sessions[room_id].words:
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
            self.confirmation_code(room_id, 'success')
            self.close_game(room_id)
            return
        self.start_round(room_id)

    def confirmation_code(self, room_id, status, user_id=None):
        """Generate token that will be sent to each player."""
        LOG.debug("Triggered confirmation_code")
        if room_id in self.sessions:
            points = self.sessions[room_id].points
        else:
            points = 0
        if user_id is not None:
            confirmation_token = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            LOG.debug(f'confirmation token is {confirmation_token, room_id, status, user_id}')

            # Or check in wordle how the user is given the link to prolific
            self.sio.emit(
                "text",
                {
                    "message": f"This is your token:  **{confirmation_token}** <br>"
                               "Please remember to save it "
                               "before you close this browser window. "
                    ,
                    "receiver_id": user_id,
                    "room": room_id,
                    "html": True
                },
            )
            # post confirmation token to logs
            self.log_event(
                "confirmation_log",
                {"status_txt": status, "token": confirmation_token, "reward": points, "receiver_id": user_id},
                room_id,
            )
            return
        for user in self.sessions[room_id].players:
            completion_token = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message=(
                            "Please remember to "
                            "save your token before you close this browser window. "
                            f"Your token: **{completion_token}**"
                        ),
                    ),
                    "receiver_id": user["id"],
                    "room": room_id,
                    "html": True,
                },
            )

            self.log_event(
                "confirmation_log",
                {
                    "status_txt": status,
                    "token": completion_token,
                    "reward": self.sessions[room_id].points,
                    "receiver_id": user["id"],
                },
                room_id,
            )

    def start_timeout_timer(self, room_id):
        timer = Timer(
            TIMEOUT_TIMER * 60, self.timeout_close_game, args=[room_id]
        )
        timer.start()
        self.sessions[room_id].timer = timer

    def timeout_close_game(self, room_id):
        LOG.debug('Triggered timeout_close_game')
        # self.sessions[room_id].set_game_over(True)
        self.sio.emit(
            "text",
            {"message": "Closing session because of inactivity", "room": room_id},
        )
        self.confirmation_code(room_id, status='timeout')
        self.close_game(room_id)

    def user_joined(self, room_id, user):
        timer = self.sessions[room_id].left_room_timer.get(user)
        if timer is not None:
            self.sessions[room_id].left_room_timer[user].cancel()
        else:
            pass

    def user_did_not_rejoin(self, room_id):
        LOG.debug('Triggered user_did_not_rejoin')
        # self.sessions[room_id].set_game_over(True)
        self.sio.emit(
            "text",
            {"message": "Your partner didn't rejoin, you will receive a token so you can get paid for your time",
             "room": room_id},
        )
        self.confirmation_code(room_id, status='user_left')
        self.close_game(room_id)

    def _no_partner(self, room_id, user_id):
        """Handle the situation that a participant waits in vain."""
        LOG.debug('Triggered _no_partner')

        # get layout_id
        response = requests.get(
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
        self.remove_user_from_room(user_id, self.waiting_room)

        # move user to new task room
        response = requests.post(
            f"{self.uri}/users/{user_id}/rooms/{room['id']}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not let user join room: {response.status_code}")
            exit(4)

        sleep(1)

        completion_token = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=6)
        )

        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR,
                    message=(
                        "Unfortunately we could not find a partner for you!<br>"
                        "Please remember to "
                        "save your token before you close this browser window. "
                        f"Your token: **{completion_token}**<br>The room is closing, see you next time 👋"
                    ),
                ),
                "receiver_id": user_id,
                "room": room["id"],
                "html": True,
            },
        )

        self.log_event(
            "confirmation_log",
            {
                "status_txt": "no_partner",
                "token": completion_token,
                "reward": 0,
                "user_id": user_id,
            },
            room["id"],
        )
        LOG.debug(f'Confirmation token is {completion_token}')

        # remove user from new task_room
        self.remove_user_from_room(user_id, room["id"])
        # self.sessions[room_id].set_game_over(True)
        self.close_game(room_id)

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
                LOG.error(
                    f"Could not remove user from task room: {response.status_code}"
                )
                response.raise_for_status()
            LOG.debug("Removing user from task room was successful.")
        except:
            LOG.debug(f"User {user_id} not in room {room_id}")

    def close_game(self, room_id):
        LOG.debug(f"Triggered close game for room {room_id}")

        if room_id in self.sessions:
            self.sio.emit(
                "text",
                {
                    "message": "The room is closing, see you next time 👋",
                    "room": room_id
                }
            )
            self.sessions[room_id].set_game_over(True)
        self.room_to_read_only(room_id)
        # remove any task room specific objects
        self.sessions.clear_session(room_id)

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

    def close_room(self, room_id):
        self.room_to_read_only(room_id)

        # remove any task room specific objects
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

    def send_message_to_user(self, message, room, receiver=None):
        if receiver:
            self.sio.emit(
                "text",
                {"message": f"{message}", "room": room, "receiver_id": receiver},
            )
        else:
            self.sio.emit(
                "text",
                {"message": f"{message}", "room": room},
            )
        # sleep(1)

    def send_individualised_instructions(self, room_id):
        this_session = self.sessions[room_id]

        # Send explainer_ instructions to explainer
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr_title",
            json={
                "text": "Explain the taboo word",
                "receiver_id": this_session.explainer,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction title: {response.status_code}")
            response.raise_for_status()

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr",
            json={"text": f"{EXPLAINER_PROMPT}", "receiver_id": this_session.explainer},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction: {response.status_code}")
            response.raise_for_status()

        # Send guesser_instructions to guesser
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr_title",
            json={"text": "Guess the taboo word", "receiver_id": this_session.guesser},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction title: {response.status_code}")
            response.raise_for_status()

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/instr",
            json={"text": f"{GUESSER_PROMPT}", "receiver_id": this_session.guesser},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not set task instruction: {response.status_code}")
            response.raise_for_status()

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
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "placeholder",
                "value": "Wait for a message from your partner",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )

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


def check_guess(user_guess):
    return len(user_guess.split()) == 1


def correct_guess(correct_answer, user_guess):
    user_guess = user_guess.strip()
    user_guess = user_guess.lower()
    user_guess = remove_punctuation(user_guess)
    return correct_answer == user_guess


def remove_punctuation(text: str) -> str:
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text


def check_clue(clue: str, target_word: str, related_words):
    stemmer = EN_STEMMER
    clue = clue.replace("CLUE:", "")
    clue = clue.lower()
    clue = remove_punctuation(clue)
    clue = clue.split(" ")
    clue_words = [clue_word for clue_word in clue if clue_word not in EN_STOPWORDS]
    clue_word_stems = [stemmer.stem(clue_word) for clue_word in clue_words]
    errors = []
    target_word_stem = stemmer.stem(target_word)
    related_word_stems = [stemmer.stem(related_word) for related_word in related_words]

    for clue_word, clue_word_stem in zip(clue_words, clue_word_stems):
        if target_word_stem == clue_word_stem:
            errors.append({
                "message": f"The target word '{target_word}' (stem={target_word_stem})"
                           f" is similar to the word '{clue_word}' (stem={clue_word_stem})"
                           " and it was used in the clue. You both lose :(",
                "type": 0
            })
        for related_word, related_word_stem in zip(related_words, related_word_stems):
            if related_word_stem == clue_word_stem:
                errors.append({
                    "message": f"The related word '{related_word}' (stem={related_word_stem})  "
                               f"is similar to the word '{clue_word}' (stem={clue_word_stem})"
                               " and it was used in the clue. You both lose :(",
                    "type": 1
                })
    return errors


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
        "--waiting_room",
        type=int,
        help="room where users await their partner",
        **waiting_room,
    )

    parser.add_argument(
        "--taboo_data",
        help="json file containing words",
        default=os.environ.get("TABOO_DATA"),
        # default="data/taboo_words.json",
    )
    args = parser.parse_args()

    # create bot instance
    taboo_bot = TabooBot(args.token, args.user, args.task, args.host, args.port)

    taboo_bot.post_init(args.waiting_room)

    # taboo_bot.taboo_data = args.taboo_data
    # connect to chat server
    taboo_bot.run()
