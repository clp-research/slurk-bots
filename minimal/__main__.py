import logging

import requests

from templates import Bot


class MinimalBot(Bot):
    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            # get the id of the room that was entered
            room_id = data["room"]
            # get the id of the user that just joined a room
            user_id = data["user"]

            logging.debug(f"User {user_id} entered the room {room_id}")

            # based on the id retrieve additional information
            response = requests.get(
                f"{self.uri}/users/{user_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            # verify that the request was successful
            self.request_feedback(response, "MinimalBot requests user info")
            # read out information delivered with the response
            user = response.json()
            self.sio.emit(
                "text", {"message": f'Hi^o^ I am a {user["name"]}!', "room": room_id}
            )

            # retrieve all log entries for this room and user
            response = requests.get(
                f"{self.uri}/rooms/{room_id}/users/{user_id}/logs",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "MinimalBot requests logs")
            logs = response.json()
            for log_entry in logs:
                logging.info(
                    f'- status: {log_entry["event"]}, data: {log_entry["data"]}'
                )


if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = MinimalBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    minimal_bot = MinimalBot(args.token, args.user, args.host, args.port)
    # connect to chat server
    minimal_bot.run()
