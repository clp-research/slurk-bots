import logging
from threading import Timer

import requests

from templates import TaskBot


TIMEOUT_TIMER = 60  # minutes


class RoomTimer:
    def __init__(self, time, function, room_id):
        self.function = function
        self.time = time
        self.room_id = room_id
        self.start_timer()

    def start_timer(self):
        self.timer = Timer(self.time*60, self.function, args=[self.room_id])
        self.timer.start()

    def snooze(self):
        self.timer.cancel()
        self.start_timer()
        logging.debug("snooze")

    def cancel(self):
        self.timer.cancel()


class EchoBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timers_per_room = dict()
        self.register_callbacks()

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
        def new_task_room(data):
            room_id = data["room"]
            self.join_task_room()
            self.timers_per_room[room_id] = RoomTimer(
                TIMEOUT_TIMER, self.close_room, room_id
            )

        @self.sio.event
        def text_message(data):
            if self.user == data["user"]["id"]:
                return
            else:
                room_id = data["room"]
                timer = self.timers_per_room.get(room_id)
                timer.snooze()

            logging.debug(f"I got a message, let's send it back!: {data}")

            options = {}
            if data["private"]:
                logging.debug("It was actually a private message o.O")
                options["receiver_id"] = data["user"]["id"]

            message = data["message"]
            if message.lower() == "hello":
                message = "World!"
            elif message.lower() == "ping":
                message = "Pong!"

            self.sio.emit(
                "text",
                {
                    "room": data["room"],
                    "message": message,
                    **options
                },
                callback=self.message_callback
            )

        @self.sio.event
        def image_message(data):
            if self.user == data["user"]["id"]:
                return
            else:
                room_id = data["room"]
                timer = self.timers_per_room.get(room_id)
                timer.snooze()

            logging.debug(f"I got an image, let's send it back!: {data}")

            options = {}
            if data["private"]:
                logging.debug("It was actually a private image o.O")
                options["receiver_id"] = data["user"]["id"]

            self.sio.emit(
                "image",
                {
                    "room": data["room"],
                    "url": data["url"],
                    "width": data["width"],
                    "height": data["height"],
                    **options
                },
                callback=self.message_callback
            )


if __name__ == "__main__":
    # set up loggingging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = EchoBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    echo_bot = EchoBot(args.token, args.user, args.task, args.host, args.port)
    # connect to chat server
    echo_bot.run()
