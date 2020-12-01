#!/bin/env python

import argparse
import json
import os
import random
import string
import sys
import time
import logging

from PIL import Image
from socketIO_client import SocketIO, BaseNamespace
from collections import defaultdict

chat_namespace = None
users = {}
self_id = None

class Game:

    def __init__(self):
        self.images = defaultdict(dict)
        self.pointer = False
        self.curr_img = False
        self.started = False
        self.json_path = False
        self.img_path = "/usr/src/image_click_bot/image_serve/"
        self.audio_path = "/usr/src/image_click_bot/static/audio/"
        self.valid_images = [".jpg", ".png", ".tga"]

        # Load all available images
        for i in os.listdir(self.img_path):
            img_id = os.path.splitext(i)[0]
            ext = os.path.splitext(i)[1]
            if ext.lower() not in self.valid_images:
                continue
            self.images[img_id]["img_data"] = Image.open(os.path.join(self.img_path, i))
            self.images[img_id]["is_used"] = False
            self.images[img_id]["filename"] = img_id + ext

    def get_image(self):
        """
        iterate through images in dictionary,
        if key corresponds to unused images: set value as self.curr_img
        """
        for entry in self.images.keys():
            print(entry)
            if not self.images[entry]["is_used"]:
                self.curr_img = self.images[entry]
                return
        self.curr_img = False

    def next_image(self):
        """
        call get_image method to retrieve data for next image
        """
        # FIXME: does pointer need to be increased?
        # self.pointer += 1
        self.get_image()

    def click_on_target(self, click):
        """
        retrieve bounding box information from self.curr_img,
        check whether click is located within that bounding box
        """
        img = self.curr_img["img_data"]
        # Take 10% left bottom corner of the image as bounding boxes
        img_width, img_height = img.size
        x, y, width, height = 0, 0, 0.1 * img_width, 0.1 * img_height # for testing

        if int(click['x']) in range(x, x+width+1) and int(click['y']) in range(y, y+height+1):
            return True
        else:
            return False

game = Game()

def add_user(room, id):
    global users
    id = int(id)
    print("adding user", id, "to room", room)
    if room == 1:
        return
    if room not in users:
        users[room] = []
    users[room].append(id)

def generate_token(len):
    return (''.join(random.choices(string.ascii_letters + string.digits, k=len)))

