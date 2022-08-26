import asyncio
import os
import re

import aiohttp
import requests
from bs4 import BeautifulSoup

import saveManager

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}

reserved_utl_chars = ["!", "*" "(", ")", ";", ":", "@", "&", "=", "+", "$", ",", "/", "?", "%", "#", "[", "]"]

user_scores = {}
prog_scores = {}
got_peoples_score = []
games = []
calculated = False

NEEDED_REVIEWS = 40


def assign_from_json(data):
    """
    Assigns the data from jsom file to the variables
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
    Gets the best games from Metacritic.com
    """
    global games
    req = requests.get("https://www.metacritic.com/browse/games/score/metascore/all/all/filtered", headers=HEADERS_GET)
    soup = BeautifulSoup(req.text, 'html.parser')
    names = soup.find_all(name='a', attrs={'class': 'title'})
    names = [g.text for g in names]
    no_dup_games = []
    [no_dup_games.append(a) for a in names if a not in no_dup_games]
    games += no_dup_games


async def platform_data(session: aiohttp.client.ClientSession, platform_url: str):
    """
    search how many reviews a game has in a specific platform
    :param session: the session used to make requests
    :type session: aiohttp.client.ClientSession
    :param platform_url: the url of the platform to check
    :type platform_url: str
    """
    async with session.get(platform_url, headers=HEADERS_GET) as response:
        req = await response.text()

    soup = BeautifulSoup(req, 'html.parser')
    sum_reviews = soup.find_all(attrs={'class': 'count'})
    try:
        if "metascore_w user large game tbd" not in req:
            sum_reviews = sum_reviews[1]
            if len(str(sum_reviews).split('user-reviews">')) > 1:
                sum_reviews = str(sum_reviews).split('user-reviews">')[1].split("Ratings")[0]
                reviews.append((platform_url, sum_reviews))
    except Exception as e:
        print(platform_url, e)


reviews = []


async def most_viewed_platform(platforms_urls: []):
    """
    gets the most viewed platform from the given list
    :param platforms_urls: all the platform of a specific game
    """
    global platform
    reviews.clear()
    platforms_urls = platforms_urls[0:4]
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in platforms_urls:
            task = asyncio.ensure_future(platform_data(session, url))
            tasks.append(task)
        await asyncio.gather(*tasks)

    reviews.sort(key=lambda x: -int(x[1]))
    try:
        platform = reviews[0][0]
    except IndexError:
        print("THE GAME DOESN'T HAVE ANY REVIEW IN ANY CONSOLE IN METACRITIC")
        platform = None


platform = None


async def get_platforms(game: str, non_specific: bool = False) -> list:
    """
    Gets all the platforms of the game
    :param game: the name of the game
    :type game: str
    :param non_specific: whether the game could be not a perfect match to the given name
    :type non_specific: bool
    :return: the urls of the platforms
    :rtype: list
    """
    query_game = re.sub(' +', ' ', "".join([c for c in game if c not in reserved_utl_chars]))
    req = requests.get(f'https://www.metacritic.com/search/game/{query_game}/results?sort=relevancy', headers=HEADERS_GET)
    soup = BeautifulSoup(req.text, 'html.parser')
    consoles = soup.find_all(name='a', href=True)
    consoles = [str(con) for con in consoles]

    urls = []
    for i in consoles:
        n = True
        if 'href="/game/' in i and "div" not in i and 'section' not in i:
            url = i.split('<a href="')[1].split('">')[0]
            if not non_specific:
                for word in url.split('/')[3].replace("-", ' ').lower():
                    if word not in game.lower():
                        n = False
                        break
            if n:
                urls.append('https://www.metacritic.com' + url)
    return urls


