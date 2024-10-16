import time
import requests
import logging
import comicbagi_openapi
from datetime import datetime
from io import TextIOWrapper
from typing import Iterable

class Bot:
    language_english_lang = 'en'
    language_indonesian_lang = 'id'
    language_japanese_lang = 'ja'
    language_korean_lang = 'ko'
    language_chinese_lang = 'zh'

    def __init__(
        self,
        base_comicbagi: str,
        oauth_issuer: str,
        oauth_client_id: str,
        oauth_client_secret: str,
        oauth_audience: str,
        logger: logging.Logger,
        note_file: TextIOWrapper | None = None
    ):
        self.client = comicbagi_openapi.ApiClient(configuration=comicbagi_openapi.Configuration(host=base_comicbagi))

        self.oauth_issuer = oauth_issuer
        self.oauth_client_id = oauth_client_id
        self.oauth_client_secret = oauth_client_secret
        self.oauth_audience = oauth_audience
        self.oauth_token_expires = time.time()

        self.languages: list[str] = []
        self.websites: list[str] = []
        self.comic_chapters: list[str] = []

        self.logger = logger
        self.note_file = note_file

    def load(self, seeding: bool = True):
        if seeding:
            self.authenticate()

        #
        # Language
        #

        api0 = comicbagi_openapi.LanguageApi(self.client)

        language_page = 1
        while True:
            response = api0.list_language_with_http_info(page=language_page, limit=15)

            if not response.data:
                break

            for language in response.data:
                self.languages.append(language.lang)

            language_total_count = 0

            if response.headers:
                for k, v in response.headers.items():
                    if k.lower() == 'x-total-count':
                        language_total_count = int(v)
                        break

            if len(self.languages) >= language_total_count:
                break

            time.sleep(1)
            language_page += 1

        if seeding:
            languages = {
                self.language_english_lang: 'English',
                self.language_indonesian_lang: 'Indonesian',
                self.language_japanese_lang: 'Japanese',
                self.language_korean_lang: 'Korean',
                self.language_chinese_lang: 'Chinese'
            }
            for k, v in languages.items():
                if k in self.languages:
                    continue

                result = self.add_language(k, v)
                if not result:
                    continue

                time.sleep(2)

    def authenticate(self):
        if self.oauth_token_expires > time.time() + 300:
            return

        response = requests.post(
            f'{self.oauth_issuer}oauth/token',
            data={
                'grant_type': 'client_credentials',
                'client_id': self.oauth_client_id,
                'client_secret': self.oauth_client_secret,
                'audience': self.oauth_audience
            }
        )

        if not response.ok:
            raise RuntimeError('Bot authentication failed')

        token = response.json()

        config = self.client.configuration
        config.access_token = token['access_token']
        self.oauth_token_expires = time.time() + float(token['expires_in'])

        self.logger.info('ComicBagi Bot authenticated')

    def note(self, __lines: Iterable[str] | None = None):
        if __lines:
            self.logger.info(__lines)
            if self.note_file: self.note_file.writelines(__lines)

        if self.note_file: self.note_file.writelines("\n")

    def add_language(
        self,
        lang: str,
        name: str
    ):
        api = comicbagi_openapi.LanguageApi(self.client)

        result = api.add_language(
            new_language=comicbagi_openapi.NewLanguage(
                lang=lang,
                name=name
            )
        )

        if lang not in self.languages:
            self.languages.append(lang)

        self.logger.info('Language "%s" added', lang)

        return result

    def add_website(
        self,
        host: str,
        name: str
    ):
        api = comicbagi_openapi.WebsiteApi(self.client)

        result = api.add_website(
            new_website=comicbagi_openapi.NewWebsite(
                host=host,
                name=name
            )
        )

        if host not in self.websites:
            self.websites.append(host)

        self.logger.info('Website "%s" added', host)

        return result

    def add_website_item_language(
        self,
        website_host: str,
        language_lang: str,
        machine_translate: int | None = None
    ):
        api = comicbagi_openapi.WebsiteApi(self.client)

        result = api.add_website_item_language(
            website_host,
            new_website_item_language=comicbagi_openapi.NewWebsiteItemLanguage(
                languageLang=language_lang,
                machineTranslate=machine_translate
            )
        )

        self.logger.info(
            'Website "%s" Item Language "%s" added',
            website_host, language_lang
        )

        return result

    def add_link(
        self,
        website_host: str,
        relative_reference: str | None = None
    ):
        api = comicbagi_openapi.LinkApi(self.client)

        result = api.add_link(
            new_link=comicbagi_openapi.NewLink(
                websiteHost=website_host,
                relativeReference=relative_reference
            )
        )

        self.logger.info('Link "%s" added', f'{website_host}{relative_reference}')

        return result

    def add_link_item_language(
        self,
        link_href: str,
        language_lang: str,
        machine_translate: int | None = None
    ):
        api = comicbagi_openapi.LinkApi(self.client)

        result = api.add_link_item_language(
            link_href,
            new_link_item_language=comicbagi_openapi.NewLinkItemLanguage(
                languageLang=language_lang,
                machineTranslate=machine_translate
            )
        )

        self.logger.info(
            'Link "%s" Item Language "%s" added',
            link_href, language_lang
        )

        return result

    def add_comic(
        self,
        code: str
    ):
        api = comicbagi_openapi.ComicApi(self.client)

        result = api.add_comic(
            new_comic=comicbagi_openapi.NewComic(
                code=code
            )
        )

        self.logger.info('Comic "%s" added', code)

        return result

    def add_comic_destinaton_link(
        self,
        comic_code: str,
        link_website_host: str,
        link_relative_reference: str | None = None,
        released_at: datetime | None = None
    ):
        api = comicbagi_openapi.ComicApi(self.client)

        result = api.add_comic_destination_link(
            comic_code,
            new_comic_destination_link=comicbagi_openapi.NewComicDestinationLink(
                linkWebsiteHost=link_website_host,
                linkRelativeReference=link_relative_reference,
                releasedAt=released_at
            )
        )

        self.logger.info(
            'Comic "%s" Destination Link "%s" added',
            comic_code, f'{link_website_host}{link_relative_reference}'
        )

        return result

    def add_comic_chapter(
        self,
        comic_code: str,
        number: float | int,
        version: str | None = None
    ):
        api = comicbagi_openapi.ComicChapterApi(self.client)

        result = api.add_comic_chapter(
            comic_code,
            new_comic_chapter=comicbagi_openapi.NewComicChapter(
                number=number,
                version=version
            )
        )

        if f'{comic_code} {number}{version or ""}' not in self.comic_chapters:
            self.comic_chapters.append(f'{comic_code} {number}{version or ""}')

        self.logger.info(
            'Comic "%s" Chapter "%s" added',
            comic_code, f'{number}{"+" + version if version else ""}'
        )

        return result

    def add_comic_chapter_destinaton_link(
        self,
        comic_code: str,
        chapter_nv: str,
        link_website_host: str,
        link_relative_reference: str | None = None,
        released_at: datetime | None = None
    ):
        api = comicbagi_openapi.ComicChapterApi(self.client)

        result = api.add_comic_chapter_destination_link(
            comic_code,
            chapter_nv,
            new_comic_chapter_destination_link=comicbagi_openapi.NewComicChapterDestinationLink(
                linkWebsiteHost=link_website_host,
                linkRelativeReference=link_relative_reference,
                releasedAt=released_at
            )
        )

        self.logger.info(
            'Comic "%s" Chapter "%s" Destination Link "%s" added',
            comic_code, chapter_nv, f'{link_website_host}{link_relative_reference}'
        )

        return result