class ChatNamespace(BaseNamespace):

    def set_image(self,room):
        """
        emit new_image command if there are images left
        """
        if game.curr_img:
            game.started = True
            # new image
            self.emit('set_attribute', {
            'room': room,
            'id': "current-image",
            'attribute': "src",
            'value': "http://localhost:3000/" + game.curr_img["filename"]
            })
            # new audio file
            # self.emit('set_attribute', {
            # 'room': room,
            # 'id': "audio-description",
            # 'attribute': "src",
            # 'value': game.audio_path+game.curr_img['audio_filename']
            # })
            game.curr_img["is_used"] = True
        else:
            # return message if no images are left
            self.emit("text", {"msg": "No images left", 'room': room})
            game.started = False

            amt_token = generate_token(14)+"02"
            self.emit("set_text", {"id": "overlay-textbox", 'text': "Good job! Here's your token: {token}".format(token=amt_token), 'room': room})

            self.emit('set_attribute', {
            'room': room,
            'id': "current-image",
            'attribute': "src",
            'value': ""
            })

    def start_game(self,room):
        """
        prepare & start game:
        set first images
        """
        # navigate to main slurk directory
        file_dir_path = os.path.dirname(os.path.realpath(__file__))
        slurk_path = os.path.abspath(os.path.join(file_dir_path, os.pardir))
        os.chdir(slurk_path)

        # check if game was already started
        if game.started is True:
            self.emit("text", {"msg": "Game already started!", 'room':room})
            return
        # assign initial values
        # game.get_json("app/static/json/")
        if game.images is False:
            print("no json files left in directory")
            return
        game.get_image()
        # FIXME is this needed?
        # mark file as used
        # with open(game.json_path, 'w') as outfile:
            # mark json file as used
            #game.images["used"] = True
            # json.dump(game.images, outfile, sort_keys=True, indent=1)
        self.emit("text", {"msg": "Game started!", 'room': room})
        # FIXME: is anything logged?
        # self.emit('log', {'type': 'message', 'msg': 'json file: ' + os.path.basename(game.json_path),'room': room})
        # set first image
        self.set_image(room)

    @staticmethod
    def on_joined_room(data):
        global users, self_id

        self_id = data['self']['id']

        for user in data['users']:
            if user['id'] != self_id:
                add_user(data['room']['id'], user['id'])

    @staticmethod
    def on_status(data):
        global users
        print("status:", data)

        if data['user']['id'] != self_id:
            add_user(data['room'], data['user']['id'])

    def on_new_task_room(self, data):
        print("hello!!! I have been triggered!")
        print("new task room:", data)
        # FIXME: this looks like task-specific code: move to own file or branch
        # if data['task']['name'] != 'meetup':
        #     return

        if data['task'] == TASK_ID:
            room = data['room']
            print("Joining room")
            self.emit('join_room', {'room': room})
        # FIXME: what is this for?
        # self.emit("command", {'room': room['id'], 'data': ['listen_to', 'skip_image']})

    def on_text_message(self, data):
        # FIXME: why is this commented?
        # prevent parroting own messages
        # if data["user"]["name"] == "ImageClick_Pretest":
        #     message = data['msg']
        #     room = data["user"]["latest_room"]["id"]
        #     if message == 'start_game':
        #         self.start_game(room)
        message = data['msg']
        room = data['room']
        if message == 'start_game':
            self.start_game(room)
        elif message == 'skip_image':
            game.next_image()
            self.set_image(room)

    def on_skip_image(self, data):
        """
        set next image
        """
        room = data['room']
        game.next_image()
        self.set_image(room)

    def on_mouse_position(self, data):
        """
        on mouse click:
        ** log all kinds of clicks**
        check if client clicked on button
            if so: perform corresponding action
            if not: check if client clicked on target.
                if so: set new image,
                otherwise send feedback message
        """
        if data['type'] == 'click':
            room = data['room']
            pos = data['coordinates']

            print("mouse click: ({x_pos}, {y_pos}), {user_name}, {element}".format(x_pos=pos['x'],y_pos=pos['y'],user_name=data['user']['name'],element=data['element']))

            # check whether client clicked on button
            if data['element'] == "#startButton":
                # start game
                #self.start_game(room)
                pass
            elif not game.curr_img:
                # if image is clicked before game was started
                return
            elif data['element'] == "#overlayButton":
                # display target description and return
                # self.emit("text", {"msg": "Please click on the {d_name}.".format(d_name=game.curr_img["refexp"]), 'room': room})
                pass
            elif data['element'] == "confirmReportButton":
                # skip image
                game.next_image()
                self.set_image(room)
            elif data['element'] in ["#replayButton","#reportButton","#fullscreenButton"]:
                return
            # if no button was clicked: check if client clicked on target
            elif game.click_on_target(pos):
                self.emit("text", {"msg": "Correct!", 'room': room})
                time.sleep(0.3)
                game.next_image()
                self.set_image(room)
            # display message if click was off target
            else:
                self.emit("text", {"msg": "Try again!", 'room': room})

# class LoginNamespace(BaseNamespace):
#     @staticmethod
#     def on_login_status(data):
#         global chat_namespace
#         if data["success"]:
#             chat_namespace = socketIO.define(ChatNamespace, '/chat')
#         else:
#             print("Could not login to server")
#             sys.exit(1)


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description='Example MultiBot')
    # parser.add_argument('token',
    #                     help='token for logging in as bot ' +
    #                     '(see SERVURL/token)')
    # parser.add_argument('-c', '--chat_host',
    #                     help='full URL (protocol, hostname; ' +
    #                     'ending with /) of chat server',
    #                     default='http://localhost')
    # parser.add_argument('-p', '--chat_port', type=int,
    #                     help='port of chat server', default=5000)
    # args = parser.parse_args()

    # with SocketIO(args.chat_host, args.chat_port) as socketIO:
    #     login_namespace = socketIO.define(LoginNamespace, '/login')
    #     login_namespace.emit('connectWithToken', {'token': args.token, 'name': "ImageClick_Main"})
    #     socketIO.wait()
    parser = argparse.ArgumentParser(description='Run ImageClick Bot')

    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG)

    # define handler to write INFO message
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # add handler to the root logger
    logging.getLogger('ImageClickBot').addHandler(console)

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

    if 'IMAGECLICK_TASK_ID' in os.environ:
        task_id = {'default':os.environ['IMAGECLICK_TASK_ID']}
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

    logging.info("running imageclick bot on %s with token %s", uri, args.token)
    sys.stdout.flush()
    uri += "/api/v2"
    token = args.token

    # We pass token and name in request header
    socketIO = SocketIO(args.chat_host, args.chat_port,
                        headers={'Authorization': args.token, 'Name': 'ImageClick_Main'},
                        Namespace=ChatNamespace)
    socketIO.wait()
