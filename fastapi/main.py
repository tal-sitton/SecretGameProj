import json
import time
from urllib.parse import quote

import requests
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware

import main_api as backend
import sql_handler

print("start")
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    print("startup")
    sql_handler.startup()
    sql = sql_handler.SQLHandler()
    print("got sql")
    for data in sql.get_data(col="json_data, rowid"):
        json_data, rowid = json.loads(data[0]), data[1]
        json_data['calculating'] = False
        sql.update("json_data", json.dumps(json_data), "rowid", rowid)
    print("done sql startup")


@app.get("/")
def ping():
    return "PING"


@app.post("/login")
def login(username: str = Body(), password: str = Body()):
    sql = sql_handler.SQLHandler()
    if password in sql.get_data("password", ("username", username), str):
        return True
    else:
        return False


@app.post("/signup")
def signup(username: str = Body(), password: str = Body()):
    sql = sql_handler.SQLHandler()
    if username not in sql.get_data("username"):
        sql.insert(username, password)
        return True
    else:
        return False


@app.post("/to-rate")
def to_rate(username: str = Body(), password: str = Body()):
    sql = sql_handler.SQLHandler()
    if login(username, password):
        backend.assign_from_json(sql.get_data(
            "json_data", ("username", username), str)[0])
        return backend.games
    else:
        return False


@app.post("/user-score")
def user_score(username: str = Body(), password: str = Body(), game: str = Body(), rating: str = Body()):
    sql = sql_handler.SQLHandler()
    s = requests.Session()
    s.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/74.0.3729.169 Safari/537.36 '
    }
    backend.session = s
    if login(username, password):
        backend.assign_from_json(sql.get_data(
            "json_data", ("username", username), str)[0])
        if rating.isnumeric():
            backend.user_scores[game] = rating
        backend.games.remove(game)
        backend.clear_score()
        backend.calculated = False
        sql.update("json_data", backend.dump_to_json(), "username", username)
        return True
    else:
        return False


@app.post("/recommended")
def recommended(username: str = Body(), password: str = Body()):
    sql = sql_handler.SQLHandler()
    s = requests.Session()
    s.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/74.0.3729.169 Safari/537.36 '
    }
    backend.session = s
    if login(username, password):
        backend.assign_from_json(
            sql.get_data("json_data", ("username", username), str)[0])

        if (len(backend.prog_scores) == 0 or backend.prev_calc + 5 * 60 < time.time()) and not backend.calculating:
            print("started thread")
            backend.calculate(username)

        print(len(backend.user_scores) == 0, backend.prev_calc +
              5 * 60 < time.time(), not backend.calculating)
        print(backend.prev_calc, time.time())
        arr = [backend.calculating]
        for i, (game, rating) in enumerate(backend.prog_scores.items()):
            arr.append({"_id": str(i), "name": game, "rating": rating})
        return arr
    else:
        return False


@app.post("/manual")
def manual(username: str = Body(), password: str = Body(), game: str = Body()):
    s = requests.Session()
    s.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/74.0.3729.169 Safari/537.36 '
    }
    backend.session = s
    if login(username, password):
        return [quote(url) for url in backend.get_platforms(game, True)]


@app.post("/add-manual")
def add_manual(username: str = Body(), password: str = Body(), url: str = Body(), rating: str = Body()):
    s = requests.Session()
    s.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/74.0.3729.169 Safari/537.36 '
    }
    backend.session = s
    if login(username, password):
        backend.add_manual(username, url, rating)
        return True
    else:
        return False
