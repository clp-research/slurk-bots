import json
from dataclasses import dataclass

from drawing_game.data.logs.process_logs import build_interactions_file


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

def test_target_grid():
    with open("./results/10.jsonl_text_messages.json") as f:
        logs = json.load(f)
        grids = []
        for log in logs:
            if log.get('event') == 'target grid':
                grids.append(Clue(content=log['data']['content'], room_id=log['room_id']))
        assert logs

def test_process_logs():
    build_interactions_file("./results/10.jsonl_text_messages.json", 'foo')
