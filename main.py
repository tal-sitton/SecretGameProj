import asyncio
import os

import aiohttp
import requests
from bs4 import BeautifulSoup
import saveManager

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}

user_scores = {}
prog_scores = {}
got_peoples_score = []
games = []
calculated = False


def assign_from_json(data):
    global user_scores, prog_scores, got_peoples_score, games, calculated
    user_scores = data['user_scores']
    prog_scores = data['prog_scores']
    got_peoples_score = data['got_peoples_score']
    games = data['games']
    calculated = data['calculated']


def get_default_games():
    global games
    req = requests.get("https://www.metacritic.com/browse/games/score/metascore/all/all/filtered", headers=HEADERS_GET)
    soup = BeautifulSoup(req.text, 'html.parser')
    names = soup.find_all(name='a', attrs={'class': 'title'})
    names = [g.text for g in names]
    noDupGames = []
    [noDupGames.append(a) for a in names if a not in noDupGames]
    games += noDupGames


async def platform_data(session: aiohttp.client.ClientSession, platform_url: str):
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


async def most_viewed_platform(urls: []):
    global platform
    reviews.clear()
    urls = urls[0:4]
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
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


async def get_platforms(game: str) -> str:
    req = requests.get(f'https://www.metacritic.com/search/game/{game}/results?sort=relevancy', headers=HEADERS_GET)
    soup = BeautifulSoup(req.text, 'html.parser')
    consoles = soup.find_all(name='a', href=True)
    consoles = [str(con) for con in consoles]

    urls = []
    for i in consoles:
        n = True
        if 'href="/game/' in i and "div" not in i and 'section' not in i:
            url = i.split('<a href="')[1].split('">')[0]
            for word in url.split('/')[3].replace("-", ' ').lower():
                if word not in game.lower():
                    n = False
                    break
            if n:
                urls.append('https://www.metacritic.com' + url)
    await most_viewed_platform(urls)
    return platform


async def get_reviewers_to_check():
    session = requests.Session()
    url_of_reviewers = []
    for game in user_scores:
        if game not in got_peoples_score:
            print(f"checking {game}")
            got_peoples_score.append(game)
            origin_url = await get_platforms(game)
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

            while reviewers_count < 10 and page / 2 < 10 and reviews:
                for review in reviews:
                    grade = BeautifulSoup(str(review), 'html.parser').find(attrs={'class': 'review_grade'}).text
                    if abs(int(user_scores[game]) * 2 - int(grade)) < 2:
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
                page += 2
                url = origin_url + f'&page={page}'
                req = session.get(url, headers=HEADERS_GET)
                soup = BeautifulSoup(req.text, 'html.parser')
                reviews = soup.find_all(attrs={'class': 'review user_review'})
            # print(reviewers_count)
            # print(origin_url)
    session.close()
    # print(url_of_reviewers)
    # print(len(url_of_reviewers))
    return url_of_reviewers


index = 0


async def do_rating(session: aiohttp.client.ClientSession, reviewer: str, length: int):
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
    global index
    global calculated
    reviewers_urls = await get_reviewers_to_check()
    index = 0

    async with aiohttp.ClientSession() as session:
        tasks = []
        for reviewer in reviewers_urls:
            task = asyncio.ensure_future(do_rating(session, reviewer, len(reviewers_urls)))
            tasks.append(task)
        await asyncio.gather(*tasks)

    clear_things()
    calculated = True


def clear_things():
    global prog_scores
    for game in user_scores:
        if game in prog_scores:
            del prog_scores[game]
        if game in games:
            games.remove(game)
    prog_scores = {k: v for k, v in sorted(prog_scores.items(), key=lambda item: -item[1])}


def user_games_rating():
    global user_scores, calculated
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
    calculated = False


def manager():
    manager_msg = "\n" * 100 + """\t\tNice! now that we all set up we can choose what you want to do! you can do 
            couple of things like 'score more games' , 'recommended games' , 'exit' and 'delete' to delete your 
            preferences and then exit\n\n\n\n """
    print(manager_msg)

    todo = ''

    while todo != 'exit':
        todo = input("what do you want to do? ")

        if todo == "score more games":
            user_games_rating()

        elif todo == "recommended games":
            if not calculated:
                asyncio.get_event_loop().run_until_complete(prog_games_rating())
            print(prog_scores)
            input("continue? press Enter")

        elif todo == "delete":
            if os.path.exists(saveManager.data):
                os.remove(saveManager.data)
            break

        saveManager.write(user_scores=user_scores, prog_scores=prog_scores, got_peoples_score=got_peoples_score,
                          games=games, calculated=calculated)
        print(
            "\n" * 100 + "\t\tyour options are: 'score more games' , 'recommended games' , 'exit' and 'delete' to "
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
