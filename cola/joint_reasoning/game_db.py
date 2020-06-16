import configparser
import os
import json
from cola_data_processing import cola_task_and_rules

LAST_GAMES_PLAYED = []
LAST_BIRDS_CATEGORY = []
LAST_SYNTHETIC_CATEGORY = []
LAST_TEXT_CATEGORY = []

class ColaGameDb():
    """
    Cola Database Class
    Provides information on what game types should be played.
    Birds - Ask about description of a certain bird type.
    Text Comprehension - Shows sentences to players and they have
                         find answer and play.
    Logical Reasoning - Identify patterns / rules to describe a
                        category.
    """

#    global CHAT_NAMESPACE

    # initialize the object variables
    def __init__(self, room):
        # Read the config file #
        self.CONFIG = configparser.ConfigParser()
        self.CONFIG.read('cola_data_processing/cola_config.ini')

        self.room = room
        self.players = []
        self.room_data_ready = False
        self.game_names = []
        self.room_data = []
        self.answer_status = False
        self.count_msg = 0
        self.first_answer = False
        self.curr_player_ans_id = []
        self.game_over_status = False
        self.current_state = None
        self.ready_flag = False
        self.ready_id = set()

        self.ready_timer = None
        self.conversation_timer = None
        self.answer_timer = None
        self.join_timer = None

    # --- instance methods --------------------------------------------------------
    def add_users(self, player):
        """ Assign a person to the instance of the database."""
        if not self.room_data_ready:
            player['got_noreply_token'] = False
            self.players.append(player)
        else:
            print("Players should be present, once room data is ready!")

    def generate_cola_data(self):
        """" Generate data for each room """

        num_ques_game = int(self.CONFIG['param']['num_ques_per_game'])
        total_games = int(self.CONFIG['param']['num_games'])

        # get task names in a game #
        self._get_game_name(total_games)

        # get category names / rules for each game #
        instances_of_room = self._get_game_instance(num_ques_game)
        print("current game", instances_of_room)
        print("room:", self.room)
        # get room data for the task #
        self.room_data = cola_task_and_rules.call_the_task(instances_of_room,
                                                           num_ques_game, self.room)
        print(self.room_data)

        # the data for the game is ready
        self.room_data_ready = True

    # --- private methods ---------------------------------------------------------
    def _get_game_name(self, num_games):
        """ get the game name to be played and categories to display """
        global LAST_GAMES_PLAYED

        # handle games in each room
        game_list_cola = open(os.path.join(
            self.CONFIG['process']['proc_path'],
            self.CONFIG['process']['game_file'])).readlines()
        game_list_cola = [each_type.split('\n')[0]
                          for each_type in game_list_cola]
        print(game_list_cola, LAST_GAMES_PLAYED)

        self.game_names, LAST_GAMES_PLAYED = ColaGameDb.get_current_params(num_games,
                                                                           game_list_cola,
                                                                           LAST_GAMES_PLAYED)
        print("game_names: ", self.game_names)


    def _get_game_instance(self, num_ques):
        """ get the instances of each game """
        global LAST_BIRDS_CATEGORY, LAST_SYNTHETIC_CATEGORY, LAST_TEXT_CATEGORY

        game_instances = {}
        game_instances = game_instances.fromkeys(self.game_names)
        game_instances = dict([(key, []) for key in game_instances])
        # handle categories for each room
        for sub_game in self.game_names:
            if sub_game == 'birds':
                with open(os.path.join(self.CONFIG['process']['proc_path'],
                                       self.CONFIG['process']['birds_json'])) as file:
                    bird_category = json.load(file)
                bird_category_keys = bird_category.keys()

                bird_cat_per_game = int(self.CONFIG['param']['num_birds_rules'])
                num_cat = bird_cat_per_game * num_ques
                birds_cat_names, LAST_BIRDS_CATEGORY = ColaGameDb.get_current_params(
                    num_cat, bird_category_keys, LAST_BIRDS_CATEGORY)
                game_instances['birds'].extend(birds_cat_names)
            elif sub_game == 'synthetic':
                with open(os.path.join(self.CONFIG['process']['proc_path'],
                                       self.CONFIG['process']['synthetic_json'])) as file:
                    syn_category = json.load(file)
                syn_category_keys = syn_category['rules']

                syn_cat_per_game = int(self.CONFIG['param']['num_synthetic_rules'])
                num_cat = syn_cat_per_game * num_ques
                syn_cat_names, LAST_SYNTHETIC_CATEGORY = ColaGameDb.get_current_params(
                    num_cat, syn_category_keys, LAST_SYNTHETIC_CATEGORY)
                game_instances['synthetic'].extend(syn_cat_names)
            elif sub_game == 'textcomp':
                with open(os.path.join(self.CONFIG['process']['proc_path'],
                                       self.CONFIG['process']['textcomp_json'])) as file:
                    text_category = json.load(file)
                text_category_keys = text_category['rules']

                text_cat_per_game = int(self.CONFIG['param']['num_text_rules'])
                num_cat = text_cat_per_game * num_ques
                text_cat_names, LAST_TEXT_CATEGORY = ColaGameDb.get_current_params(
                    num_cat, text_category_keys, LAST_TEXT_CATEGORY)
                game_instances['textcomp'].extend(text_cat_names)

        return game_instances

    @staticmethod
    def get_current_params(num, name_list, prev_state):
        ''' Update the last game state (global) and load current games (room) '''
        curr_games = []
        residue = list(set(name_list) - set(prev_state))

        if len(residue) >= num:
            for _ in range(num):
                name = residue.pop()
                curr_games.append(name)
                prev_state.append(name)
        else:
            if not residue:
                residue = name_list
                prev_state = []
                for _ in range(num):
                    name = residue.pop()
                    curr_games.append(name)
                    prev_state.append(name)
            else:
                diff_len = num - len(residue)
                residue = residue + name_list[0:diff_len]
                prev_state = []
                for _ in range(num):
                    name = residue.pop()
                    curr_games.append(name)
                    prev_state.append(name)

        return curr_games, prev_state