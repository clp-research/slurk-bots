#!/bin/env python

import argparse
import sys
import os
import json
import time
import random
import string

from socketIO_client import SocketIO, BaseNamespace

chat_namespace = None
users = {}
self_id = None

images = 5
mistakes_allowed = 1

class Game:

    def __init__(self):
        self.images = False
        self.pointer = False
        self.mistakes = False
        self.image_mistakes = False
        self.curr_img = False
        self.started = False
        self.json_path = False
        self.img_path = "/static/test_items/"
        self.audio_path = "/static/test_items/"

    def get_json(self, dir):
        """
        generate random sample for testing
        """
        cwd = os.getcwd()+"/"
        file = "shapes-colors.json"
        self.json_path = os.path.join(cwd+dir,file)

        with open(self.json_path, "r")  as raw_jfile:
            jfile = json.load(raw_jfile)
            # number of images
            n = images
            self.images = {str(i):jfile[str(j)] for i,j in zip(range(n),random.choices(list(range(9)),k=n))}
            self.started, self.pointer = True, 0

    def get_image(self):
        """
        iterate through keys in current json file,
        if key corresponds to current state of self.pointer: set value as self.curr_img
        """
        for entry in self.images:
            if entry == str(self.pointer):
                self.curr_img = self.images[entry]
                return
        # if self.pointer exeeds the highest id
        self.curr_img = False

    def next_image(self):
        """
        increment value of self.pointer by 1,
        call get_image method to retrieve data for next image
        """
        self.pointer += 1
        self.image_mistakes = 0
        self.get_image()

    def click_on_target(self, click):
        """
        retrieve bounding box information from self.curr_img,
        check whether click is located within that bounding box
        """
        bb = self.curr_img["bb"]
        x,y,width,height = int(bb[0]),int(bb[1]),int(bb[2]),int(bb[3])

        if int(click['x']) in range(x, x+width+1) and int(click['y']) in range(y, y+height+1):
            return True
        else:
            return False

game = Game()

def add_user(room, id):
    global users
    room = int(room)
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
            # new image
            self.emit('set_attribute', {
            'room': room,
            'id': "current-image",
            'attribute': "src",
            'value': game.img_path+game.curr_img["image_filename"]
            })
            # new audio file
            self.emit('set_attribute', {
            'room': room,
            'id': "audio-description",
            'attribute': "src",
            'value': game.audio_path+game.curr_img['audio_filename']
            })

        else:
            # return message if no images are left
            time.sleep(1)
            game.started = False
            print ("mistakes: ",game.mistakes)
            if game.mistakes <= mistakes_allowed:
                self.emit("text", {"msg": "start_game", 'room': room})
            else:
                amt_token = generate_token(14)+"01"

                self.emit("set_text", {"id": "overlay-textbox", 'text': "Too many mistakes! Here's your token: {token}".format(token=amt_token), 'room': room})

                self.emit('set_attribute', {
                'room': room,
                'id': "current-image",
                'attribute': "src",
                'value': ""
                })

    def start_game(self,room):
        """
        prepare & start game:
        import json files, set first image, send audio files to client
        """
        # navigate to main slurk directory
        file_dir_path = os.path.dirname(os.path.realpath(__file__))
        slurk_path = os.path.abspath(os.path.join(file_dir_path, os.pardir))
        os.chdir(slurk_path)

        # check if game was already started
        if game.started == True:
            self.emit("text", {"msg": "Game already started!", 'room':room})
            return
        # assign initial values
        game.get_json("app/static/test_items/")
        if game.images == False:
            print ("no json files left in directory")
            return
        game.mistakes = 0;
        game.get_image()
        # mark file as used
        self.emit("text", {"msg": "Game started!", 'room': room})
        self.emit('log', {'type': 'message', 'msg': 'json file: ' + os.path.basename(game.json_path),'room': room})
        #set first image
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
            add_user(data['room']['id'], data['user']['id'])

    def on_new_task_room(self, data):
        print("hello!!! I have been triggered!")
        print("new task room:", data)
        if data['task']['name'] != 'meetup':
            return

        room = data['room']
        print("Joining room", room['name'])
        self.emit('join_task', {'room': room['id']})
        self.emit("command", {'room': room['id'], 'data': ['listen_to', 'skip_image']})

    def on_skip_image(self,data):
        """
        set next image
        """
        room = data['room']['id']
        game.next_image()
        self.set_image(room)

    def on_mouse_position(self, data):
        """
        on mouse click:
        check if client clicked on button
            if so: perform corresponding action
            if not: check if client clicked on target.
                if so: set new image,
                otherwise send feedback message
        """
        if data['type'] == 'click':
            room = data['user']['latest_room']['id']
            pos = data['coordinates']

            print("mouse click: ({x_pos}, {y_pos}), {user_name}, {element}".format(x_pos=pos['x'],y_pos=pos['y'],user_name=data['user']['name'],element=data['element']))

            # check whether client clicked on button
            if data['element'] == "#startButton":
                # start game
                self.start_game(room)
            elif not game.curr_img:
                # if image is clicked before game was started
                return
            elif data['element'] == "#overlayButton":
                # display target description and return
                self.emit("text", {"msg": "Please click on the {d_name}.".format(d_name=game.curr_img["refexp"]), 'room': room})
            elif data['element'] == "confirmReportButton":
                # skip image
                game.next_image()
                self.set_image(room)

            elif data['element'] in ['#replayButton', '#reportButton', '#fullscreenButton']:
                # do nothing
                pass

            # if no button was clicked: check if client clicked on target
            elif game.click_on_target(pos):
                self.emit("text", {"msg": "Correct!", 'room': room})
                time.sleep(0.3)
                game.next_image()
                self.set_image(room)
            # display message if click was off target
            else:
                self.emit("text", {"msg": "Try again!", 'room': room})
                game.mistakes += 1
                game.image_mistakes += 1
                # if user needs to many tries for current image
                if game.image_mistakes >= 5:
                    self.emit("text", {"msg": "Skipping Image", 'room': room})
                    game.next_image()
                    self.set_image(room)


class LoginNamespace(BaseNamespace):
    @staticmethod
    def on_login_status(data):
        global chat_namespace
        if data["success"]:
            chat_namespace = socketIO.define(ChatNamespace, '/chat')
        else:
            print("Could not login to server")
            sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example MultiBot')
    parser.add_argument('token',
                        help='token for logging in as bot ' +
                        '(see SERVURL/token)')
    parser.add_argument('-c', '--chat_host',
                        help='full URL (protocol, hostname; ' +
                        'ending with /) of chat server',
                        default='http://localhost')
    parser.add_argument('-p', '--chat_port', type=int,
                        help='port of chat server', default=5000)
    args = parser.parse_args()

    with SocketIO(args.chat_host, args.chat_port) as socketIO:
        login_namespace = socketIO.define(LoginNamespace, '/login')
        login_namespace.emit('connectWithToken', {'token': args.token, 'name': "ImageClick_Pretest"})
        socketIO.wait()
