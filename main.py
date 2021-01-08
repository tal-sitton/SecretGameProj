import requests
from bs4 import BeautifulSoup

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}

scores = {}


def get_default_games():
    req = requests.get("https://www.metacritic.com/browse/games/score/metascore/all/all/filtered", headers=HEADERS_GET)
    soup = BeautifulSoup(req.text, 'html.parser')
    games = soup.find_all(name='a', attrs={'class': 'title'})
    games = [g.text for g in games]
    noDupGames = []
    [noDupGames.append(a) for a in games if a not in noDupGames]
    return noDupGames


def games_rating(games):
    done = 0
    for i in games:
        rating = input(f"What do you think about {i} from 1 to 5? (ENTER if you didn't play) ")
        while rating!='' or not rating.isnumeric or (5 < int(rating) or int(rating) < 1):
            print("THIS ISN'T A VALID ANSWER")
            rating = int(input(f"What do you think about {i} from 1 to 5? (ENTER if you didn't play)"))
        if rating != -1:
            scores[i] = rating
            done += 1
        if done == 5:
            break
    print(scores)


def main():
    start_msg = """    Hello, This Program will help find whats your next game will be.
    you just have to answer some questions about some games, and I will calculate whats your next ga,e should be
    Just know that the more questions you answer, the more accurate my calculation will be
    """
    print(start_msg)
    games = get_default_games()
    games_rating(games)
    pass


if __name__ == '__main__':
    main()
