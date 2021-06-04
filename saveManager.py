import csv
import json
import os

data = os.getcwd() + "\\data.json"


def write(**kwargs):
    with open(data, 'w') as f:
        f.write(json.dumps(kwargs))


def read() -> dict:
    if os.path.exists(data):
        with open(data, 'r') as f:
            return json.loads(f.read())
    return None


def to_csv(prog_scores: dict):
    with open('names.csv', 'w', newline='') as csvfile:
        fieldnames = ["name", "score"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for key in prog_scores.keys():
            writer.writerow({"name": key, "score": prog_scores.get(key)})
