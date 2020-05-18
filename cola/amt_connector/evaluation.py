# This script evaluates the logfiles and generates all needed information for payment
import glob
import json
import os
import configparser
import requests


# --- class implementation --------------------------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------------------------------------------------
class Evaluation:
    """ Evaluation Module for the slack tasks (cola chat).

    This class provides the code to evaluate all dialogues/tasks given a set of log-files from slurk.
    There is one function available:
    evaluate() goes through all logs from slurk, grabs all generated tokens and analyses the dialogues to check
    for valid HIT tasks, waiting-room-only turkers and necessary information for generating the correct amount of
    bonus payment.

    Args:
        mturk_session   A string. Folder name of the current HIT-Session. The log-files need to be in the
                        './logs/mturk_session/' location.

    """
    def __init__(self, mturk_session):
        self.path_logs = "./logs/" + mturk_session + "/"
        self.path_evaluation = "./results/" + mturk_session + "/"
        self.tokens = []
        self.evaluation_info = []

# --- public functions ------------------------------------------------------------------------------------------------
    def evaluate(self):
        """ Generates a results.py with information about all generated tokens."""

        # Load the logs.
        logs = glob.glob(self.path_logs + '*.json')
        if len(logs) == 0:
            print("No Logs found in '" + self.path_logs + "'. Finished.")
            return
        else:
            print("The following logs were found:")
            for log in logs:
                print(str(log))

        self._load()

        # get all waiting room tokens
        print("Checking for waiting room tokens.")
        # Go through all logs.
        for log in logs:
            # Check if the log comes from a waiting room.
            if "Waiting Room" in log:
                # Evaluate the tokens.
                tokens, evaluation_info = self._check_wr_log(log)
                # Append the evaluated tokens.
                for token in tokens:
                    if token not in self.tokens:
                        self.tokens.append(token)
                        print("Found new token: " + str(token))
                for evaluation_info_single in evaluation_info:
                    if evaluation_info_single not in self.evaluation_info:
                        self.evaluation_info.append(evaluation_info_single)
                        print("Added evaluation info for token: " + str(evaluation_info_single['token']))
                        print(evaluation_info_single)

        # Get all chat tokens.
        print("Checking for chat tokens.")
        # Go through all logs.
        for log in logs:
            # Check if the log comes from the meetup. This is meetup, because slack does not allow to create an own
            # chat room.
            if "cola" in log:
                # Evaluate the tokens.
                tokens, evaluation_info = self._check_chat_log(log)
                # Append the evaluated tokens.
                for token in tokens:
                    if token not in self.tokens:
                        self.tokens.append(token)
                        print("Found new token: " + str(token))
                for evaluation_info_single in evaluation_info:
                    if evaluation_info_single not in self.evaluation_info:
                        self.evaluation_info.append(evaluation_info_single)
                        print("Added evaluation info for token: " + str(evaluation_info_single['token']))
                        print(str(evaluation_info_single))

        self._save()

