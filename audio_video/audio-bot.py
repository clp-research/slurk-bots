from time import sleep

import urllib3
import requests
import json
import sys
import os
import argparse
import logging

from uuid import uuid1
from socketIO_client import SocketIO, BaseNamespace
from openvidu import Session, Server, OpenViduException

logger = logging.getLogger('audio-bot')

URI = None
TOKEN = None
TASK_ID = None
OPENVIDU_URL = None
OPENVIDU_SECRET = None
OPENVIDU_VERIFY = True

class ChatNamespace(BaseNamespace):
    def __init__(self, io, path):
        super().__init__(io, path)

        self.id = None
        self.server = Server(OPENVIDU_URL, OPENVIDU_SECRET, verify=OPENVIDU_VERIFY)
        self.sessions = {}
        self.emit('ready')

    def on_new_task_room(self, data):
        if data['task'] == TASK_ID:
            self.sessions[data['room']] = {
                'id': self.server.initialize_session(custom_session_id=data['room']),
                'tokens': dict()
            }
            self.emit("join_room", {'user': self.id, 'room': data['room']})

    def on_joined_room(self, data):
        self.id = data['user']
        print(self.id)
        resp = requests.get(f"{URI}/room/{data['room']}", headers={'Authorization': f"Token {TOKEN}"})
        if resp.status_code == 200:
            room = json.loads(resp.content)
            for id in room['current_users'].keys():
                self.send_token_to_client(data['room'], int(id))

    def on_status(self, data):
        room = data['room']
        user_id = int(data['user']['id'])
        if data['type'] == 'join':
            self.send_token_to_client(room, user_id)
        elif data['type'] == 'leave':
            session = self.sessions.get(room)
            if not session:
                return
            del session['tokens']['user_id']
            if len(session['tokens']) == 0:
                session['id'].close()
                del self.sessions[room]

    @staticmethod
    def update_client_token_response(success, data=None):
        if not success:
            logger.error("Could not update client token:", data)
            sys.exit(3)
        logger.info("token sent to client")

    def send_token_to_client(self, room, user_id):
        if user_id == self.id:
            return

        session = self.sessions.get(room)
        if not session:
            return

        session['tokens']['user_id'] = session['id'].generate_token()

        sleep(1)
        self.emit("set_attribute", {"attribute": "value", "value": session['tokens']['user_id'].id, "id": "openvidu-token", 'receiver_id': user_id, 'room': room}, self.update_client_token_response)
        sleep(10)
        try:
            session['id'].start_recording(has_video=False)
        except OpenViduException as e:
            logger.error(e)


def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run audio pilot bot')

    urllib3.disable_warnings()
    logging.captureWarnings(True)

    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)
    ch.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(ch)

    # logging.getLogger('openvidu').setLevel(logging.DEBUG)
    # logging.getLogger('py.warnings').setLevel(logging.ERROR)

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

    if 'TASK_ID' in os.environ:
        task_id = {'default': os.environ['TASK_ID']}
    else:
        task_id = {'default': None}

    if 'OPENVIDU_URL' in os.environ:
        openvidu_url = {'default': os.environ['OPENVIDU_URL']}
    else:
        openvidu_url = {'required': True}

    if 'OPENVIDU_SECRET' in os.environ:
        openvidu_secret = {'default': os.environ['OPENVIDU_SECRET']}
    else:
        openvidu_secret = {'required': True}

    if 'OPENVIDU_VERIFY' in os.environ:
        openvidu_verify = {'default': os.environ['OPENVIDU_VERIFY']}
    else:
        openvidu_verify = {'default': True}

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
    parser.add_argument('--task-id',
                        type=int,
                        help='Task to join',
                        **task_id)
    parser.add_argument('--openvidu-url',
                        type=str,
                        help='URL for openvidu kms server',
                        **openvidu_url)
    parser.add_argument('--openvidu-secret',
                        type=str,
                        help='Secret for openvidu kms server',
                        **openvidu_secret)
    parser.add_argument('--openvidu-verify',
                        type=str2bool,
                        help='Verify certificate for openvidu server',
                        **openvidu_verify)
    args = parser.parse_args()

    TASK_ID = args.task_id
    OPENVIDU_URL = args.openvidu_url
    OPENVIDU_SECRET = args.openvidu_secret
    OPENVIDU_VERIFY = args.openvidu_verify

    URI = args.chat_host
    if args.chat_port:
        URI += f":{args.chat_port}"

    logger.info("running audio pilot bot on %s with token %s", URI, args.token)
    URI += "/api/v2"
    TOKEN = args.token

    # We pass token and name in request header
    socketIO = SocketIO(args.chat_host, args.chat_port,
                        headers={'Authorization': TOKEN, 'Name': 'Kamikaze'},
                        Namespace=ChatNamespace)
    socketIO.wait()
