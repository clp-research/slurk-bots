"""
A simple math bot where two parties ask each other simple math
questions and the bot check the correct answer.

The bot consists of several functions:
on_command - provides interface for users to create and answer math questions
_command_question - provides logic for question creation
_command_answer - provides logic for comparing proposed answer with the solution
on_new_task_room - listen on "new_task_room" event and join the room
get_message_response - callback to verify successful emits

You can create question and answer using "/question" and "/answer" e.g.
"/question 3+6" (where the appropriate response is "/answer 9").

To ensure users are permitted to send commands, please set "message_command: true"
when creating token for new users and math bot.
"""

from socketIO_client import BaseNamespace, SocketIO

import sys
import os
import argparse

TASK_ID = None


class ChatNamespace(BaseNamespace):
    def __init__(self, io, path):
        super().__init__(io, path)
        self.id = None
        self.emit('ready')
        self.questions = {}

    @staticmethod
    def get_message_response(success, error=None):
        if not success:
            print("Could not send message:", error)
            sys.exit(2)

        print("message sent successfully")
        sys.stdout.flush()

    def on_command(self, data):
        """
        Process the question and answer turns for both parties.
        """
        if data["command"].startswith("question"):
            self.emit("text", {'room': data['room'], 'msg': 'You have set a question', 'receiver_id': data['user']['id']}, self.get_message_response)
            self._command_question(data)
        elif data["command"].startswith("answer"):
            self.emit("text", {'room': data['room'], 'msg': 'You have set an answer', 'receiver_id': data['user']['id']}, self.get_message_response)
            self._command_answer(data)
        else:
            self.emit("text", {'room': data['room'], 'msg': '{} is not a valid command'.format(data['command']), 
                               'receiver_id': data['user']['id']}, self.get_message_response)

    def _command_question(self, data):
        """
        Broadcast math question to the room.
        """
        if 'room' in data and data['room']:
            query = data["command"].split(' ')[-1]
            self.questions[data["room"]] = query
            self.questions["sender"] = data["user"]["id"]
            self.emit("text", {'room': data['room'], 'msg': "A math question has been created!"}, self.get_message_response)
            self.emit("text", {'room': data['room'], 'msg': query}, self.get_message_response)

    def _command_answer(self, data):
        """
        Check if the provided answer is correct.
        """
        sender = data["user"]["id"]
        answer = data["command"].split(' ')[-1]

        if 'room' in data and data['room'] and self.questions["sender"] != sender:
            self.emit("text", {'room': data['room'], 'msg': "Your answer is {}".format(answer), 'receiver_id' : sender}, self.get_message_response)
            self.emit("text", {'room': data['room'], 'msg': "The proposed answer is {}".format(answer)}, self.get_message_response)
            if eval(self.questions[data["room"]]) == int(answer):
                self.emit("text", {'room': data['room'], 'msg': "Turns out {}'s answer is correct!".format(data['user']['name'])}, self.get_message_response)
            else:
                self.emit("text", {'room': data['room'], 'msg': "Unfortunately {}'s answer is wrong, please try again!".format(data['user']['name'])}, self.get_message_response)

    def on_new_task_room(self, data):
        """
        Listen to events and join the room when the task matches the ID.
        """
        if data['task'] == TASK_ID:
            self.emit("join_room", {'user': self.id, 'room': data['room']})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Math Bot')

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

    if 'MATH_TASK_ID' in os.environ:
        task_id = {'default':os.environ['MATH_TASK_ID']}
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

    uri = args.chat_host
    if args.chat_port:
        uri += f":{args.chat_port}"

    sys.stdout.flush()
    uri += "/api/v2"
    token = args.token

    # We pass token and name in request header
    socketIO = SocketIO(args.chat_host, args.chat_port,
                        headers={'Authorization': args.token, 'Name': 'Math Bot'},
                        Namespace=ChatNamespace)
    socketIO.wait()

