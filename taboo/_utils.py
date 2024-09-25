import json

from taboo.__main__ import TabooBot, SessionManager, Session

taboo = TabooBot()

taboo.sessions = SessionManager(Session)
taboo.taboo_data = taboo.get_taboo_data()
taboo.guesser_instructions = taboo.read_instructions()


def load_instances_from_json_file(filename):
    file = open(filename)
    data = json.load(file)
    return data

def test_load_instances_from_json_file():
    assert load_instances_from_json_file('data/taboo_words.json')  == 0

def test_show_instructions():
    assert taboo.show_instructions('14') == 0