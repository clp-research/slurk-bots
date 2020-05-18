'''configuring MTurk account given settings / credentials in config.ini'''

import configparser
import boto3

class ConnectToMTurk():

    def __init__(self):
        '''defines MTurk working environment'''
        CONFIG = configparser.ConfigParser()
        CONFIG.read('config.ini')

        self.mturk = boto3.client(
            'mturk',
            aws_access_key_id=CONFIG['credentials']['aws_access_key_id'],
            aws_secret_access_key=CONFIG['credentials']['aws_secret_access_key'],
            region_name='us-east-1',
            endpoint_url=CONFIG['environment']['endpoint_url']
        )


    def create_command_qualification(self):
        questions = open('cola_qs.xml', 'r').read()
        answers = open('cola_ans.xml', 'r').read()

        qual_response = self.mturk.create_qualification_type(
            Name='Game command Screening Test',
            Keywords='test, qualification, boto',
            Description='This is a brief test to check if players know the game commands',
            QualificationTypeStatus='Active',
            Test=questions,
            AnswerKey=answers,
            TestDurationInSeconds=60)

        print(qual_response['QualificationType']['QualificationTypeId'])
