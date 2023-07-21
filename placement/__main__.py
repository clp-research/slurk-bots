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


class Placement(TaskBot):
    timers_per_room = dict()
    latest_board_per_room = dict()

    def on_task_room_creation(self, data):
        room_id = data["room"]

        logging.debug(data)

        self.timers_per_room[room_id] = RoomTimer(
            self.close_room, room_id
        )

        # map a dictionary user_id: last board
        self.latest_board_per_room[room_id] = dict()
        for user in data["users"]:
            self.latest_board_per_room[room_id][user["id"]] = None

    def close_room(self, room_id):
        self.room_to_read_only(room_id)

        # delete data structures
        self.timers_per_room.pop(room_id)
        self.latest_board_per_room.pop(room_id)

    def calculate_score(self, board1, board2):
        return random.randint(0, 100)

    def register_callbacks(self):
        @self.sio.event
        def command(data):
            """Parse user commands."""
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if user_id == self.user:
                return

            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            if isinstance(data["command"], dict):
                if data["command"]["event"] == "board_logging":
                    board = data["command"]["board"]

                    # update latest board for this user
                    self.latest_board_per_room[room_id][user_id] = board

            else:
                if data["command"] == "stop":
                    # retrieve latest board and calculate score
                    board1, board2 = list(self.latest_board_per_room[room_id].values())
                    score = self.calculate_score(board1, board2)

                    # log extra event
                    self.log_event("score", {"score": score}, room_id)

                    # inform users the game is over
                    self.sio.emit(
                        "text",
                        {
                            "message": f"your score is {score}. The experiment is over.",
                            "room": room_id,
                            "html": True,
                        },
                    )

                    self.close_room(room_id)

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


if __name__ == "__main__":
    # set up loggingging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = Placement.create_argparser()
    args = parser.parse_args()

    # create bot instance
    bot = Placement(args.token, args.user, args.task, args.host, args.port)
    # connect to chat server
    bot.run()
