"""
A module for communicating with the igdb api
"""

import base64
import json
import requests
from functools import lru_cache

from hidden import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET

TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"
IGDB_GAMES_URL = "https://api.igdb.com/v4/games"


def get_igdb_access_token() -> str:
    """
    Returns the access token to the api
    """
    response = requests.post(
        f"{TWITCH_AUTH_URL}?client_id={TWITCH_CLIENT_ID}&client_secret={TWITCH_CLIENT_SECRET}&grant_type=client_credentials")
    return json.loads(response.text)["access_token"]


def get_game_image_url(game: str) -> str:
    """
    Returns the cover url for the game
    """
    access_token = get_igdb_access_token()

    game_id_response = requests.post(
        IGDB_GAMES_URL,
        headers={
            "Client-ID": TWITCH_CLIENT_ID,
            "Authorization": f"Bearer {access_token}"
        },
        data=f"search \"{game}\"; fields cover.url;"
    )

    result, *_ = json.loads(game_id_response.text)
    return result["cover"]["url"].replace("t_thumb", "t_cover_big")


@lru_cache
def get_game_image(game: str) -> str:
    """
    Returns tha game image as base64
    """
    image_url = get_game_image_url(game)

    image_result = requests.get(f"https:{image_url}")
    
    image_bytes = b""
    for chunk in image_result:
        image_bytes += chunk

    return f"data:image/png;base64, {base64.b64encode(image_bytes).decode()}"
