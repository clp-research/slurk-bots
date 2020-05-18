'''publish batches of HITs on MTurk'''
import time
import json
import configparser
import os

import aws_config
from slurk_link_generator import insert_names_and_tokens

RESULTS = []

SLIDES = ['https://raw.githubusercontent.com/nattari/cola_instructions/master/cola_inst_001.jpeg',
          'https://raw.githubusercontent.com/nattari/cola_instructions/master/cola_inst_002.jpeg',
          'https://raw.githubusercontent.com/nattari/cola_instructions/master/cola_inst_003.jpeg',
          'https://raw.githubusercontent.com/nattari/cola_instructions/master/cola_inst_004.jpeg',
          'https://raw.githubusercontent.com/nattari/cola_instructions/master/cola_inst_005.jpeg',
          'https://raw.githubusercontent.com/nattari/cola_instructions/master/cola_inst_006.jpeg',
          'https://raw.githubusercontent.com/nattari/cola_instructions/master/cola_inst_007.jpeg',
          'https://raw.githubusercontent.com/nattari/cola_instructions/master/cola_inst_008.jpeg']

HTML = open('./CoLA.html', 'r').read()
QUESTION_XML = """
        <HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
        <HTMLContent><![CDATA[{}]]></HTMLContent>
        <FrameHeight>650</FrameHeight>
        </HTMLQuestion>"""
QUESTION = QUESTION_XML.format(HTML)
Q_ATTR = {
    # Amount of assignments per HIT
    'MaxAssignments': 1,
    # How long the task is available on MTurk (1 day)
    'LifetimeInSeconds': 60*60*1,
    # How much time Workers have in order to complete each task (20 minutes)
    'AssignmentDurationInSeconds': 60*20,
    # the HIT is automatically approved after this number of minutes (0.5 day)
    'AutoApprovalDelayInSeconds': 60*720,
    # The reward we offer Workers for each task
    'Reward': '0.10',
    'Title': 'Play our Chat Game for 2 workers and earn up to 0.85$ in 3 minutes!',
    'Keywords': 'dialogue, game',
    'Description': 'You and your partner need to discuss and reason,\
                            togther. It is important in this game that both,\
                            of you must reach a common agreement.'
}

def publish(number_of_hits):
    '''publish HITs with creates URLs in predefined HTML template'''
    link = insert_names_and_tokens(number_of_hits)
    for login_url in link:
        create(login_url)

def create(login_url):
    '''defining HITs' template for MTurk'''
    print(login_url)
    question = QUESTION.replace('${Link}', login_url).\
                        replace('${Image1}', SLIDES[0]).\
                        replace('${Image2}', SLIDES[1]).\
                        replace('${Image3}', SLIDES[2]).\
                        replace('${Image4}', SLIDES[3]).\
                        replace('${Image5}', SLIDES[4]).\
                        replace('${Image6}', SLIDES[5]).\
                        replace('${Image7}', SLIDES[6]).\
                        replace('${Image8}', SLIDES[7])
    #print(question)
    mturk_connector = aws_config.ConnectToMTurk()
    #mturk_connector.create_command_qualification()
    mturk = mturk_connector.mturk

    new_hit = mturk.create_hit(
        **Q_ATTR,
        Question=question,
        QualificationRequirements=[
            #{
            #    'QualificationTypeId' : '3ETJLUMS0DM8X13DGYGLAJ6V7SNU3X',
            #    'Comparator' : 'NotIn',
            #    'IntegerValues' :
            #        [
            #            6, 7, 8, 9, 10
            #        ],
            #    'ActionsGuarded' : 'PreviewAndAccept'
            #},
            {
                'QualificationTypeId' : '00000000000000000071',
                'Comparator' : 'In',
                'LocaleValues' : [
                    {'Country':'GB'}, {'Country':'US'},
                    {'Country':'AU'}, {'Country':'CA'},
                    {'Country':'IE'}, {'Country':'DE'}
                    ],
                'ActionsGuarded': 'PreviewAndAccept'
            },
            {
                'QualificationTypeId' : '00000000000000000040',
                'Comparator' : 'GreaterThanOrEqualTo',
                'IntegerValues' : [
                    2000
                    ],
                'ActionsGuarded': 'PreviewAndAccept'
            }
            #{
            #    'QualificationTypeId': '3X8OU3XHWD1ZRF1SJZ3XJDGXPEXDUV',
            #    'Comparator': 'EqualTo',
            #    'IntegerValues': [100]
            #}
            ]
    )

    RESULTS.append({
        'link': login_url,
        'hit_id': new_hit['HIT']['HITId']
    })

    print('A new HIT has been created. You can preview it here:')
    print('https://worker.mturk.com/mturk/preview?groupId=' + new_hit['HIT']['HITGroupId'])
    print('HITID = ' + new_hit['HIT']['HITId'] + ' (Use to Get Results)')

if __name__ == "__main__":
    CONFIG = configparser.ConfigParser()
    CONFIG.read('config.ini')
    SESSION = CONFIG['session']['name']
    HITS = CONFIG['session']['hits']

    publish(HITS)

    if not os.path.isdir('./published/' + SESSION):
        os.mkdir('./published/' + SESSION)

    MOMENT = time.strftime("%Y-%b-%d__%H_%M_%S", time.localtime())
    with open('./published/' + SESSION + '/data_'+ MOMENT +'.json', 'w') as outfile:
        json.dump(RESULTS, outfile)