# --- private functions -----------------------------------------------------------------------------------------------
    def _check_wr_log(self, log):
        """ Check the waiting room tokens.

        Args:
            log     A list of dict. The log to check for the waiting room tokens.

        Returns:
            tokens              A list of tokens.
            evaluation_info     A list of dict. Additional information for all tokens.
        """
        with open(log) as log_file:
            tokens = []
            evaluation_info = []
            log_text = json.load(log_file)
            # Go through all log entries.
            for item in log_text:
                # Check for a token print.
                if item['user']['name'] == 'Cola Bot' and item['event'] == 'confirmation_log':
                    print(item)
                    # Split the print into user_id and token.
                    token = item['message'][:6]
                    user_id = item['message'][6:]
                    tokens.append(token)
                    evaluation_info.append({
                        'token': token,
                        'userid': user_id,
                        'info': "waiting_room"
                    })

        return tokens, evaluation_info

    def _check_chat_log(self, log):
        """ Check the chat room (meetup) tokens.

        Args:
            log     A list of dict. The log to check for the chat room tokens.

        Returns:
            tokens              A list of tokens.
            evaluation_info     A list of dict. Additional information for all tokens.

        """
        with open(log) as log_file:
            tokens = []
            evaluation_info = []
            log_text = json.load(log_file)
            # Go through all log entries.
            for item in log_text:
                # Check for a token print. The chat room tokens are generated via the chat moderator.
                if item['user']['name'] == 'Cola Bot' and item['event'] == 'confirmation_log':
                    print(item)
                    # Split the print into user_id and token.
                    chat_token = item['amt_token']
                    room_id = item['room']
                    no_reply = item['status_txt']
                    tokens.append(chat_token)
                    # Compute and append evaluation info
                    evaluation_info.append(self._compute_chat_eval_properties(log_text, room_id, chat_token, no_reply))

        return tokens, evaluation_info

    def _compute_chat_eval_properties(self, log_text, room_id, token, no_reply):
        """ Analyse a chat log according to a specific user with it's token.

        Args:
            log_text    A list of dict. The log file.
            user_id     A string. The user id generated by slurk.
            token       A string. The token generated by the chat room bot.
            no_reply    A string. Information about the type of "no reply", if its a no reply token.

        Returns:
            info        A dict. All important information, see below.

        """

        # Collect the number utterances, that the user and his partner has written.
        utterances_in_room = []
        utterances_ans_room = []

        for item in log_text:
            #print(item['type'])
            if item['event'] == 'text_message' and item['user']['name'] != "Cola Bot":
                print(room_id)
                if str(item['room']).startswith(room_id):
                    #print("check", item['msg'])
                    utterances_in_room.append(item)
            elif item['event'] == 'command' and item['user']['name'] != "Cola Bot" and item['command'].startswith('answer'):
                if str(item['room']).startswith(room_id):
                    utterances_ans_room.append(item)

        # Compute the time of the dialogue.
        # Compute the start time (first utterance).
        dialogue_start_time = min([utterance['date_created'] for utterance in utterances_in_room], default=0)
        # Compute the stop time (last utterance).
        dialogue_end_time = max([utterance['date_created'] for utterance in utterances_in_room], default=0)

        # Compute the time of the commands in the game.
        # Compute the start time (first command).
        ans_dialogue_start_time = min([utterance['date_created'] for utterance in utterances_ans_room], default=0)
        # Compute the stop time (last command).
        ans_dialogue_end_time = max([utterance['date_created'] for utterance in utterances_ans_room], default=0)

        # Compute the time based on start of utterance or start of command
        # Start of the dialogue maybe utterance or command so compute based on
        # whatever starts the first.
        if dialogue_start_time > ans_dialogue_start_time:
                dialogue_start_time = ans_dialogue_start_time
        
        if dialogue_end_time < ans_dialogue_end_time:
                dialogue_end_time = ans_dialogue_end_time

        # "no reply" check
        if no_reply == "no_reply":
            if len(utterances_in_room) == 0 and len(utterances_ans_room) == 0:
                dialogue_pay_result = "no_reply_no_pay"
            else:
                # As token is sent to the room and attached to room_id
                # both players are paid for the time they talked
                dialogue_pay_result = "no_reply_pay"
        else:
            dialogue_pay_result = "chat_room"

        # TODO: Violation check.

        return {
            'token': token,                                         # The token.
            'roomid': room_id,                                      # The room.
            'info': dialogue_pay_result,                            # To be done.
            'duration': dialogue_end_time - dialogue_start_time,    # Duration of the dialogue.
            'turns': len(utterances_ans_room)+len(utterances_in_room)  # Number of utterances, the user has sent.
        }

    def _save(self):
        """ Safe the results.json """
        if not os.path.exists(self.path_evaluation):
            os.makedirs(self.path_evaluation)
        with open(os.path.join(self.path_evaluation, "results.json"), 'w') as file:
            json.dump({'tokens': self.tokens,
                       'evaluation_info': self.evaluation_info},
                      file)

    def _load(self):
        """ Load the results.json """
        if os.path.isfile(os.path.join(self.path_evaluation, "results.json")):
            with open(os.path.join(self.path_evaluation, "results.json")) as file:
                file_content = json.load(file)
                self.tokens = file_content['tokens']
                self.evaluation_info = file_content['evaluation_info']

    def _user2token(self, user_id):
        "get the token for a user id"
        
        url = "http://141.89.97.91/api/v2/tokens"
        headers = {'Authorization': "Token " + CONFIG["logs"]["admin_token"]}
        response = requests.request("GET", url, headers=headers)

        for item in response.json():
            if item["user"] == user_id:
                return item["token"]

        raise ValueError("The user id " + user_id + " has no token associated to it.")

# call the evaluation
if __name__ == '__main__':
    CONFIG = configparser.ConfigParser()
    CONFIG.read('config.ini')
    SESSION = CONFIG['session']['name']

    eval_module = Evaluation(SESSION)
    eval_module.evaluate()