async def get_reviewers_to_check() -> list:
    """
    Gets the reviewers to check and learn from
    :return: all the reviewers the program has to check
    :rtype: list
    """
    session = requests.Session()
    print("started get_reviewers_to_check")
    url_of_reviewers = []
    for game in user_scores:
        if game not in got_peoples_score:
            print(f"checking {game}")
            got_peoples_score.append(game)
            await most_viewed_platform(await get_platforms(game))
            origin_url = platform
            if origin_url is None:
                print(f"COULDN'T FIND {game} IN METACRITIC")
                continue
            origin_url += r"/user-reviews?sort-by=most-helpful&num_items=100"
            url = origin_url
            reviewers_count = 0
            page = 0

            req = session.get(url, headers=HEADERS_GET)
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
                            reviewers_count += 1
                            url_of_reviewers.append(
                                f"https://www.metacritic.com/{real_link}?myscore-filter=Game&myreview-sort=score")
                if reviewers_count <= NEEDED_REVIEWS:
                    page += 1
                    url = origin_url + f'&page={page}'
                    req = session.get(url, headers=HEADERS_GET)
                    soup = BeautifulSoup(req.text, 'html.parser')
                    reviews = soup.find_all(attrs={'class': 'review user_review'})
            print({game}, {reviewers_count}, {origin_url})
    session.close()
    return url_of_reviewers


index = 0


async def rate(session: aiohttp.client.ClientSession, reviewer: str, length: int):
    """
    Rates games based on a reviewer opinion of the game
    :param session: the session used to make requests
    :type session: aiohttp.client.ClientSession
    :param reviewer: the reviewer the program needs to check
    :type reviewer: str
    :param length: how many reviewers there are in total
    :type length: int
    """
    global index
    async with session.get(reviewer, headers=HEADERS_GET) as response:
        html = await response.text()
        reviews = [str(i) for i in BeautifulSoup(html, 'html.parser').find_all(attrs={'class': 'review_stats'})]
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


async def prog_games_rating():
    """
    Rates according to every single reviewer the program gathered
    """
    global index
    global calculated
    reviewers_urls = await get_reviewers_to_check()
    index = 0

    async with aiohttp.ClientSession() as session:
        tasks = []
        for reviewer in reviewers_urls:
            task = asyncio.ensure_future(rate(session, reviewer, len(reviewers_urls)))
            tasks.append(task)
        await asyncio.gather(*tasks)

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


def user_games_rating():
    """
    Manages all the user interaction: asking the user for his opinion about every game
    """
    global user_scores, calculated
    done = 0
    for game in games:
        rating = input(f"What do you think about {game} from 1 to 5? (ENTER if you didn't play, q to quit) ").lower()
        while (rating != "q" and rating != '' and not rating.isnumeric()) or (
                rating.isnumeric() and (int(rating) < 1 or int(rating) > 5)):
            print("THIS ISN'T A VALID ANSWER")
            rating = input(f"What do you think about {game} from 1 to 5? (ENTER if you didn't play) ")
        if rating == 'q':
            break
        if rating != '':
            user_scores[game] = rating
            if game in prog_scores:
                del prog_scores[game]
            done += 1
        games.remove(game)
        if done == 5:
            break
    calculated = False
    clear_score()


def add_manually():
    """
    Adding a game manually - the user gives the name of the game and his rating
    """
    global user_scores, calculated
    session = requests.Session()
    game = input("whats the name of the game? ENTER to main menu\n")
    while game != '':
        rating = input("how much do u rate the game from 1 to 5\n")

        while (rating != '' and not rating.isnumeric()) or (
                rating.isnumeric() and (int(rating) < 1 or int(rating) > 5)):
            print("INVALID INPUT")
            rating = input("how much do u rate the game from 1 to 5\n")

        urls = asyncio.get_event_loop().run_until_complete(get_platforms(game, True))
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
            print(urls[i])
            req = session.get(urls[i], headers=HEADERS_GET)
            soup = BeautifulSoup(req.text, 'html.parser')
            name = soup.find(name="div", attrs={'class': 'product_title'}).a.text.strip()
            user_scores[name] = rating
            if game in prog_scores:
                del prog_scores[game]
            if game in games:
                games.remove(game)
            calculated = False
        else:
            print(ans)
        game = input("whats the name of the game? ENTER to main menu\n")
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
                asyncio.get_event_loop().run_until_complete(prog_games_rating())
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
    print(start_msg)
    data = saveManager.read()

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
