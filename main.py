import os

import requests
from bs4 import BeautifulSoup

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}

user_scores = {}
prog_scores = {}
got_peoples_score = []
games = []


def get_default_games():
    global games
    req = requests.get("https://www.metacritic.com/browse/games/score/metascore/all/all/filtered", headers=HEADERS_GET)
    soup = BeautifulSoup(req.text, 'html.parser')
    names = soup.find_all(name='a', attrs={'class': 'title'})
    names = [g.text for g in names]
    noDupGames = []
    [noDupGames.append(a) for a in names if a not in noDupGames]
    games += noDupGames


def real_most_viewed_platform(urls: []) -> str:
    reviews = []
    for url in urls:
        req = requests.get(url, headers=HEADERS_GET)
        soup = BeautifulSoup(req.text, 'html.parser')
        sumReviews = soup.find_all(attrs={'class': 'count'})[1]
        sumReviews = str(sumReviews).split('user-reviews">')[1].split("Ratings")[0]
        reviews.append((sumReviews, url))

    reviews.sort(key=lambda x: -int(x[0]))
    print(reviews)
    return reviews[0][1]


def most_viewed_platform(game: str) -> str:
    req = requests.get(f'https://www.metacritic.com/search/game/{game}/results', headers=HEADERS_GET)
    soup = BeautifulSoup(req.text, 'html.parser')
    consoles = soup.find_all(name='a', href=True)
    consoles = [str(con) for con in consoles]

    urls = []
    for i in consoles:
        n = True
        if 'href="/game/' in i and "div" not in i and 'section' not in i:
            url = i.split('<a href="')[1].split('">')[0]
            for word in url.split('/')[3].replace("-", ' '):
                if word not in game:
                    n = False
            if n is False:
                continue
            urls.append('https://www.metacritic.com' + url)
    print(urls)
    return real_most_viewed_platform(urls)


def get_rating_from_people():
    for game in user_scores:
        if game not in got_peoples_score:
            got_peoples_score.append(game)
            url = most_viewed_platform(game)


def user_games_rating():
    global user_scores
    done = 0
    for game in games:
        rating = input(f"What do you think about {game} from 1 to 5? (ENTER if you didn't play) ")
        while (rating != '' and not rating.isnumeric()) or (
                rating.isnumeric() and (int(rating) < 1 or int(rating) > 5)):
            print("THIS ISN'T A VALID ANSWER")
            rating = input(f"What do you think about {game} from 1 to 5? (ENTER if you didn't play) ")
        if rating != '':
            user_scores[game] = rating
            if game in prog_scores:
                del prog_scores[game]
            done += 1
        games.remove(game)
        if done == 5:
            break
    print(user_scores)


def manager():
    todo = ''
    while todo != 'exit':

        manager_msg = "\n" * 100 + """\t\tNice! now that we all set up we can choose what you want to do!
        you can do couple of things like 'score more games' , 'recommended games' and 'exit\n\n\n\n
        """
        print(manager_msg)
        todo = input("what do you want to do?")

        if todo == "score more games":
            user_games_rating()

        elif todo == "recommended games":
            print(prog_scores)


def main():
    start_msg = """\tHello, This Program will help find whats your next game will be.
    you just have to answer some questions about some games, and I will calculate whats your next game should be
    Just know that the more questions you answer, the more accurate my calculation will be
    """
    print(start_msg)
    get_default_games()
    user_games_rating()
    manager()
    # platform = most_viewed_platform("watch dogs: legion")
    # print(platform)


if __name__ == '__main__':
    main()
