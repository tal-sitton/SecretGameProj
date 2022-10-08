import os
import re
import threading
import time
import traceback
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

import saveManager

requests.packages.urllib3.util.connection.HAS_IPV6 = False
reserved_utl_chars = ["!", "*" "(", ")", ";", ":", "@", "&", "=", "+", "$", ",", "/", "?", "%", "#", "[", "]"]

global session

user_scores = {}  # the games the user already scored
prog_scores = {}  # the games the program scored
got_peoples_score = []  # the games the program learned from
games = []  # the games the user has to score
calculated = False  # whether the program already scored all the games
NEEDED_REVIEWS = 20  # how many reviewers to look for every game
MAX_PAGES = 7  # the maximum amount of pages to look for reviewers


def assign_from_json(data):
    """
    assigns the data from jsom file to the variables
    :param data: data from the json
    """
    global user_scores, prog_scores, got_peoples_score, games, calculated
    user_scores = data['user_scores']
    prog_scores = data['prog_scores']
    got_peoples_score = data['got_peoples_score']
    games = data['games']
    calculated = data['calculated']


def get_default_games():
    """
    gets the best games from Metacritic.com
    """
    global games
    req = session.get("https://www.metacritic.com/browse/games/score/metascore/all/all/filtered")
    soup = BeautifulSoup(req.text, 'html.parser')
    names = soup.find_all(name='a', attrs={'class': 'title'})
    names = [g.text for g in names]
    games += list(dict.fromkeys(names))


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


def get_platforms(game: str, non_specific: bool) -> list:
    """
    gets all the platforms of the game
    :param game: the name of the game
    :type game: str
    :param non_specific: whether the game could be not a perfect match to the given name
    :type non_specific: bool
    :return: the urls of the platforms
    """
    query_game = re.sub(' +', ' ', "".join([c for c in game if c not in reserved_utl_chars]))
    req = session.get(f'https://www.metacritic.com/search/game/{query_game}/results?sort=relevancy')
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
    got_peoples_score.append(game)
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


def add_manually():
    """
    adding a game manually - the user gives the name of the game and his rating
    """
    global user_scores, calculated
    game = input("whats the name of the game? ENTER to main menu\n")
    while game != '':
        rating = input("how much do you rate the game from 1 to 5\n")

        while (rating != '' and not rating.isnumeric()) or (
                rating.isnumeric() and (int(rating) < 1 or int(rating) > 5)):
            print("INVALID INPUT")
            rating = input("how much do u rate the game from 1 to 5\n")

        urls = get_platforms(game, True)
        ans = 'n'
        i = 0
        while ans != 'y':
            if i > len(urls) - 1:
                print("we couldn't find the game you wanted")
                break
            ans = input("is this right? " + urls[i] + " ")
            i += 1
        if ans == 'y':
            i -= 1
            req = session.get(urls[i])
            soup = BeautifulSoup(req.text, 'html.parser')
            name = soup.find(name="div", attrs={'class': 'product_title'}).a.text.strip()
            user_scores[name] = rating
            calculated = False
        else:
            print(ans)
        game = input("whats the name of the game? ENTER to main menu\n")
    clear_score()


def user_games_rating():
    """
    manages all the user interaction: asking the user for his opinion about every game
    """
    global user_scores, calculated
    done = 0
    for game in games:
        rating = input(f"What do you think about {game} from 1 to 5? (ENTER if you didn't play, q to quit) ").lower()
        while (rating != "q" and rating != '' and not rating.isnumeric()) or (
                rating.isnumeric() and (int(rating) < 1 or int(rating) > 5)):
            print("THIS ISN'T A VALID ANSWER")
            rating = input(f"What do you think about {game} from 1 to 5? (ENTER if you didn't play) q to quit").lower()
        if rating == 'q':
            break
        if rating != '':
            user_scores[game] = rating
            done += 1
        if done == 5:
            break
    calculated = False
    clear_score()


def manager():
    """
    Managing everything
    """
    manager_msg = "\n" * 100 + "\t\tNice! now that we all set up we can choose what you want to do! you can do couple " \
                               "of things like:\n\t\t'score more games' , 'recommended games' , 'manual' to add games " \
                               "manually,\n\t\t'exit' , and " \
                               "'delete' to delete your preferences and then exit\n\n\n\n "
    print(manager_msg)

    todo = ''
    while todo != 'exit' and todo != 'e':
        todo = input("what do you want to do? ")

        if todo == "score more games" or todo == "s":
            user_games_rating()

        elif todo == "recommended games" or todo == "r":
            if not calculated:
                prog_games_rating()
            print(prog_scores)
            input("continue? press Enter")

        elif todo == "manual" or todo == "m":
            add_manually()

        elif todo == "delete" or todo == "d":
            if os.path.exists(saveManager.data):
                os.remove(saveManager.data)
            break

        saveManager.write(user_scores=user_scores, prog_scores=prog_scores, got_peoples_score=got_peoples_score,
                          games=games, calculated=calculated)
        print(
            "\n" * 100 + "\t\tyour options are: 'score more games' , 'recommended games' ,'manual' to add games "
                         "manually 'exit' and 'delete' to "
                         "delete your preferences and then exit\n\n\n\n ")


def main():
    start_msg = """\tHello, This Program will help find whats your next game will be.
    you just have to answer some questions about some games, and I will calculate whats your next game should be
    Just know that the more questions you answer, the more accurate my calculation will be
    """
    global session
    print(start_msg)
    data = saveManager.read()

    session = requests.Session()
    session.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/74.0.3729.169 Safari/537.36 '
    }

    if data is None:
        get_default_games()
        user_games_rating()
        saveManager.write(user_scores=user_scores, prog_scores=prog_scores, got_peoples_score=got_peoples_score,
                          games=games, calculated=calculated)

    else:
        try:
            assign_from_json(data)
        except Exception as e:
            print(
                f"There was a PROBLEM with reading the saved data... sorry about that. plz start over. ERROR= {type(e)} : {e}")
            os.remove(saveManager.data)
            get_default_games()
            user_games_rating()
            saveManager.write(user_scores=user_scores, prog_scores=prog_scores, got_peoples_score=got_peoples_score,
                              games=games, calculated=calculated)

    manager()


if __name__ == '__main__':
    main()
