'''slurk link generator'''

import random
import configparser
import requests
import json

LINKS_LIST = []

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')

with open('adj.txt', 'r') as adj_file:
    ADJ = adj_file.read().splitlines()

def insert_names_and_tokens(n_hits):
    '''take html webpage source and generate slurk tokens for players'''
    for _ in range(int(n_hits)):
        full_name = random.choice(ADJ)
        url = CONFIG['link_generator']['url']

        headers = {'Authorization': 'Token ' + CONFIG['link_generator']['admin_token'],
                   'Content-Type': 'application/json'}
        data = {"room": "waiting_room", "message_text": True, "message_command": True, "task": "1"}
        login_token = requests.post(url, data=json.dumps(data), headers=headers).text.strip().strip('\"')

        uris = CONFIG['login']['url']+'/?name={}&token={}'.format(full_name, login_token)
        print("login uris: " + uris)
        LINKS_LIST.append(uris)
    return LINKS_LIST

if __name__ == '__main__':
    GENER_LINKS = insert_names_and_tokens(2)
