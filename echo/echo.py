import socketio

import sys
import os
import argparse

TASK_ID = None

class EchoBot:
    sio = socketio.Client()
    user_id = None

    def __init__(self, host, port, token):
        self.uri = host
        if port:
            self.uri += f":{port}"
        self.uri += "/api/v2"
        self.token = token
        self.callbacks()

    def run(self):
        self.sio.connect(self.uri, headers={'Authorization': self.token, 'Name': 'Echo'})
        self.sio.wait()

    def callbacks(self):
        @self.sio.event
        def joined_room(data):
            self.user_id = data['user']
            print("joined as", self.user_id)

        @self.sio.event
        def text_message(data):
            if not self.user_id:
                return

            sender = data['user']['id']
            if sender == self.user_id:
                return

            print("I got a message, let's send it back!:", data)

            message = data['msg']
            if message.lower() == "hello":
                message = "World!"
            if message.lower() == "ping":
                message = "Pong!"

            if 'room' in data and data['room']:
                self.sio.emit("text", {'room': data['room'], 'msg': message})
            else:
                print("It was actually a private message oO")
                self.sio.emit("text", {'receiver_id': data['user']['id'], 'msg': message})

def main():
    parser = argparse.ArgumentParser(description='Run Echo bot')

    if 'TOKEN' in os.environ:
        token = {'default': os.environ['TOKEN']}
    else:
        token = {'required': True}

    if 'CHAT_HOST' in os.environ:
        chat_host = {'default': os.environ['CHAT_HOST']}
    else:
        chat_host = {'default': 'http://localhost'}

    if 'CHAT_PORT' in os.environ:
        chat_port = {'default': os.environ['CHAT_PORT']}
    else:
        chat_port = {'default': None}

    if 'ECHO_TASK_ID' in os.environ:
        task_id = {'default': os.environ['ECHO_TASK_ID']}
    else:
        task_id = {'default': None}

    parser.add_argument('-t', '--token',
                        help='token for logging in as bot (see SERVURL/token)',
                        **token)
    parser.add_argument('-c', '--chat_host',
                        help='full URL (protocol, hostname; ending with /) of chat server',
                        **chat_host)
    parser.add_argument('-p', '--chat_port',
                        type=int,
                        help='port of chat server',
                        **chat_port)
    parser.add_argument('--task_id',
                        type=int,
                        help='Task to join',
                        **task_id)
    args = parser.parse_args()
    TASK_ID = args.task_id

    sys.stdout.flush()

    echo_bot = EchoBot(args.chat_host, args.chat_port, args.token)
    echo_bot.run()

if __name__ == '__main__':
    main()
