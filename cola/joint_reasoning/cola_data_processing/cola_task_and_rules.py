"""
Process CoLA game room data and return
game data.
This script is called when new task room
is created.
"""
import configparser
import os
import random
import string

# Read the config file #
CONFIG = configparser.ConfigParser()
# change the path for config file
CONFIG.read('/usr/src/cola/cola_data_processing/cola_config.ini')

def process_whichpattern(input_dict, n_ques, room):
    SYN_ROOM_DICT = []
    laws = ['more_red_than_black', 'upper_left_red', 'diagonal_red']
    rands = random.sample(laws, n_ques)
    for law in rands:
        instances = str(4)
        ques = 'Based on the examples that are shown for class A, discuss whether the question example belongs to class A or not. \n\n\n\n' \
               'Try to come to a common conclusion. Then, one of you must propose your joint answer, together with the justification. \n\n' \
               'Please do not try to answer right away, and instead first discuss with your partner.'\
               'A proposal starts with "/answer", and then the text. For example: ' \
               '*"/answer it does not belong to A, because there is a yellow block and A has only red or black blocks".*\n\n' \
               'Tip: It might be helpfull to first describe the sample blocks in class A. Then see if you can find a pattern.'\
               'Look for the number of blocks of a type, lines of one color or positions in the grid.'\
               'The other player must then type "/agree", to show that this answer is indeed the joint answer. \n\n' \
               'You can keep discussing after a proposal has been made, but the round only ends once one of you has typed a proposal and the other has agreed to it.'
        rand = random.choice(range(5))
        filename = law + '_' + instances + '_' + str(rand) + ".jpg"

        SYN_ROOM_DICT.append({
            'question': ques,
            'data': CONFIG['path']['data_url'] + filename
        })
    return SYN_ROOM_DICT

def process_whichbird(input_dict, n_ques, room):
    SYN_ROOM_DICT = []
    
    rands = random.sample(range(10), n_ques)
    
    for rand in rands:

        filename = "birds" + '_' + str(rand) + ".jpg"
        
        SYN_ROOM_DICT.append({
            'question': 'Which one is described by this?\n\n\n\n'\
                        'Try to come to a common conclusion. Then, one of you must propose your joint answer, together with the justification. \n\n' \
                        'Please do not try to answer right away, and instead first discuss with your partner.'\
                        'A proposal starts with "/answer", and then the text. For example: ' \
                        '*"/answer The text describes the first picture because the bird has a black tail.".*\n\n' \
                        'Don‘t just say "because it fits the description" in your answer. Please explain why you think the picture fits the text based on specific features.\n\n' \
                        'The other player must then type "/agree", to show that this answer is indeed the joint answer. \n\n' \
                        'You can keep discussing after a proposal has been made, but the round only ends once one of you has typed a proposal and the other player has agreed to it.',
            'data': CONFIG['path']['data_url'] + filename
        })
    return SYN_ROOM_DICT


def call_the_task(dict_task, num_ques, room_name):
    """
    Called by the bot to get the data for the room
    :param dict_task: dict of task
    :return: game_room_data  A dict of Question, Build-up Category Name and Data list
    """
    print(dict_task)
    all_data = []
    # Check which game
    for game in dict_task.keys():
        print(game)
        if game == 'whichpattern':
            new_data = process_whichpattern(dict_task, num_ques, room_name)
        elif game == 'whichbird':
            new_data = process_whichbird(dict_task, num_ques, room_name)
        else:
            continue
        print("new data: ",new_data)
        all_data.extend(new_data)
        print("all data: ", all_data)

    return all_data
