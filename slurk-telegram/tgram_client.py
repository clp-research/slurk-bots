import json
from pathlib import Path
from multiprocessing import Process

import time

import requests


class TeleClient:
    def __init__(self, token):
        self.token = token
        self.offset = 0
    
    def process_updates(self, updates):
        updates = json.loads(updates)
        to_process = updates.get("result")
        if to_process:
            for update in to_process:
                self.offset = update["update_id"] + 1
                self.process_update(update)

    def process_update(self, update):
        message = update["message"]["text"]
        chat_id = update["message"]["from"]["id"]
        nickname = update["message"]["from"]["username"]
        


    def run(self):
        while True:
            updates = requests.get(
                f"https://api.telegram.org/bot{self.token}/getUpdates",
                params={'offset': self.offset}
            )
            self.process_updates(updates.text)
            time.sleep(2)  

    def send_message(self, message, chat_id):
        requests.post(
            f'https://api.telegram.org/bot{self.token}/sendMessage?chat_id={chat_id}&text={message}'
        )


if __name__ == "__main__":
    token = Path("token.txt").read_text()
    bot = TeleClient(token)
    bot.run()
    # p = Process(target=bot.run)
    # p.start()
    # # bot.run()
    # p.join()