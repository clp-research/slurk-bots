from collections import defaultdict
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

TIMEOUT_TIMER = 5  # minutes of inactivity before the room is closed automatically
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

        # TODO: read the game data from file
        self.taboo_data = {
            "Applesauce": ["fruit", "tree", "glass", "preserving"],
            "Beef patty": ["pork", "ground", "steak"],
        }
        # self.json_data = self.get_taboo_data()

    def get_taboo_data(self):
        # experiments = load_json("data/instances.json", "taboo")
        # experiment_1 = experiments["experiments"][0]
        # game_1 = experiment_1["game_instances"][0]
        # return game_1
        data = json.load("/Users/sandrasanchezp/Desktop/slurk-bots/taboo/data/taboo_words.json")
        return data

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
            self.sio.emit(
                "text", {"message": message, "room": room_id, }
            )

        @self.sio.event
        def command(data):
            """Parse user commands."""
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if user_id == self.user:
                return

            self.sessions[room_id].timer.reset()
            this_session = self.sessions[room_id]
            word_to_guess = this_session.word_to_guess
            # explainer
            if this_session.explainer == user_id:
                LOG.debug(f"{data['user']['name']} is the explainer.")
                command = data['command'].lower()
                logging.debug(
                    f"Received a command from {data['user']['name']}: {data['command']}"
                )
                self.sio.emit(
                    "message_command",
                    {
                        "command": command,
                        "room": room_id,
                        "receiver_id": this_session.guesser,
                    },
                )
                for taboo_word in self.taboo_data[word_to_guess]:
                    if taboo_word.lower() in command:
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
                        this_session.played_words.append(word_to_guess)
                        this_session.rounds_left -= 1
                        self.update_reward(room_id, 0)
                        self.update_title_points(room_id, 0)
                        self.next_round(room_id)
                    else:
                        self.sio.emit(
                            "text",
                            {
                                "message": f"HINT: {command}",
                                "room": room_id,
                                "receiver_id": this_session.guesser,
                            },
                        )
            # if room_id in self.sessions:
            #     # get users
            #     curr_usr, other_usr = self.sessions[room_id].players
            #     if curr_usr["id"] != user_id:
            #         curr_usr, other_usr = other_usr, curr_usr

                # if isinstance(data["command"], dict):
                #     # commands from interface
                #     event = data["command"]["event"]
                #
                #     if event == "confirm_selection":
                #         self.sessions[room_id].selected_object = False
                #
                #         if self.version == "show_gripper":
                #             # attach wizard's controller
                #             self.sio.emit(
                #                 "message_command",
                #                 {
                #                     "command": {"event": "attach_controller"},
                #                     "room": room_id,
                #                     "receiver_id": other_usr["id"],
                #                 },
                #             )
                #
                #         if data["command"]["answer"] == "no":
                #             # remove gripper
                #             if self.version != "show_gripper":
                #                 response = requests.delete(
                #                     f"{self.golmi_server}/slurk/gripper/{room_id}/mouse"
                #                 )
                #                 self.request_feedback(response, "removing mouse gripper")
                #
                #             else:
                #                 # reset the gripper to its original position
                #                 req = requests.get(f"{self.golmi_server}/slurk/{room_id}/state")
                #                 self.request_feedback(req, "retrieving state")
                #
                #                 state = req.json()
                #                 grippers = state["grippers"]
                #                 gr_id = list(grippers.keys())[0]
                #
                #                 req = requests.patch(f"{self.golmi_server}/slurk/gripper/reset/{room_id}/{gr_id}")
                #
                #             # allow the player to send a second description
                #             self.sessions[room_id].description = False
                #             self.set_message_privilege(user_id, True)
                #
                #             # remove points
                #             self.update_reward(room_id, NEGATIVE_REWARD)
                #             self.sessions[room_id].points["history"][-1]["wrong"] += 1
                #
                #             # update points in title
                #             if self.version != "no_feedback":
                #                 self.update_title_points(room_id)
                #
                #             # inform users
                #             self.sio.emit(
                #                 "text",
                #                 {
                #                     "message": (
                #                         "Your partner thinks you selected the wrong piece, "
                #                         "wait for the new instruction and try again"),
                #                     "room": room_id,
                #                     "receiver_id": other_usr["id"],
                #                     "html": True,
                #                 },
                #             )
                #             self.sio.emit(
                #                 "text",
                #                 {
                #                     "message": "You can now send a new description to your partner",
                #                     "room": room_id,
                #                     "receiver_id": curr_usr["id"],
                #                     "html": True,
                #                 },
                #             )
                #         else:
                #             # player thinks the wizard selected the right object
                #             req = requests.get(
                #                 f"{self.golmi_server}/slurk/{room_id}/gripped"
                #             )
                #             self.request_feedback(req, "retrieving gripped piece")
                #
                #             piece = req.json()
                #             if piece:
                #                 target = self.sessions[room_id].boards[0]["state"][
                #                     "targets"
                #                 ]
                #                 result = (
                #                     "right" if piece.keys() == target.keys()
                #                     else "wrong"
                #                 )
                #                 self.load_next_state(room_id, result)
                #
                #     # wizard sends a warning
                #     if event == "warning":
                #         logging.debug("emitting WARNING")
                #
                #         if self.version == "no_feedback":
                #             # not available
                #             return
                #
                #         # TODO: add official warning log??
                #
                #         if self.sessions[room_id].description is True:
                #             self.sio.emit(
                #                 "text",
                #                 {
                #                     "message": COLOR_MESSAGE.format(
                #                         color=WARNING_COLOR,
                #                         message=("You sent a warning to your partner"),
                #                     ),
                #                     "room": room_id,
                #                     "receiver_id": curr_usr["id"],
                #                     "html": True,
                #                 },
                #             )
                #
                #             self.sio.emit(
                #                 "text",
                #                 {
                #                     "message": COLOR_MESSAGE.format(
                #                         color=WARNING_COLOR,
                #                         message=(
                #                             "WARNING: your partner thinks that you "
                #                             "are not doing the task correctly"
                #                         ),
                #                     ),
                #                     "room": room_id,
                #                     "receiver_id": other_usr["id"],
                #                     "html": True,
                #                 },
                #             )
                #
                #             # give user possibility to send another message
                #             self.sessions[room_id].description = False
                #             self.set_message_privilege(other_usr["id"], True)
                #
                #             # remove points
                #             self.update_reward(room_id, NEGATIVE_REWARD)
                #             self.sessions[room_id].points["history"][-1]["warnings"] += 1
                #
                #         else:
                #             self.sio.emit(
                #                 "text",
                #                 {
                #                     "message": COLOR_MESSAGE.format(
                #                         color=WARNING_COLOR,
                #                         message=(
                #                             "Wait for your partner fo send at least one message"
                #                         ),
                #                     ),
                #                     "room": room_id,
                #                     "receiver_id": curr_usr["id"],
                #                     "html": True,
                #                 },
                #             )
                #
                #     # user wants to terminate experiment
                #     if event == "abort":
                #         self.terminate_experiment(room_id)
                #
                # else:
                #     # commands from users
                #     # set wizard
                #     if data["command"] == "role:wizard":
                #         self.set_wizard_role(room_id, user_id)
                #
                #     elif data["command"] == "abort":
                #         self.terminate_experiment(room_id)
                #
                #     elif data["command"] == "reset:description":
                #         if curr_usr["role"] == "wizard":
                #             # Allow player to send a new message
                #             self.sessions[room_id].description = False
                #             self.set_message_privilege(other_usr["id"], True)
                #             self.log_event("reset_description", dict(), room_id)
                #             self.sio.emit(
                #                 "text",
                #                 {
                #                     "message": "Your partner can now send a new description",
                #                     "room": room_id,
                #                     "receiver_id": user_id,
                #                 },
                #             )
                #             self.sio.emit(
                #                 "text",
                #                 {
                #                     "message": "You can now send a new message, remember you can only send one message per board",
                #                     "room": room_id,
                #                     "receiver_id": other_usr["id"],
                #                 },
                #             )
                #
                #     else:
                #         self.sio.emit(
                #             "text",
                #             {
                #                 "message": "Sorry, but I do not understand this command.",
                #                 "room": room_id,
                #                 "receiver_id": user_id,
                #             },
                #         )

        @self.sio.event
        def status(data):
            """Triggered when a user enters or leaves a room."""
            room_id = data["room"]
            event = data["type"]
            user = data["user"]

            # automatically creates a new session if not present
            this_session = self.sessions[room_id]
            timer = RoomTimer(self.timeout_close_game, room_id)
            this_session.timer = timer

            # don't do this for the bot itself
            if user["id"] == self.user:
                return

            # someone joined a task room
            if event == "join":
                # inform everyone about the join event
                self.sio.emit(
                    "text",
                    {
                        "message": f"{user['name']} has joined the game. ",
                        "room": room_id,
                    },
                )

                this_session.players.append({**user, "status": "joined", "wins": 0})

                if len(this_session.players) < 2:
                    self.sio.emit(
                        "text",
                        {"message": "Let's wait for more players.", "room": room_id},
                    )
                else:
                    self.next_round(room_id)
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
            word_to_guess = this_session.word_to_guess
            new_line = '\n'

            if user_id == self.user:
                return

            # explainer
            if this_session.explainer == user_id:
                LOG.debug(f"{data['user']['name']} is the explainer.")
                message = data["message"].lower()
                # check whether the user used a forbidden word
                for taboo_word in self.taboo_data[word_to_guess]:
                    if taboo_word.lower() in message:
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
                        this_session.played_words.append(word_to_guess)
                        this_session.rounds_left -= 1
                        self.update_reward(room_id, 0)
                        self.update_title_points(room_id, 0)
                        self.next_round(room_id)


                # check whether the user used the word to guess
                if word_to_guess.lower() in message:
                    self.sio.emit(
                        "text",
                        {
                            "message": f"You used the word to guess '{word_to_guess}'! {new_line}GAME OVER",
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

                    this_session.played_words.append(word_to_guess)
                    this_session.rounds_left -= 1
                    self.update_reward(room_id, 0)
                    self.update_title_points(room_id, 0)
                    self.next_round(room_id)
            # Guesser guesses word
            elif word_to_guess.lower() in data["message"].lower():
                self.sio.emit(
                    "text",
                    {
                        "message": f"{word_to_guess} was correct! {new_line}YOU WON :)",
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
                this_session.played_words.append(word_to_guess)
                this_session.rounds_left -= 1
                self.update_reward(room_id, 1)
                self.update_title_points(room_id, 1)
                self.next_round(room_id)

    def remove_punctuation(text: str) -> str:
        text = text.translate(str.maketrans("", "", string.punctuation))
        return text

    def timeout_close_game(self, room_id, status):
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
            # start a game
            # 1) Choose a word
            this_session.word_to_guess = random.choice(
                list(self.taboo_data.keys())
            )
            # 2) Choose an explainer and a guesser
            this_session.pick_explainer()
            this_session.pick_guesser()

            # 3) Tell the explainer about the word
            word_to_guess = this_session.word_to_guess
            taboo_words = ", ".join(self.taboo_data[word_to_guess])
            self.sio.emit(
                "text",
                {
                    "message": f"Your task is to explain the word {word_to_guess}. You cannot use the following words: {taboo_words}",
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
                            "receiver_id": player["id"],
                        },
                    )


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = TabooBot.create_argparser()

    parser.add_argument(
        "--taboo_data",
        help="json file containing words",
        default=os.environ.get("TABOO_DATA"),
    )
    args = parser.parse_args()

    # create bot instance
    taboo_bot = TabooBot(args.token, args.user, args.task, args.host, args.port)
    # taboo_bot.taboo_data = args.taboo_data
    # connect to chat server
    taboo_bot.run()
