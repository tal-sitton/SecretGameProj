import json
import os

data = os.getcwd() + "\\data"


def write(**kwargs):
    with open(data, 'w') as f:
        f.write(json.dumps(kwargs))


def read() -> dict:
    if os.path.exists(data):
        with open(data, 'r') as f:
            return json.loads(f.read())
    return None
