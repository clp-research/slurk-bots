import logging
import random
from threading import Timer

import requests

from templates import TaskBot


TIMEOUT_TIMER = 60  # minutes


class RoomTimer:
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()

    def start_timer(self):
        self.timer = Timer(TIMEOUT_TIMER * 60, self.function, args=[self.room_id])
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.debug("reset timer")

    def cancel(self):
        self.timer.cancel()


class StrictTurnTakingBot(TaskBot):
    timers_per_room = dict()
    users_per_room = dict()

    def on_task_room_creation(self, data):
        room_id = data["room"]
        self.users_per_room[room_id] = list()

        self.timers_per_room[room_id] = RoomTimer(self.close_room, room_id)

        # assign random writing rights and inform the users
        rights = [True, False]
        random.shuffle(rights)
        for usr, writing_right in zip(data["users"], rights):
            # update writing_rights
            self.set_message_privilege(usr["id"], writing_right)
            self.users_per_room[room_id].append(usr)

            if writing_right is True:
                self.sio.emit(
                    "text",
                    {
                        "room": data["room"],
                        "message": "You can send a message to your partner",
                        "receiver_id": usr["id"],
                    },
                )
            else:
                self.sio.emit(
                    "text",
                    {
                        "room": data["room"],
                        "message": "You will only be able to send a message after your partner",
                        "receiver_id": usr["id"],
                    },
                )

                # make input field unresponsive
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/text",
                    json={
                        "attribute": "style",
                        "value": "pointer-events: none",
                        "receiver_id": usr["id"],
                    },
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/text",
                    json={
                        "attribute": "placeholder",
                        "value": "Wait for a message from your partner",
                        "receiver_id": usr["id"],
                    },
                    headers={"Authorization": f"Bearer {self.token}"},
                )

    def close_room(self, room_id):
        self.room_to_read_only(room_id)
        self.timers_per_room.pop(room_id)
        self.users_per_room.pop(room_id)

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

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only by disabling the text input field
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "Could not set room to read_only")
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "Could not set room to read_only")

        # get users in this room
        response = requests.get(
            f"{self.uri}/rooms/{room_id}/users",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not get user: {response.status_code}")

        users = response.json()
        for user in users:
            if user["id"] != self.user:
                # get current user
                response = requests.get(
                    f"{self.uri}/users/{user['id']}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(
                    response, f"Could not get user: {response.status_code}"
                )
                etag = response.headers["ETag"]

                # remove this user from this room
                response = requests.delete(
                    f"{self.uri}/users/{user['id']}/rooms/{room_id}",
                    headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(
                    response,
                    f"Could not remove user from task room: {response.status_code}",
                )
                logging.debug("Removing user from task room was successful.")

    def register_callbacks(self):
        @self.sio.event
        def text_message(data):
            if self.user == data["user"]["id"]:
                return

            room_id = data["room"]
            timer = self.timers_per_room.get(room_id)
            if timer is not None:
                timer.reset()

            # switch writing rights
            curr_usr, other_usr = self.users_per_room[room_id]
            if curr_usr["id"] != data["user"]["id"]:
                curr_usr, other_usr = other_usr, curr_usr

            # revoke writing rights to current user
            self.set_message_privilege(curr_usr["id"], False)
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "style",
                    "value": "pointer-events: none",
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

            # assign writing rights to other user
            self.set_message_privilege(other_usr["id"], True)
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/attribute/id/text",
                json={
                    "attribute": "style",
                    "value": "pointer-events: auto",
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


if __name__ == "__main__":
    # set up loggingging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = StrictTurnTakingBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    echo_bot = StrictTurnTakingBot(
        args.token, args.user, args.task, args.host, args.port
    )
    # connect to chat server
    echo_bot.run()
