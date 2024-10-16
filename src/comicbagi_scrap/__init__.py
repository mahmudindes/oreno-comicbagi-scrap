import os
import dotenv
import logging
import comicking_scrap

from .bot import Bot
from .bot_mangadex import BotMangaDex

logging.basicConfig(level=logging.DEBUG)

def main():
    dotenv.load_dotenv()

    logger = logging.getLogger(__name__)
    note_file = open('bot.txt', 'a', encoding='utf-8')

    bot = Bot(
        os.getenv('COMICBAGI_SCRAP_BASE_COMICBAGI') or '',
        oauth_issuer=os.getenv('COMICBAGI_SCRAP_OAUTH_ISSUER') or '',
        oauth_client_id=os.getenv('COMICBAGI_SCRAP_OAUTH_CLIENT_ID') or '',
        oauth_client_secret=os.getenv('COMICBAGI_SCRAP_OAUTH_CLIENT_SECRET') or '',
        oauth_audience=os.getenv('COMICBAGI_SCRAP_OAUTH_AUDIENCE') or '',
        logger=logger,
        note_file=note_file
    )
    bot.load(True)

    bot_comicking = comicking_scrap.Bot(
        os.getenv('COMICBAGI_SCRAP_BASE_COMICKING') or '',
        oauth_issuer=os.getenv('COMICBAGI_SCRAP_OAUTH_ISSUER') or '',
        oauth_client_id=os.getenv('COMICBAGI_SCRAP_OAUTH_CLIENT_ID') or '',
        oauth_client_secret=os.getenv('COMICBAGI_SCRAP_OAUTH_CLIENT_SECRET') or '',
        oauth_audience=os.getenv('COMICBAGI_SCRAP_OAUTH_AUDIENCE') or '',
        logger=logger,
        note_file=note_file
    )
    bot_comicking.load(True)

    bot_comicking_jikan = comicking_scrap.BotJikan(
        bot_comicking,
        logger=logger
    )
    bot_comicking_jikan.load(True)

    bot_mangadex = BotMangaDex(
        bot,
        comicking_jikan_bot=bot_comicking_jikan,
        logger=logger
    )
    bot_mangadex.process(
        int(os.getenv('COMICBAGI_SCRAP_MAX_NEW_COMIC') or 1),
        int(os.getenv('COMICBAGI_SCRAP_MAX_NEW_COMIC_CHAPTER') or 10)
    )

    note_file.close()
