from collections import defaultdict
import logging
import json
from multiprocessing import Process
from pathlib import Path
import time

import requests

from templates import TaskBot


TOKEN = Path("slurk-telegram/token.txt").read_text()


class TelegramBot(TaskBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telegram_token = TOKEN
        self.offset = 0
        self.chat2room = dict()
        self.room2chat = defaultdict(list)
        self.waitlist = set()
        self.sio.connect(
            self.uri,
            headers={
                "Authorization": f"Bearer {self.token}",
                "user": str(self.user)
            },
            namespaces="/",
        )

    def run(self):
        """overwrite run function from template, connection in init"""
        self.sio.wait()

    def process_updates(self, updates):
        updates = json.loads(updates)
        to_process = updates.get("result")
        if to_process:
            for update in to_process:
                self.offset = update["update_id"] + 1
                self.process_update(update)

    def get_token_info(self, token):
        return json.loads(
            requests.get(
                f"{self.uri}/tokens/{token}"
            ).text
        )

    def register_telegram_user(self, chat_id, room_id):
        logging.debug(f"registering {chat_id} in {room_id}")
        self.chat2room[chat_id] = room_id
        self.room2chat[room_id].append(chat_id)

    def process_update(self, update):
        message = update["message"]["text"]
        chat_id = update["message"]["from"]["id"]
        nickname = update["message"]["from"]["username"]
        
        #self.send_message(message, chat_id)
        room_id = 2
        self.register_telegram_user(chat_id, room_id)
        room_id = self.chat2room[chat_id]

        logging.debug(f"SENDING TELEGRAM MESSAGE TO ROOM {room_id}")

        self.sio.emit(
            "text",
            {
                "room": room_id,
                "message": message,
                **dict()
            }
        )

        # # # TODO: apply check, for now register user and forward message
        # if chat_id not in self.chat2room:
        #     if "/login" not in message:
        #         if chat_id not in self.waitlist:
        #             self.send_message("Please enter your Token: /login YOUR TOKEN HERE", chat_id)
        #             self.waitlist.add(chat_id)
        #         else:
        #             self.send_message("invalid token, try again", chat_id)

        #     else:
        #         token = message.replace("/login", "").strip()
        #         token_info = self.get_token_info(token)
                
        #         if "code" in token_info and token_info["code"] == 404:
        #             self.send_message("invalid token, try again", chat_id)
        #         else:
        #             room_id = token_info["room_id"]
        #             self.register_telegram_user(room_id, chat_id)
        #             if chat_id in self.waitlist:
        #                 self.waitlist.remove(chat_id)

        # else:
        #     room_id = self.chat_id2room[chat_id]
        #     self.sio.emit(
        #             "text",
        #             {
        #                 "room": room_id,
        #                 "message": message,
        #                 **dict()
        #             },
        #             callback=self.message_callback
        #         )


    def run_telegram(self):
        while True:
            updates = requests.get(
                f"https://api.telegram.org/bot{self.telegram_token}/getUpdates",
                params={'offset': self.offset}
            )
            self.process_updates(updates.text)
            time.sleep(2)  

    def send_message(self, message, chat_id):
        requests.post(
            f'https://api.telegram.org/bot{self.telegram_token}/sendMessage?chat_id={chat_id}&text={message}'
        )

    def register_callbacks(self):
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
            # for room_id in self.room2chat[data["room"]]:
            #     self.send_message(message, room_id)
            #     logging.debug(room_id)

            self.send_message(message, 17817222)

            logging.debug("HERE GOES MESSAGE")
            # self.sio.emit(
            #     "text",
            #     {
            #         "room": data["room"],
            #         "message": message,
            #         **options
            #     },
            #     callback=self.message_callback
            # )

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
    parser = TelegramBot.create_argparser()
    args = parser.parse_args()

    # create bot instance
    telegram_bot = TelegramBot(args.token, args.user, args.task, args.host, args.port)
    # telegram_bot.create_telegram_bot()
    # connect to chat server
    # p = Process(target=telegram_bot.run_telegram)
    # p.start()
    # telegram_bot.start_telegram_client()
    telegram_bot.run()
    logging.debug("CIAOCIAOCIAO")
    # p.join()
