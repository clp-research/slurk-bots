import json
import os

interactions = []
with open(os.path.join(ROOT, "data", "logs", 'runs_interactions.json'), 'r', encoding='utf8') as f:
    json_list = list(f)
    for json_str in json_list:
        log = json.loads(json_str)


with open(os.path.join(ROOT, "data", "logs", f'parsed_runs_interactions.json'), 'w', encoding='utf8') as json_file:
    json.dump(text_messages, json_file, indent=4, ensure_ascii=False)