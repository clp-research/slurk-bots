import json
from dataclasses import dataclass


@dataclass
class Clue:
    content: str
    room_id : int


def test_test():
    with open("./results/2.jsonl_text_messages.json") as f:
        logs = json.load(f)
        clues = []
        for log in logs:
            if log.get('event') == 'clue':
                clues.append(Clue(content=log['data']['content'], room_id=log['room_id']))
        assert logs
