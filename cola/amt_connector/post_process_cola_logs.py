"""
# In this file, logs for each mturk session are processed
# In CoLA, the logs contains as well as images / text data
# which changes depending on the task i.e. game played.
"""


#import packages
import os
import json
import requests
import configparser
import sys


#from PIL import Image
#from PIL import ImageFont, ImageDraw

# the font style for dispplaying category names
#FONT = ImageFont.truetype("/Library/Fonts/Arial.ttf", 15)

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')

# def get_players(data):
#     """get player information - id and names"""
#     players = defaultdict(dict)
#     for log in data:
#         # players have joined a cola room
#         if log['type'] == 'join':
#             user_name = log['user']['name']
#             print(user_name)
#             user_id = log['user']['id']
#             if user_name != 'ColaBot':
#                 players[user_id] = f'{user_name}'
#     return players.keys(), players.values()

# def each_room_data(sess_directory, data_directory, filename):
#     """function to process data of each cola room"""

#     # size of image grid to save all the image in one task
#     # in one block
#     size_im_x = 500
#     size_im_y = 500

#     # read file and get players info #
#     file_path = os.path.join(sess_directory, filename)
#     with open(file_path) as fn:
#         input_log = json.load(fn)

#         # process data in each cola room
#         counter = 0  # to separate image data inside one room
#         row_space = 25 # space between each row of images in a grid
#         for chat in input_log:
#             if chat['type'] == 'command':
#                 if chat["command"] == 'show_image':
#                     counter += 1
#                     # check the type of data - string or list of images
#                     image_data_type = type(chat['data'][0][1])
#                     data_path = os.path.join(data_directory, filename.split('.')[0]+ '_' + str(counter))

#                     # if string, then text comprehension data
#                     # else list would be images
#                     if image_data_type == str:

#                         # writing the text comprehension in a text file #
#                         text_comp_file = open(data_path, 'w+')
#                         for line in chat['data'][0]:
#                             text_comp_file.write('%s\r\n' % line)
#                     else:
#                         # save images of each category as a grid
#                         new_grid = Image.new('RGB', (size_im_x, size_im_y))
#                         for len_x in range(len(chat['data'][0])):
#                             # name of each category, this is not the real name atm
#                             cat_name = chat['data'][0][len_x][0]

#                             for len_y in range(len(chat['data'][0][len_x][1:])):
#                                 # len_y+1 because 0 is category name
#                                 each_im_url = chat['data'][0][len_x][len_y+1]

#                                 # open image from the URL
#                                 response = requests.get(each_im_url)
#                                 print(each_im_url)
#                                 im = Image.open(BytesIO(response.content))
#                                 im.thumbnail((100, 100))
#                                 new_grid.paste(im, (len_y*100, len_x*100+row_space))

#                             # write text over the image
#                             draw_grid = ImageDraw.Draw(new_grid)
#                             draw_grid.text((0, len_x*100), cat_name, (255, 255, 255), font=FONT)

#                         im_path = os.path.join(data_path + '.png')
#                         new_grid.save(im_path)

def each_room_dialogue(room):
    """function to process dialogues in each cola room"""
    token = CONFIG['logs']['admin_token']
    uri = CONFIG['logs']['url']
    SESSION = CONFIG['session']['name']

    room_name = room["name"]
    print(room_name)

    logs = requests.get(f"{uri}/room/{room_name}/logs", headers={'Authorization': f"Token {token}"})
    if not logs.ok:
        print("Could not get logs")
        sys.exit(4)
        
    out_path_processed = os.path.join("processed_logs", SESSION)
    file_path_processed = os.path.join(out_path_processed, room_name + ".log")

    # dump unprocessed logs
    if not os.path.isdir('./logs/' + SESSION):
        os.mkdir('./logs/' + SESSION)

    with open('./logs/' + SESSION + '/'+ room_name +'.json', 'w') as outfile:
        json.dump(logs.json(), outfile)

    if not os.path.isdir(out_path_processed):
        os.mkdir(out_path_processed)
    #write processed logs
    with open(file_path_processed, 'w+') as room_fn:
        # open new file for each game, write the complete dialogue in a game to a file #

        # go over each type of chat - process text and commands
        # and write them to a file.
        for log_entry in logs.json():
            if log_entry['event'] == "text_message":
                chat_str = log_entry['user']['name'] + '-text: ' + log_entry['message']
                room_fn.write('%s\r\n' %chat_str)
            elif log_entry['event'] == 'command':
                if log_entry["command"].startswith('answer'):
                    data_str = "".join(log_entry["data"]["command"].split("answer")[1:]).strip()
                    chat_str = log_entry['user']['name']+'-answer: '+ data_str
                    room_fn.write('%s\r\n' % chat_str)
                elif log_entry["command"] == 'agree':
                    data_str = ' '.join(log_entry['data'])
                    chat_str = log_entry['user']['name'] + '-agree: ' + data_str
                    room_fn.write('%s\r\n' % chat_str)
                elif log_entry['command'] == 'ready':
                    chat_str = log_entry['user']['name'] + '-ready: '
                    room_fn.write('%s\r\n' % chat_str)
            elif log_entry['event'] == 'join':
                chat_str = log_entry['user']['name'] + '-join: '
                room_fn.write('%s\r\n' % chat_str)
            elif log_entry['event'] == 'leave':
                chat_str = log_entry['user']['name'] + '-leave: '
                room_fn.write('%s\r\n' % chat_str)
            elif log_entry['event'] == 'set_attribute':
                chat_str = log_entry['user']['name'] + '-show_image: ' + log_entry['value']
                room_fn.write('%s\r\n' % chat_str)
            elif log_entry['event'] == 'set_text':
                chat_str = log_entry['user']['name'] + '-set_text: ' + log_entry['text']
                room_fn.write('%s\r\n' % chat_str)
            else:
                print(log_entry)

# def process_logs_per_session(sess_dir, processed_sess_dir, proc_type):
#     """process all logs in one mturk session"""

#     # directory to save all dialogues
#     out_path = os.path.join(processed_sess_dir, proc_type)
#     if not os.path.exists(out_path):
#         os.makedirs(out_path)

#     # go over each cola room log #
#     for filename in os.listdir(sess_dir):
#         # only game room processing
#         if filename.endswith('log') and 'Waiting' not in filename:
#             # process data or dialogues
#             if proc_type == 'dialogues':
#                 each_room_dialogue(sess_dir, out_path, filename)
#             else:
#                 each_room_data(sess_dir, out_path, filename)

def process_logs():
    """process all logs"""
    token = CONFIG['logs']['admin_token']
    uri = CONFIG['logs']['url']
    session = CONFIG['session']['name']

    # directory to save all dialogues
    out_path = os.path.join("processed_logs", session)
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    out_path_unprocessed = os.path.join("logs", session)
    if not os.path.exists(out_path_unprocessed):
        os.makedirs(out_path_unprocessed)

    rooms = requests.get(f"{uri}/rooms", headers={'Authorization': f"Token {token}"})
    if not rooms.ok:
        print("Could not get rooms")
        sys.exit(3)

    # go over each cola room log #
    for room in rooms.json():
        # only game room processing
        print("Processing room " + room["name"])
        if room["label"] == 'cola':
            # process data or dialogues
            #if proc_type == 'dialogues':
            each_room_dialogue(room)
            #else:
            #    each_room_data(out_path, room)

if __name__ == '__main__':
    # process data for each mturk session
    # dialogues
    process_logs()
