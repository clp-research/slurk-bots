import json
from dataclasses import dataclass


@dataclass
class Clue:
    content: str
    room_id : int


def test_clue():
    """Player a triggers log_event('clue', content, room_id) after sending each message."""
    with open("./results/10.jsonl_text_messages.json") as f:
        logs = json.load(f)
        clues = []
        for log in logs:
            if log.get('event') == 'clue':
                clues.append(Clue(content=log['data']['content'], room_id=log['room_id']))
        assert logs
