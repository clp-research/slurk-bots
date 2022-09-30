import logging

import requests

from templates import TaskBot


class CcbtsBot(TaskBot):
    def register_callbacks(self):
        @self.sio.event
        def command(data):
            """Parse user commands."""
            logging.debug(f"Received a command from {data['user']['name']}: {data['command']}")

        @self.sio.event
        def text_message(data):
            if self.user == data["user"]["id"]:
                return

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
    parser = CcbtsBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    ccbts_bot = CcbtsBot(args.token, args.user, args.task, args.host, args.port)
    # connect to chat server
    ccbts_bot.run()
