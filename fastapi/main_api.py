import json
import re
import threading
import time
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

import sql_handler

requests.packages.urllib3.util.connection.HAS_IPV6 = False
reserved_utl_chars = ["!", "*" "(", ")", ";", ":", "@", "&", "=", "+", "$", ",", "/", "?", "%", "#", "[", "]"]

global session

user_scores = {}  # the games the user already scored
prog_scores = {}  # the games the program scored
got_peoples_score = []  # the games the program learned from
games = []  # the games the user has to score
calculated = False  # whether the program already scored all the games
calculating = False  # whether the program is currently scoring the games
NEEDED_REVIEWS = 20  # how many reviewers to look for every game
MAX_PAGES = 7  # the maximum amount of pages to look for reviewers
prev_calc = 0  # the previews time the scores were calculated


def assign_from_json(data: str):
    """
    assigns the data from jsom file to the variables
    :param data: data from the json
    """
    data = json.loads(data)
    global user_scores, prog_scores, got_peoples_score, games, calculated, calculating, prev_calc
    user_scores = data['user_scores']
    prog_scores = data['prog_scores']
    got_peoples_score = data['got_peoples_score']
    games = data['games']
    calculated = data['calculated']
    calculating = data['calculating']
    prev_calc = data['prev_calc']


def dump_to_json() -> str:
    """
    dumps the variables to json
    :return: the json data
    """
    data = {
        "user_scores": user_scores,
        "prog_scores": prog_scores,
        "got_peoples_score": got_peoples_score,
        "games": games,
        "calculated": calculated,
        "calculating": calculating,
        "prev_calc": prev_calc
    }
    return json.dumps(data)


def get_platform_data(platform_url: str, game: str):
    """
    search how many reviews a game has in a specific platform
    :param platform_url: the url of the platform to check
    :type platform_url: str
    """
    req = session.get(platform_url).text

    soup = BeautifulSoup(req, 'html.parser')
    sum_reviews = soup.find_all(attrs={'class': 'count'})
    try:
        if "metascore_w user large game tbd" not in req:
            sum_reviews = sum_reviews[1]
            if len(str(sum_reviews).split('user-reviews">')) > 1:
                sum_reviews = str(sum_reviews).split('user-reviews">')[1].split("Ratings")[0]
                platforms_data[game].append((platform_url, sum_reviews))
    except Exception as e:
        print(e)


platforms_data = defaultdict(list)


def most_viewed_platform(platforms_urls: [], game: str) -> str:
    """
    gets the most viewed platform from the given list
    :param platforms_urls: all the platform of a specific game
    :return the url of the most viewed platform
    """
    threads = []
    for url in platforms_urls:
        t = threading.Thread(target=get_platform_data, args=[url, game])
        t.start()
        threads.append(t)
    while [t for t in threads if t.is_alive()]:
        pass
    platforms_data[game].sort(key=lambda x: -int(x[1]))
    try:
        return platforms_data[game][0][0]
    except IndexError:
        print(f"{game} DOESN'T HAVE ANY REVIEW IN ANY CONSOLE IN METACRITIC")
        return None


def get_platforms(game: str, non_specific: bool) -> [str]:
    """
    gets all the platforms of the game
    :param game: the name of the game
    :type game: str
    :param non_specific: whether the game could be not a perfect match to the given name
    :type non_specific: bool
    :return: the urls of the platforms
    """
    query_game = re.sub(' +', ' ', "".join([c for c in game if c not in reserved_utl_chars]))
    url = f'https://www.metacritic.com/search/game/{query_game}/results?sort=relevancy'
    print(url)
    req = session.get(url)
    soup = BeautifulSoup(req.text, 'html.parser')
    consoles = soup.find_all(name='a', href=True)

    urls = []
    for con in consoles:
        i = str(con)
        n = True
        if 'href="/game/' in i and "div" not in i and 'section' not in i:
            url = i.split('<a href="')[1].split('">')[0]
            if non_specific or con.text.strip().lower() == game.lower():
                urls.append('https://www.metacritic.com' + url)
    return urls


url_of_reviewers = []


