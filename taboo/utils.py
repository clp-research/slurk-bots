import json


def save_file(data, file_name: str):
    """
    Store a results file in your game results' directory. The top-level directory is 'results'.

    :param sub_dir: automatically created when given; otherwise an error will be thrown.
    :param data: to store
    :param file_name: can have subdirectories e.g. "sub/my_file"
    """
    with open(file_name, "w", encoding='utf-8') as f:
        if file_name.endswith(".json"):
            json.dump(data, f,  indent=4, ensure_ascii=False)
        else:
            f.write(data)
    return

