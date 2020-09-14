"""
This is CoLA Bot code that uses slurk interface.
 CoLA bot handles the dialogue between two players
 who need to collaborate togther to solve a task.
 In each game room, we show the players - images, text
 information, logical rules. They need to discuss together
 and reach an agreement.
 So, the two important commands here are:
 /answer: provide a description / reasoning
 /agree: If you agree with other player's answer.
 """

# import packages
import configparser
import os
import json
import random
import sys
import string
import argparse
from threading import Timer
import requests

from time import sleep

from socketIO_client import SocketIO, BaseNamespace

from game_db import ColaGameDb

# Global variables

TASK_ID = None

# --- class implementation --------------------------------------------------------
# ChatNamespace
# ---------------------------------------------------------------------------------
class ChatNamespace(BaseNamespace):
    """ Moderates dialogues between players and handles the commands in the game"""

    # Called when connected
    def __init__(self, io, path):
        super().__init__(io, path)
        self.WAITING_TIMER = Timer(1, print, args=["Timer"])
        self.id = None
        self.COLA_GAME_DB = []
        self.emit('ready')

    def on_text_message(self, data):
        if data['user']['name'] != 'Cola Bot':
            for each_room_db in self.COLA_GAME_DB:
                if data['room'] == each_room_db.room:
                    if data['msg'] == "ready":
                        self._command_ready(data)
                    elif data["msg"].startswith("answer"):
                        data["command"] = data["msg"]
                        self._command_answer(data)
                    elif data["msg"] == "agree":
                        self._command_agree(data)
                    elif data["msg"] == "noreply" or data["msg"] == "no reply":
                        self._command_noreply(data)
                    each_room_db.count_msg += 1

    def on_new_task_room(self, data):
        """
        This gets called as soon as new task (cola) room is created.
        :param
        data: A dict. Information about the new room.
        """
        #global COLA_GAME_DB
        print("new task room: ", data)
        # As a new room opens, an instance of cola game class is created
        cola_db = ColaGameDb(data['room'])

        # add both players information
        for user in data['users']:
            cola_db.add_users(user)

        # Generate the data for each game instance
        print("generate data every time cola is called")
        cola_db.generate_cola_data()

        self.WAITING_TIMER.cancel()

        cola_db.ready_timer = Timer(60*1, self.emit, args=['text',
                                                           {
                                                               'msg': "Are you ready? Please type **/ready** to begin the game.",
                                                               'room': cola_db.room,
                                                               'html': True
                                                           }
                                                          ])
        cola_db.ready_timer.start()

        # Keeping information ofall the rooms i.e. each instance of COLA_GAME_DB class
        self.COLA_GAME_DB.append(cola_db)
        self.emit("join_room", {'user': self.id, 'room': data['room']}) # join cola
        sys.stdout.flush()

