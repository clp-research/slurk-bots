import logging
import os
import string
import random
from time import sleep
from threading import Timer

import requests
from templates import TaskBot

import logging

from reference.config import EXPLAINER_HTML, GUESSER_HTML, \
    EMPTY_GRID, GRIDS, GRIDS_PER_ROOM, TASK_GREETING, \
    COLOR_MESSAGE, STANDARD_COLOR, WARNING_COLOR, \
    TIMEOUT_TIMER, LEAVE_TIMER, WAITING_ROOM_TIMER,\
    INPUT_FIELD_UNRESP_GUESSER, INPUT_FIELD_UNRESP_EXPLAINER

from reference.dataloader import Dataloader
from reference.grid import GridManager

TARGET_GRID_NAMES = {"1": "first", "2": "second", "3": "third"}
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
        self.players = list()
        self.grids = Dataloader(GRIDS, GRIDS_PER_ROOM)
        self.grid_manager = GridManager(EMPTY_GRID)
        self.guesser = None
        self.explainer = None
        self.points = {
            "score": 0,
            "history": [{"correct": 0, "wrong": 0, "warnings": 0}],
        }
        self.turn = None
        self.game_over = False
        self.timer = None

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

class ReferenceBot(TaskBot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.sessions = SessionManager()
        self.register_callbacks()

    def post_init(self, waiting_room):
        """
        save extra variables after the __init__() method has been called
        and create the init_base_dict: a dictionary containing
        needed arguments for the init event to send to the JS frontend
        """
        self.waiting_room = waiting_room
        # self.version = version


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

            self.move_divider(room_id, 20, 80)

            self.sessions.create_session(room_id)
            timer = RoomTimer(self.timeout_close_game, room_id)
            self.sessions[room_id].timer = timer

            for usr in data["users"]:
                self.sessions[room_id].players.append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )

                # cancel waiting-room-timers
                if usr["id"] in self.sessions.waiting_room_timers:
                    logging.debug(f"Cancelling waiting room timer for user {usr['id']}")
                    self.sessions.waiting_room_timers[usr["id"]].cancel()
                    self.sessions.waiting_room_timers.pop(usr["id"])

            # join the newly created room
            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )

        # 2) Choose an explainer/guesser
            self.assign_roles(room_id)

            # send_instructions
            for player in self.sessions[room_id].players:
                self.send_instr(room_id, player["id"])

            self.set_message_privilege(room_id, self.sessions[room_id].explainer, False)
            self.make_input_field_unresponsive(room_id, self.sessions[room_id].explainer)

            self.set_message_privilege(room_id, self.sessions[room_id].guesser, False)
            self.make_input_field_unresponsive(room_id, self.sessions[room_id].guesser)
            # self.set_message_privilege(room_id,self.sessions[room_id].guesser, True)
            # # assign writing rights to other user
            # self.give_writing_rights(room_id, self.sessions[room_id].guesser)

            for line in TASK_GREETING:
                self.sio.emit(
                    "text",
                    {
                        "message": COLOR_MESSAGE.format(
                            color= "#800080", message=line
                        ),
                        "room": room_id,
                        "html": True,
                    },
                )
            sleep(2)

            self.send_message_to_user(STANDARD_COLOR, "Are you ready?"
                    " Once you click on 'yes' you will see the grids. <br> <br>"
                    "<button class='message_button' onclick=\"confirm_ready('yes')\">YES</button> "
                    "<button class='message_button' onclick=\"confirm_ready('no')\">NO</button>", room_id)

    def assign_roles(self, room_id):
        # assuming there are 2 players
        session = self.sessions[room_id]

        guesser_index = random.randint(0, len(session.players) - 1)
        explainer_index = 1 - guesser_index
        session.players[explainer_index]["role"] = "explainer"
        session.explainer = session.players[explainer_index]["id"]
        self.log_event("player", session.players[explainer_index], room_id)


        session.players[guesser_index]["role"] = "guesser"
        session.guesser = session.players[guesser_index]["id"]
        self.log_event("player", session.players[guesser_index], room_id)

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
            # it sends to itself, user id = null, receiver if = null
            self.sio.emit("text", {"message": data["message"], "room": data["room"]})

        @self.sio.event
        def status(data):
            """Triggered when a user enters or leaves a room."""
            room_id = data["room"]
            event = data["type"]
            user = data["user"]

            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{user['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not task.ok:
                logging.error(
                    f"Could not set task instruction title: {task.status_code}"
                )
                task.raise_for_status()
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

            # # don't do this for the bot itself
            # if user["id"] == self.user:
            #     return

            # someone joined waiting room
            if room_id == self.waiting_room:
                if event == "join":
                    if user["id"] not in self.sessions.waiting_room_timers:
                        # start no_partner timer
                        timer = Timer(
                            WAITING_ROOM_TIMER * 60,
                            self.timeout_waiting_room,
                            args=[user],
                        )
                        timer.start()
                        logging.debug(f"Started a waiting room/no partner timer: {WAITING_ROOM_TIMER}")
                        self.sessions.waiting_room_timers[user["id"]] = timer
                return

            elif room_id in self.sessions:

                this_session = self.sessions[room_id]
                curr_usr, other_usr = this_session.players
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr
                # someone joined a task room
                if event == "join":
                    # inform everyone about the join event
                    self.send_message_to_user(STANDARD_COLOR,
                        f"{user['name']} has joined the game.", room_id, other_usr["id"]
                    )

                    # user joined
                    self.sessions[room_id].timer.user_joined(curr_usr["id"])

                    # cancel timer
                    logging.debug(
                        f"Cancelling Timer: left room for user {curr_usr['name']}"
                    )
                    timer = this_session.timer.left_room.get(curr_usr["id"])
                    if timer is not None:
                        timer.cancel()

                    # Change to role check like in recolage?
                    if self.sessions[room_id].guesser is not None and self.sessions[room_id].explainer is not None:
                        LOG.debug("RESTART ROUND")
                        self.reload_state(room_id, curr_usr["id"])


                elif event == "leave":
                    # self.send_message_to_user(f"{user['name']} has left the game.", room_id)
                    if self.sessions[room_id].game_over is False:
                        self.send_message_to_user(STANDARD_COLOR,
                            f"{user['name']} has left the game. "
                            f"Please wait a bit, your partner may rejoin.", room_id, other_usr["id"])

                        # start timer since user left the room
                        logging.debug(
                            f"Starting Timer: left room for user {curr_usr['name']}"
                        )
                        self.sessions[room_id].timer.user_left(curr_usr["id"])




        @self.sio.event
        def text_message(data):
            """Parse user messages."""
            # LOG.debug(
            #     f"Received a message from {data['user']['name']}: {data['message']}"
            # )
            room_id = data["room"]
            user_id = data["user"]["id"]

            if room_id not in self.sessions or user_id == self.user:
                return

            this_session = self.sessions[room_id]
            this_session.timer.reset()

            if this_session.explainer == user_id:
                # EXPLAINER sent the command

                # OLD: means that new turn began
                # self.log_event("turn", dict(), room_id)

                self.log_event("clue", {"content": data['message']}, room_id)

                self.set_message_privilege(room_id, self.sessions[room_id].explainer, False)
                self.make_input_field_unresponsive(room_id, self.sessions[room_id].explainer)
                # self.set_message_privilege(room_id,self.sessions[room_id].guesser, True)
                # # assign writing rights to other user
                # self.give_writing_rights(room_id, self.sessions[room_id].guesser)

                LOG.debug(f"Button{this_session.button_number}")
                self.send_message_to_user(STANDARD_COLOR,  f" Click on the number of the grid the description above matches. <br> <br>"
                                                          f"<button class='message_button' id='Button{this_session.button_number}' onclick=\"choose_grid('1')\">1</button> "
                                                          f"<button class='message_button' id='Button{this_session.button_number + 1}' onclick=\"choose_grid('2')\">2</button>"
                                                          f"<button class='message_button' id='Button{this_session.button_number + 2}' onclick=\"choose_grid('3')\">3</button>",
                room_id, this_session.guesser)



        @self.sio.event
        def command(data):
            """Parse user commands."""
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if user_id == self.user:
                return

            if room_id not in self.sessions:
                return

            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            self.sessions[room_id].timer.reset()

            if isinstance(data["command"], dict):
                # commands from interface
                event = data["command"]["event"]
                if event == "confirm_ready":
                    if data["command"]["answer"] == "yes":
                        self._command_ready(room_id, user_id)
                    elif data["command"]["answer"] == "no":
                        self.send_message_to_user(STANDARD_COLOR,
                            "OK, read the instructions carefully and click on <yes> once you are ready.",
                            room_id,
                            user_id,
                        )
                    return
                elif event == "choose_grid":
                    LOG.debug(f"{self.sessions[room_id].button_number}")
                    LOG.debug(f"Button{self.sessions[room_id].button_number}")
                    self.send_message_to_user(STANDARD_COLOR,
                                              f"Guess was submitted. You can not change it."
                                              f"<script> document.getElementById('Button{self.sessions[room_id].button_number}').disabled = true;</script>"
                                              f"<script> document.getElementById('Button{self.sessions[room_id].button_number + 1}').disabled = true;</script>"
                                              f"<script> document.getElementById('Button{self.sessions[room_id].button_number + 2}').disabled = true;</script>",
                                              room_id,
                                              self.sessions[room_id].guesser)
                    guess = data["command"]["answer"]
                    LOG.debug(f"GUESS was {guess}")

                    self.log_event("guess", {"content": guess}, room_id)

                    guess_correct = correct_guess(guess, self.sessions[room_id].grids[0][6][1])
                    if guess_correct:
                        self.send_message_to_user(STANDARD_COLOR,
                                                      f"GUESS was correct ✅!"
                                                      f"You both win this round.",
                                                      room_id,
                                                      )
                        self.update_reward(room_id, 1)
                        self.log_event("correct guess", {"content": guess}, room_id)
                    else:
                        self.send_message_to_user(WARNING_COLOR,
                                                      f"GUESS was false ❌."
                                                      f"You both lose this round.",

                                                      room_id,
                                                      )
                        self.update_reward(room_id, 0)
                        self.log_event("false guess", {"content": guess}, room_id)


                    self.load_next_game(room_id)


    def _command_ready(self, room_id, user):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user:
            curr_usr, other_usr = other_usr, curr_usr

        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            sleep(0.5)
            self.send_message_to_user(STANDARD_COLOR,
                "You have already  clicked 'ready'.", room_id, curr_usr["id"]
            )

            return
        curr_usr["status"] = "ready"

        # both
        if other_usr["status"] == "ready":
            self.send_message_to_user(STANDARD_COLOR, "Woo-Hoo! The game will begin now.", room_id)
            self.start_round(room_id)
        else:
            self.send_message_to_user(STANDARD_COLOR,
                "Now, waiting for your partner to click 'ready'.",
                room_id,
                curr_usr["id"],
            )

    def send_instr(self, room_id, user_id):
        if user_id == self.sessions[room_id].explainer:
            # LOG.debug("instruction to explainer sent")
            message = f"{EXPLAINER_HTML}"
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": "mark_target_grid",
                        "message": "Target grid"
                    },
                    "room": room_id,
                    "receiver_id": user_id,
                }
            )

        else:
            message = f"{GUESSER_HTML}"

        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "send_instr",
                    "message": message
                },
                "room": room_id,
                "receiver_id": user_id,
            }
        )
        self.sio.emit(
            "message_command",
            {
                "command": {
                    "event": "show_grid",
                    "message": f"{EMPTY_GRID}"
                },
                "room": room_id,
                "receiver_id": user_id,
            }
        )
        sleep(1)

    def load_next_game(self, room_id):

        # reset timer here?
        self.sessions[room_id].timer.reset()

        # grid list gets smaller, next round starts
        self.sessions[room_id].grids.pop(0)
        if not self.sessions[room_id].grids:
            self.terminate_experiment(room_id)
            return
        self.start_round(room_id)

    def reload_state(self, room_id, user):
        if not self.sessions[room_id].grids:
            self.terminate_experiment(room_id)
            return

        LOG.debug(f'Reload state for {user}')
        self.send_instr(room_id, user)
        if self.sessions[room_id].turn == user:
            self.set_message_privilege(room_id, user, True)
            self.give_writing_rights(room_id, user)
        grid_instance = self.sessions[room_id].grids[0]
        if user == self.sessions[room_id].explainer:
            self.show_items(room_id, grid_instance[:3], self.sessions[room_id].explainer)
        else:
            self.show_items(room_id, grid_instance[3:6], self.sessions[room_id].guesser)

    def start_round(self, room_id):
        if not self.sessions[room_id].grids:
            self.terminate_experiment(room_id)
            return

        round_n = (GRIDS_PER_ROOM - len(self.sessions[room_id].grids)) + 1
        self.sessions[room_id].button_number = round_n * 3

        # try to log the round number
        self.log_event("round", {"number": round_n}, room_id)

        # in this game 1 round consists of only 1 turn!
        self.log_event("turn", dict(), room_id)

        self.send_message_to_user(STANDARD_COLOR, f"Let's start round {round_n}, the grids are updated!.", room_id)
        grid_instance = self.sessions[room_id].grids[0]
        self.log_event("grid type", {"content": f"{grid_instance[-1][1]}"}, room_id)
        self.log_event("target grid", {"content": f"{grid_instance[-2][1]}"}, room_id)
        self.show_items(room_id, grid_instance[:3], self.sessions[room_id].explainer)
        self.show_items(room_id, grid_instance[3:6], self.sessions[room_id].guesser)
        self.send_message_to_user(STANDARD_COLOR, "Generate the description for the given target.",
                                  room_id, self.sessions[room_id].explainer)
        self.send_message_to_user(STANDARD_COLOR, "Wait for the description from the explainer.",
                                  room_id, self.sessions[room_id].guesser)

        # update writing_rights
        self.set_message_privilege(room_id, self.sessions[room_id].explainer, True)
        # assign writing rights to other user
        self.give_writing_rights(room_id, self.sessions[room_id].explainer)
        self.set_message_privilege(room_id, self.sessions[room_id].guesser, False)
        self.make_input_field_unresponsive(room_id, self.sessions[room_id].guesser)

    def show_items(self, room_id, grid_instance, user_id):
        for i in range(len(grid_instance)):
            updated_grid = self.sessions[room_id].grid_manager.update_grid(grid_instance[i][1])
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "event": f"update_grid{i+1}",
                        "message": updated_grid
                    },
                    "room": room_id,
                    "receiver_id": user_id,
                }
            )

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

    def timeout_waiting_room(self, user):
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
        # self.confirmation_code(room["id"], "timeout_waiting_room")
        self.remove_user_from_room(user["id"], room["id"])

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

    def room_to_read_only(self, room_id):
        """Set room to read only."""
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

        # remove user from room
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

    def terminate_experiment(self, room_id):
        self.send_message_to_user(STANDARD_COLOR, "The experiment is over 🎉 🎉 thank you very much for your time!",
                                  room_id)
        for player in self.sessions[room_id].players:
            self.confirmation_code(room_id, "success", player["id"])
        # self.confirmation_code(room_id, "success")
        self.close_game(room_id)

    def timeout_close_game(self, room_id, status):

        self.send_message_to_user(STANDARD_COLOR, "The room is closing because of inactivity",
                                  room_id)
        for player in self.sessions[room_id].players:
            self.confirmation_code(room_id, status, player["id"])
        # self.confirmation_code(room_id, status)
        self.close_game(room_id)

    def close_game(self, room_id):
        self.send_message_to_user(STANDARD_COLOR, "The room is closing, see you next time 👋",
                                  room_id)
        self.sessions[room_id].game_over = True
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

    def confirmation_code(self, room_id, status, user_id):
        """Generate AMT token that will be sent to each player."""
        amt_token = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if room_id in self.sessions:
            points = self.sessions[room_id].points
        else:
            points = 0
            logging.debug(f"Room not in self sessions {points}")
        self.log_event(
            "confirmation_log",
            {"status_txt": status, "amt_token": amt_token, "receiver": user_id,
             "points": points},
            room_id,
        )

        self.send_message_to_user(STANDARD_COLOR, "Please remember to "
                        "save your token before you close this browser window. "
                        f"Your token: {amt_token}", room_id, user_id)

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
        if value:
            self.sessions[room_id].turn = user_id
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
        if user_id == self.sessions[room_id].explainer:
            message = INPUT_FIELD_UNRESP_EXPLAINER

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "placeholder",
                "value": f"{message}",
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


def correct_guess(guess, answer):
    return answer == TARGET_GRID_NAMES[guess]





if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = ReferenceBot.create_argparser()


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

    args = parser.parse_args()
    logging.debug(args)

    # create bot instance
    bot = ReferenceBot(args.token, args.user, args.task, args.host, args.port)

    bot.post_init(args.waiting_room)

    # connect to chat server
    bot.run()