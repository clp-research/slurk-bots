from collections import defaultdict
import logging
from threading import Timer

import requests
from time import sleep
import random
import os

import nltk
from nltk.corpus import stopwords
import string

nltk.download("stopwords", quiet=True)
EN_STOPWORDS = stopwords.words("english")
nltk.download("wordnet")
nltk.download("stopwords", quiet=True)
EN_LEMMATIZER = nltk.stem.WordNetLemmatizer()


from taboo.dataloader import Dataloader
from taboo.config import EXPLAINER_PROMPT, GUESSER_PROMPT, LEVEL_WORDS, WORDS_PER_ROOM, COLOR_MESSAGE, STANDARD_COLOR, \
    STARTING_POINTS, TIMEOUT_TIMER, LEAVE_TIMER
from templates import TaskBot


LOG = logging.getLogger(__name__)


class Session:
    # what happens between 2 players
    def __init__(self):
        self.players = list()
        self.words = Dataloader(LEVEL_WORDS, WORDS_PER_ROOM)
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

    # log next turn?
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


#     game over


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

    def on_task_room_creation(self, data):
        """This function is executed as soon as 2 users are paired and a new
        task took is created
        """
        room_id = data["room"]

        task_id = data["task"]
        logging.debug(f"A new task room was created with id: {data['room']}")
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
                    LOG.debug(f'{user["name"]} is the explainer.')
                else:
                    LOG.debug(f'{user["name"]} is the guesser.')

            response_e = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr",
                json={
                    "text": EXPLAINER_PROMPT,
                    "receiver_id": self.sessions[room_id].explainer,
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response_e.ok:
                LOG.error(f"Could not set task instruction: {response.status_code}")
                response_e.raise_for_status()

            response_g = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr",
                json={
                    "text": GUESSER_PROMPT,
                    "receiver_id": self.sessions[room_id].guesser,
                },
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not response_g.ok:
                LOG.error(f"Could not set task instruction: {response.status_code}")
                response_g.raise_for_status()

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
            room_id = data["room"]
            event = data["type"]
            user = data["user"]

            # don't do this for the bot itself
            if user["id"] == self.user:
                return

            if room_id == self.waiting_room:
                pass

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

            if data["command"].startswith("ready"):
                self._command_ready(room_id, user_id)
                return
            # elif isinstance(data["command"], dict):
            #     if command["event"] == "confirm_ready":
            #         if command["answer"] == "yes":
            #             self.sio.emit(
            #                 "text",
            #                 {
            #                     "message": "You typed 'YES",
            #                     "room": room_id,
            #                     "receiver_id": user_id,
            #                 },
            #             )
            #             # self._command_ready(room_id, user_id)
            #         elif data["command"]["answer"] == "no":
            #             self.sio.emit(
            #                 "text",
            #                 {
            #                     "message": "You typed 'NO'",
            #                     "room": room_id,
            #                     "receiver_id": user_id,
            #                 },
            #             )
            #             # self.send_message_to_user(STANDARD_COLOR,
            #             #                           "OK, read the instructions carefully and click on <yes> once you are ready.",
            #             #                           room_id,
            #             #                           user_id,
            #             #                           )
            #         return
            if this_session.explainer == user_id:

                # EXPLAINER sent a message
                # self.update_interactions(room_id, "clue", data['message'])

                # means that new turn began
                self.log_event("turn", dict(), room_id)
                # log event
                self.log_event("clue", {"content": data['command']}, room_id)

                #todo: 258-269 I added extra bc message not displayed
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
                    # self.update_interactions(room_id, "invalid clue", message)
                    self.log_event("invalid clue", {"content": message}, room_id)
                    # for player in this_session.players:
                    self.send_message_to_user(
                            f"{message}",
                            room_id,
                        )

                    self.load_next_game(room_id)
                else:
                    self.set_message_privilege(self.sessions[room_id].guesser, True)
                    # assign writing rights to other user
                    self.give_writing_rights(room_id, self.sessions[room_id].guesser)

            else:
                # GUESSER sent the command
                # self.update_interactions(room_id, "guess", data['message'])
                self.log_event("guess", {"content": data['command']}, room_id)

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
                        self.load_next_game(room_id)

                    else:
                        # guess is false
                        self.send_message_to_user(
                                f"GUESS {this_session.guesses} '{data['command']}' was false",
                                room_id,
                                # player["id"],
                            )

                            # if player["id"] == this_session.explainer:
                        self.send_message_to_user(
                                    f"Please provide a new description",
                                    room_id,
                                    this_session.explainer,
                                )
                        self.set_message_privilege(
                            self.sessions[room_id].explainer, True
                        )
                        # assign writing rights to other user
                        self.give_writing_rights(room_id, self.sessions[room_id].explainer )
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
                    else:
                        # guess is false
                        # self.update_interactions(room_id, "max turns reached", str(3))
                        self.log_event("max turns reached", {"content": str(3)}, room_id)
                        self.send_message_to_user(
                                f"3 guesses have been already used. You lost this round.",
                                room_id,
                            )
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

        self.send_message_to_user(f"Let's start round {round_n}", room_id)
        self.send_message_to_user(
            "Wait a bit for the first hint about the word you need to guess",
            room_id,
            self.sessions[room_id].guesser,
        )

        self.sessions[room_id].word_to_guess = self.sessions[room_id].words[0][
            "target_word"
        ]
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
        points = self.sessions[room_id].points
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
        self.sessions[room_id].set_game_over(True)
        self.sio.emit(
            "text",
            {"message": "Closing session because of inactivity", "room": room_id},
        )
        self.confirmation_code(room_id, status='timeout')
        self.close_game(room_id)

    def user_did_not_rejoin(self, room_id):
        self.sessions[room_id].set_game_over(True)
        self.sio.emit(
            "text",
            {"message": "Your partner didn't rejoin, you will receive a token so you can get paid for your time",
             "room": room_id},
        )
        self.confirmation_code(room_id, status='user_left')
        self.close_game(room_id)

    def close_game(self, room_id):
        LOG.debug(f"Triggered close game for room {room_id}")

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


    # def update_interactions(self, room_id, type_, value_):
    #     turn_info = {"action": {"type": type_, "content": value_}}
    #     self.sessions[room_id].interactions["turns"][self.sessions[room_id].log_current_turn].append(turn_info)


def check_guess(user_guess):
     return len(user_guess.split()) == 1


def correct_guess(correct_answer, user_guess):
    return correct_answer in user_guess


def remove_punctuation(text: str) -> str:
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text


def check_clue(utterance: str, target_word: str, related_words):
    utterance = utterance.lower()
    utterance = remove_punctuation(utterance)
    # simply contain checks
    if target_word in utterance:
        return [
            {
                "message": f"Target word '{target_word}' was used in the clue. You both lose this round.",
                "type": 0,
            }
        ]
    for related_word in related_words:
        if related_word in utterance:
            return [
                {
                    "message": f"Related word '{related_word}' was used in the clue, You both lose this round",
                    "type": 1,
                }
            ]

    # lemma checks
    utterance = utterance.split(" ")
    filtered_clue = [word for word in utterance if word not in EN_STOPWORDS]
    target_lemma = EN_LEMMATIZER.lemmatize(target_word)
    related_lemmas = [
        EN_LEMMATIZER.lemmatize(related_word) for related_word in related_words
    ]
    errors = []
    for clue_word in filtered_clue:
        clue_lemma = EN_LEMMATIZER.lemmatize(clue_word)
        if clue_lemma == target_lemma:
            return [
                {
                    "message": f"Target word '{target_word}' is morphological similar to clue word '{clue_word}'",
                    "type": 0,
                }
            ]
        if clue_lemma in related_lemmas:
            return [
                {
                    "message": f"Related word is morphological similar to clue word '{clue_word}'",
                    "type": 1,
                }
            ]
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
