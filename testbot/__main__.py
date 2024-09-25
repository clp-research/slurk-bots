import logging
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
        self.timer = Timer(
            TIMEOUT_TIMER*60,
            self.function,
            args=[self.room_id]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.debug("reset timer")

    def cancel(self):
        self.timer.cancel()


class EchoBot(TaskBot):
    timers_per_room = dict()

    def on_task_room_creation(self, data):
        room_id = data["room"]

        self.timers_per_room[room_id] = RoomTimer(
            self.close_room, room_id
        )

    def close_room(self, room_id):
        self.room_to_read_only(room_id)
        self.timers_per_room.pop(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only
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

        response = requests.get(
            f"{self.uri}/rooms/{room_id}/users",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            logging.error(f"Could not get user: {response.status_code}")

        users = response.json()
        for user in users:
            if user["id"] != self.user:
                response = requests.get(
                    f"{self.uri}/users/{user['id']}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(f"Could not get user: {response.status_code}")
                    response.raise_for_status()
                etag = response.headers["ETag"]

                response = requests.delete(
                    f"{self.uri}/users/{user['id']}/rooms/{room_id}",
                    headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                )
                if not response.ok:
                    logging.error(
                        f"Could not remove user from task room: {response.status_code}"
                    )
                    response.raise_for_status()
                logging.debug("Removing user from task room was successful.")

    def register_callbacks(self):
        @self.sio.event
        def text_message(data):
            room_id = data["room"]
            user_id = data["user"]["id"]
            if self.user == user_id:
                return

            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/text_to_modify",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"text": data["message"]}
            )


        @self.sio.event
        def command(data):
            if self.user == data["user"]["id"]:
                return

            room_id = data["room"]
            user_id = data["user"]["id"]

            logging.debug(f"I got a message, let's send it back!: {data}")

            if isinstance(data["command"], dict):
                # commands from front end
                event = data["command"]["event"]
                if event == "user_input":
                    message = data["command"]["message"]
                    self.sio.emit(
                        "text",
                        {
                            "room": data["room"],
                            "message": message[::-1],
                            "receiver_id": data["user"]["id"]
                        },
                    )
            else:
                # commands from user
                if data["command"] == "reset":
                    self.sio.emit(
                        "text",
                        {
                            "room": data["room"],
                            "message": "I'm cleaning up for you",
                            "receiver_id": data["user"]["id"],
                        }
                    )

                    self.sio.emit(
                        "message_command",
                        {
                            "command": {"event": "reset"},
                            "room": room_id,
                            "receiver_id": data["user"]["id"],
                        }
                    )


            


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = EchoBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    echo_bot = EchoBot(args.token, args.user, args.task, args.host, args.port)
    # connect to chat server
    echo_bot.run()