# --- public functions -----------------------------------------------------------------
    def on_joined_room(self, data):
        """ This is called once, when the bot joins a room.

        :param
            data: A dict. All information about the new room.
        """
        self.id = data['user']
        #global COLA_GAME_DB

        # Search for the correct database (accoording to the actual room)
        for cola_db in self.COLA_GAME_DB:
            if data['room'] == cola_db.room:
                cola_db.add_users(data['user'])

                print("on_joined_room", data)
                sys.stdout.flush()
                # Send a welcome message to both users (via the room-id).
                if data['room'] != "waiting_room":

                    # Welcome message for the cola room #
                    sleep(.5)
                    self.emit('text', {'msg': ' **Welcome to the CoLa Game!**'
                                              ' Discussion and providing reason(s)'
                                              ' for your answer is crucial for this game.',
                                       'room': data['room'],
                                       'html': True})
                    sleep(.5)
                    self.emit('text', {'msg': ' Remember the following commands to play the game:'
                                              ' \n\n(1) Propose answer to your partner: Type "/answer'
                                              ' ...your description here...".'
                                              ' \n\n(2) Agree on the answer proposed by your partner:'
                                              ' Type "/agree".\n\n',
                                       'room': data['room'],
                                       'html': True})
                    sleep(.5)
                    self.emit('text', {'msg': ' Please type **/ready** to begin the game.',
                                       'room': data['room'],
                                       'html': True})
                    sleep(.5)
                    self.emit('set_text',{'room': data['room'],
                                          'id': "status-box",
                                          'text': 'Please type /ready to begin the game.'})

    def on_command(self, data):
        print("on_command", data)
        sys.stdout.flush()
        if data["command"].startswith("ready"):
            self._command_ready(data)
        elif data["command"].startswith("answer"):
            self._command_answer(data)
        elif data["command"].startswith("agree"):
            self._command_agree(data)
        elif data["command"].startswith("noreply"):
            self._command_noreply(data)
        #elif data["command"].startswith("change"):
        #    self._command_change(data)
        else:
            for each_room_db in self.COLA_GAME_DB:
                if data['room'] == each_room_db.room:
                    all_players = each_room_db.players
                    self_id = [all_players[i]['id'] for i in range(0, len(all_players))
                               if data['user']['id'] == all_players[i]['id']]
                    self.emit('text',
                              {
                                  'msg': '{} is not a valid command. '.format(data["command"]),
                                  'receiver_id': self_id,
                                  'room': data['room']
                              })
    
    def _command_ready(self, data):
        """ Test slash command skills of the players """
        print("_command_ready", data)
        sys.stdout.flush()
        for each_room_db in self.COLA_GAME_DB:
            if data['room'] == each_room_db.room:
                self_id = [player['id'] for player in each_room_db.players
                           if player['id'] == data['user']['id']]
                other_user = [player['id'] for player in each_room_db.players
                                  if player['id'] != data['user']['id']]
                if not each_room_db.ready_id:
                    each_room_db.ready_id.add(self_id[0])
                    self.emit('text', {
                        'msg': 'Now, waiting for your partner to type /ready. ',
                        'receiver_id': self_id[0],
                        'room': each_room_db.room
                        })
                    each_room_db.ready_timer.cancel()
                    each_room_db.ready_timer = Timer(60*.5,
                                                     self.emit,
                                                     args=['text', {
                                                                        'msg': "Your partner is ready. Please, also type /ready!",
                                                                        'room': each_room_db.room,
                                                                        'receiver_id': other_user
                                                                    }
                                                     ]
                                                    )
                    each_room_db.ready_timer.start()

                elif self_id[0] not in each_room_db.ready_id and len(each_room_db.ready_id) == 1:
                    # game starts #
                    self.emit('text', {
                        'msg': 'Woo-Hoo! Game begins now. ',
                        'room': each_room_db.room})
                    each_room_db.ready_id.add(self_id[0])
                    each_room_db.ready_flag = True
                    each_room_db.first_answer = False
                    self.on_show_and_query(each_room_db)

                    each_room_db.ready_timer.cancel()
                    
                    # conversation timer starts
                    each_room_db.conversation_timer = Timer(60*5,
                                                            self.emit,
                                                            args=['text',
                                                                  {
                                                                      'msg': 'You both seem to be having a discussion for a '
                                                                             'long time. Could you reach an agreement and '
                                                                             'provide an answer?',
                                                                      'room': each_room_db.room
                                                                  }
                                                              ]
                                                    )
                    each_room_db.conversation_timer.start()

                elif self_id[0] in each_room_db.ready_id:
                    self.emit('text', {
                        'msg': 'You have already typed /ready. ',
                        'receiver_id': self_id[0],
                        'room': each_room_db.room})

    def on_show_and_query(self, game_room_db):
        """
        Start the game by showing the images and asking questions
        :param data: current room database dict
        :return:
        """

        # start the game and update the current state of game
        # pop-out the current question from room data
        curr_data = game_room_db.room_data.pop(0)
        game_room_db.current_state = curr_data

        print(curr_data)
        sys.stdout.flush()
        self.emit('set_attribute',
                  {
                      'room': game_room_db.room,
                      'id': "current-image",
                      'attribute': "src",
                      'value': curr_data['data']
                  })
        self.emit('set_text',
                  {
                      'room': game_room_db.room,
                      'id': "status-box",
                      'text': curr_data['question']
                  })

    def _command_answer(self, data):
        """
        Providing your own (individual player's) answer / reason
        :param data: dict of user data
        :return:
        """

        for each_room_db in self.COLA_GAME_DB:
            if data['room'] == each_room_db.room:
                all_players = each_room_db.players
                self_id = [all_players[i]['id'] for i in range(0, len(all_players))
                           if data['user']['id'] == all_players[i]['id']]
                if not each_room_db.first_answer and each_room_db.count_msg < 5:
                    self.emit('text',
                              {
                                  'msg': 'There is no discussion so far. You should discuss first, then suggest and update'
                                         ' your answers.',
                                  'receiver_id': self_id[0],
                                  'room': each_room_db.room
                              })
                elif not each_room_db.ready_flag:
                    self.emit('text',
                              {
                                  'msg': 'Both players have not typed /ready yet. ',
                                  'receiver_id': self_id[0],
                                  'room': each_room_db.room
                              })
                elif not each_room_db.game_over_status:
                    sent_id = [all_players[i]['id'] for i in range(0, len(all_players))
                               if data['user']['id'] != all_players[i]['id']]
                    self_name = [all_players[i]['name'] for i in range(0, len(all_players))
                                 if data['user']['id'] == all_players[i]['id']]
                    self_id = [all_players[i]['id'] for i in range(0, len(all_players))
                               if data['user']['id'] == all_players[i]['id']]

                    proposal = " ".join(data['command'].split("answer ")[1:]).strip()
                    if proposal:
                        each_room_db.answer_status = True

                        self.emit('text', {'msg': 'The current proposal from '
                                                  '{} is **"{}"** '.format(self_name[0]
                                                                                , proposal),
                                           'room': each_room_db.room,
                                           'html': True})
                        each_room_db.curr_player_ans_id = self_id[0]

                        self.emit('text', {'msg': 'Do you agree with your partner\'s answer?'
                                                  ' If not, please continue the discussion.',
                                           'receiver_id': sent_id[0],
                                           'room': each_room_db.room})

                    else:
                        self.emit('text', {
                            'msg': 'This command cannot be processed.\n\n Answer comes with a'
                                   ' description, for example, /answer This is a... because '
                                   '...your description here...',
                            'receiver_id': self_id[0],
                            'room': each_room_db.room,
                            'html': True})
                else:
                    self.emit('text', {
                        'msg': 'Cannot process this command. The game is already finished.'
                               ' ',
                        'room': each_room_db.room})

    def _command_agree(self, data):
        """
        Function where one player can agree to another player's answer
        new query automatically begins or the game ends.
        :param data:
        :return:
        """
        #global COLA_GAME_DB

        for each_room_db in self.COLA_GAME_DB:
            if data['room'] == each_room_db.room:
                # ID of the user #
                all_players = each_room_db.players
                self_id = [all_players[i]['id'] for i in range(0, len(all_players))
                           if data['user']['id'] == all_players[i]['id']]

                if not each_room_db.ready_flag:
                    self.emit('text', {
                        'msg': 'Both players have not typed /ready yet. ',
                        'receiver_id': self_id[0],
                        'room': each_room_db.room})
                
                elif each_room_db.room_data:
                    if each_room_db.answer_status:
                        if self_id[0] == each_room_db.curr_player_ans_id:
                            self.emit('text', {
                                'msg': 'You cannot agree to your own answer. ',
                                'receiver_id': self_id[0],
                                'room': each_room_db.room})
                            return

                        # if the game list is non-empty, the game continues.
                        self.emit('text', {
                            'msg': 'Bravo! You have now moved to the next round. ',
                            'room': each_room_db.room})

                        # timer cancels
                        each_room_db.conversation_timer.cancel()

                        self.on_show_and_query(each_room_db)

                        each_room_db.answer_status = False
                        each_room_db.count_msg = 0
                    else:
                        self.emit('text',
                                  {'msg': 'This command cannot be processed. You have not'
                                          ' started discussion with your partner. You have to '
                                          'propose answers to each other and reach an agreement.',
                                    'receiver_id': self_id[0],
                                    'room': each_room_db.room})
                else:
                    # as soon as the list is empty, game end #
                    if each_room_db.game_over_status is False and\
                            each_room_db.answer_status is False:
                        self.emit('text',
                                  {'msg': 'This command cannot be processed. You have not '
                                             'started discussion with your partner. You have to '
                                             'propose answers to each other and reach an agreement.'
                                             ' ',
                                    'receiver_id': self_id[0],
                                    'room': each_room_db.room})
                    elif each_room_db.game_over_status is False and\
                            each_room_db.answer_status is True:
                        if self_id[0] == each_room_db.curr_player_ans_id:
                            self.emit('text', {
                                'msg': 'You cannot agree to your own answer. ',
                                'receiver_id': self_id[0],
                                'room': each_room_db.room})
                            return
                        self.game_over(each_room_db.room)
                        each_room_db.game_over_status = True
                    elif each_room_db.game_over_status is True:
                        self.emit('text', {
                            'msg': 'Cannot process this command. The game is already finished.'
                                   ' ',
                            'room': each_room_db.room})
                    else:
                        print("Something is wrong!!!")
                    # self.game_over(data)

    # message to end the game #
    def game_over(self, room):
        """ Called when game gets over and token is genrated for """
        #global COLA_GAME_DB

        self.emit('text', {'msg': 'Please enter the following token into' \
                                  ' the field on the HIT webpage, and close this' \
                                  ' browser window. ', 'room': room})
        amt_token = self.confirmation_code(room)
        self.emit('text', {'msg': 'Here\'s your token: {}'.format(f'{amt_token}'),
                           'room': room})
        self.close_game(room)

    # message to end the game #
    def no_partner(self, room):
        """ Called when game gets over and token is genrated for """
        #global COLA_GAME_DB

        self.emit('text', {'msg': 'Unfortunately we could not find a partner for you!', 'room': room})
        self.emit('text', {'msg': 'Please enter the following token into' \
                                  ' the field on the HIT webpage, and close this' \
                                  ' browser window. ', 'room': room})
        amt_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        status_txt = 'no_partner'
        self.emit('log', {'room': room, 'type': "confirmation_log", 'amt_token':amt_token, 'status_txt':status_txt})
        self.emit('text', {'msg': 'Here\'s your token: {}'.format(f'{amt_token}'),
                           'room': room})
        self.close_game(room)

    def confirmation_code(self, room):
        """ Generate AMT token that will be sent to each player """
        amt_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        status_txt = 'success'

        #token_log = random.choices(string.ascii_uppercase + string.digits, k=6)
        self.emit('log', {'room': room, 'type': "confirmation_log", 'amt_token':amt_token, 'status_txt':status_txt})

        return amt_token

    def _command_noreply(self, data):
        """ If the partner does not reply """
        #global COLA_GAME_DB

        for each_room_db in self.COLA_GAME_DB:
            if data['room'] == each_room_db.room:
                room = each_room_db.room
                # ID of the user #
                all_players = each_room_db.players
                self_id = [player['id'] for player in all_players
                           if data['user']['id'] == player['id']]
                other_id = [player['id'] for player in all_players
                            if player['id'] != data['user']['id']]

                # generate AMT token that will be sent to each player
                amt_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                status_txt = 'no_reply'
                self.emit('log', {'room': room, 'type': "confirmation_log", 'amt_token':amt_token, 'status_txt':status_txt})
                self.emit('text', {'msg': 'Here\'s your token: {}'.format(f'{amt_token}'),
                                   'room': room,
                                   'receiver_id': self_id[0]})

                self.emit('text', {'msg': 'Your partner closed the game, because you were not responding for a while.',
                                   'room': room,
                                   'receiver_id': other_id[0]})
                
                self.close_game(room)

    def close_game(self, room):
        self.emit('text', {'msg': 'The game is over! Thank you for your participation!',
                                   'room': room})
        self.emit('set_attribute', {
                      'room': room,
                      'id': "type-area",
                      'attribute': "style",
                      'value': 'visibility:hidden'
                  })
        if room != "waiting_room":
            response = requests.put(f"{uri}/room/{room}",
                                headers={'Authorization': f"Token {token}"},
                                json=dict(read_only=True)
                                )
            print(response)
            sys.stdout.flush()
            
            for each_room_db in self.COLA_GAME_DB:
                each_room_db.game_closed = True
                if room == each_room_db.room:
                    if each_room_db.ready_timer:
                        each_room_db.ready_timer.cancel()
                    if each_room_db.conversation_timer:
                        each_room_db.conversation_timer.cancel()
                    if each_room_db.answer_timer:
                        each_room_db.answer_timer.cancel()
                    if each_room_db.join_timer:
                        each_room_db.join_timer.cancel()

                    # all_players = each_room_db.players
                    # for player in all_players:
                    #     print(player)
                    #     sys.stdout.flush()
                        
                    #     self.emit("leave_room", {'user': player["id"], 'room': room})
                    #     user_id = player["id"]
                    #     response = requests.get(f"{uri}/user/{user_id}",
                    #                             headers={'Authorization': f"Token {token}"})
                    #     print(response.text)
                    #     sys.stdout.flush()
                    #     user_token = response.json()["token"]
                    #     response = requests.delete(f"{uri}/token/{user_token}",
                    #                             headers={'Authorization': f"Token {token}"})
                    #     print(response)
                    #     sys.stdout.flush()
                        
                

    def on_status(self, data):
        """  determine join/leave/rejoin status and display corresponding messages  """

        #global COLA_GAME_DB
        print("status:", data)
        sys.stdout.flush()

        # If this function is called because a player joins the room ...
        # Occurs when the player re-joins the room
        if data['type'] == "join":
            if data['room'] == "waiting_room":
                if not self.WAITING_TIMER.is_alive():
                    self.WAITING_TIMER = Timer(5*60,
                                            self.no_partner,
                                            args=[data['room']]
                                            )
                    self.WAITING_TIMER.start()
            else:
                # ... find the correct database.
                for each_room_db in self.COLA_GAME_DB:
                    if each_room_db.room == data['room']:
                        # update the display for the rejoined user.
                        curr_data = each_room_db.current_state
                        if curr_data is not None:
                            rejoin_timer = Timer(3*1, self.emit, args=['set_attribute',
                                                            {
                                                                    'room':data['room'],
                                                                    'id': "current-image",
                                                                    'attribute': "src",
                                                                    'value': curr_data['data'],
                                                                    'receiver_id': data['user']['id']
                                                                }
                                                        ])
                            rejoin_timer.start()

                            rejoin_timer2 = Timer(3*1, self.emit, args=['set_text',
                                                                        {
                                                                            'room': data['room'],
                                                                            'id': "status-box",
                                                                            'text': curr_data['question'],
                                                                            'receiver_id': data['user']['id']
                                                                        }
                                                        ])
                            rejoin_timer2.start()

                        other_user = [player for player in each_room_db.players
                                    if player['id'] != data['user']['id']]
                        user_name = data['user']['name']
                        # Send a message to the other user, that the current user has
                        # rejoined the chat.
                        self.emit('text',
                                {
                                    'msg': f'{user_name} has rejoined the game.',
                                    'room': each_room_db.room,
                                    'receiver_id': other_user[0]['id']
                                })

        # If this function is called because a player left the room ...
        if data['type'] == "leave":
            for each_room_db in self.COLA_GAME_DB:
                    # ... find the correct database.
                    if each_room_db.room == data['room']:
    #                    if data['user']['token']['task'] is not None:
                        other_user = [player for player in each_room_db.players if
                                    player['id'] != data['user']['id']]
                        user_name = data['user']['name']
                        # Send a message to the other user, that the current user has left the chat.
                        self.emit('text', {'msg': f'{user_name} has left the game. Please wait a '
                                                f'bit, your partner may rejoin.',
                                        'room': each_room_db.room,
                                        'receiver_id': other_user[0]['id']})

if __name__ == '__main__':
    print("bot started")
    parser = argparse.ArgumentParser(description='Cola Bot')

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

    if 'COLA_TASK_ID' in os.environ:
        task_id = {'default': os.environ['COLA_TASK_ID']}
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

    print("running cola bot on", uri, "with token", args.token)
    sys.stdout.flush()
    uri += "/api/v2"
    token = args.token

    # We pass token and name in request header
    socketIO = SocketIO(args.chat_host, args.chat_port,
                        headers={'Authorization': args.token, 'Name': 'Cola Bot'},
                        Namespace=ChatNamespace)
    socketIO.wait()