def get_reviewers_for_game(game: str):
    """
    get reviewers for a specific game
    :param game: the name of the game to check
    """
    print(f"checking {game}")
    origin_url = get_platforms(game, False)
    if not origin_url:
        print(f"COULDN'T FIND {game} IN METACRITIC")
        return []
    elif len(origin_url) > 1:
        origin_url = most_viewed_platform(origin_url, game)
    else:
        origin_url = origin_url[0]

    origin_url += r"/user-reviews?sort-by=most-helpful&num_items=100"
    url = origin_url
    reviewers_count = 0
    page = 0

    req = session.get(url)
    soup = BeautifulSoup(req.text, 'html.parser')
    reviews = soup.find_all(attrs={'class': 'review user_review'})
    while reviewers_count < NEEDED_REVIEWS and page < 15 and reviews:
        for review in reviews:
            grade = BeautifulSoup(str(review), 'html.parser').find(attrs={'class': 'review_grade'}).text
            if abs(int(user_scores[game]) * 2 - int(grade)) <= 2:
                reviewer_link = [str(i) for i in
                                 BeautifulSoup(str(review), 'html.parser').find_all(href=True, name='a')]
                real_link = None
                for link in reviewer_link:
                    if "/user/" in link:
                        real_link = link.split('"')[1].split('"')[0]
                        break
                if real_link:
                    url_of_reviewers.append(
                        f"https://www.metacritic.com/{real_link}?myscore-filter=Game&myreview-sort=score")
                    reviewers_count += 1
        if reviewers_count < NEEDED_REVIEWS:
            page += 1
            url = origin_url + f'&page={page}'
            req = session.get(url)
            soup = BeautifulSoup(req.text, 'html.parser')
            reviews = soup.find_all(attrs={'class': 'review user_review'})
    got_peoples_score.append(game)
    print({game}, {reviewers_count}, {origin_url})


def get_reviewers_to_check() -> list:
    """
    gets the reviewers to check and learn from
    :return: all the reviewers the program has to check
    """
    threads = []
    for game in user_scores:
        if game not in got_peoples_score:
            t = threading.Thread(target=get_reviewers_for_game, args=[game])
            t.start()
            threads.append(t)
    while [t for t in threads if t.is_alive()]:
        pass
    platforms_data.clear()
    return url_of_reviewers


index = 0


def rate(reviewer: str, length: int):
    """
    Rates games based on a reviewer opinion of the game
    :param reviewer: the reviewer the program needs to check
    :type reviewer: str
    :param length: how many reviewers there are in total
    :type length: int
    """
    global index

    try:
        res = session.get(reviewer)
        reviews = [str(i) for i in BeautifulSoup(res.text, 'html.parser').find_all(attrs={'class': 'review_stats'})]
        for review in reviews:
            grade = int(BeautifulSoup(review, 'html.parser').find(attrs={'class': 'review_score'}).text)
            game_name = BeautifulSoup(review, 'html.parser').find(attrs={'class': 'product_title'}).text
            if game_name not in games:
                games.insert(0, game_name)
            if grade >= 9:
                if prog_scores.get(game_name):
                    prog_scores[game_name] = prog_scores.get(game_name) + 1
                else:
                    prog_scores[game_name] = 1
            elif grade <= 2:
                if prog_scores.get(game_name):
                    prog_scores[game_name] = prog_scores.get(game_name) - 1
                else:
                    prog_scores[game_name] = -1
        print(str(index + 1) + "/" + str(length))
        index += 1
    except Exception as e:
        print(e)
        print("ERROR IN RATE")


def prog_games_rating():
    """
    rates according to every single reviewer the program gathered
    """
    global index
    global calculated
    reviewers_urls = get_reviewers_to_check()
    index = 0
    threads = []
    for reviewer in reviewers_urls:
        t = threading.Thread(target=rate, args=[reviewer, len(reviewers_urls)])
        time.sleep(0.03)
        t.start()
        threads.append(t)
    while [t for t in threads if t.is_alive()]:
        pass
    url_of_reviewers.clear()

    clear_score()
    calculated = True


def calculate(username: str):
    global calculating
    if not calculated:
        sql = sql_handler.SQLHandler()
        calculating = True
        sql.update("json_data", dump_to_json(), "username", username)

        threading.Thread(target=calculation_thread, args=[username]).start()


def calculation_thread(username: str):
    global calculating, prev_calc, user_scores, session
    sql = sql_handler.SQLHandler()
    prog_games_rating()
    calculating = False
    prev_calc = time.time()

    data = json.loads(sql.get_data("json_data", ("username", username), str)[0])
    user_scores = data["user_scores"]
    clear_score()
    sql.update("json_data", dump_to_json(), "username", username)
    print("done calculating")


def clear_score():
    """
    Clears and organize the lists
    """
    global prog_scores
    for game in user_scores:
        if game in prog_scores:
            del prog_scores[game]
        if game in games:
            games.remove(game)
    prog_scores = {k: v for k, v in sorted(prog_scores.items(), key=lambda item: -item[1]) if v != 0}


def add_manual(username: str, url: str, rating: str):
    global calculated, user_scores, session
    sql = sql_handler.SQLHandler()

    req = session.get(url)
    with open ("../m.html", "w") as f:
      f.write(req.text)
    print("url=",url)
    soup = BeautifulSoup(req.text, 'html.parser')
    name = soup.find(name="div", attrs={'class': 'product_title'}).a.text.strip()
    user_scores[name] = rating
    calculated = False
    clear_score()
    sql.update("json_data", dump_to_json(), "username", username)
