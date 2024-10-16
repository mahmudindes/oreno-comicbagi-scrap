import time
import logging
import comicbagi_openapi
import mangadex_openapi
import comicking_scrap
from datetime import datetime
from typing import Iterable
from urllib.parse import quote

from .bot import Bot

class BotMangaDex:
    website_mangadex_host = 'mangadex.org'

    def __init__(
        self,
        bot: Bot,
        comicking_jikan_bot: comicking_scrap.BotJikan | None,
        logger: logging.Logger
    ):
        from mangadex_openapi.api_client import ApiClient as MangaDexApiClient

        self.bot = bot
        self.client = MangaDexApiClient()

        self.comicking_jikan_bot = comicking_jikan_bot

        self.item_languages: list[str] = []

        self.logger = logger

    def load(self, seeding: bool = True):
        if seeding:
            self.bot.authenticate()

        #
        # Website
        #

        api0 = comicbagi_openapi.WebsiteApi(self.bot.client)

        if self.website_mangadex_host not in self.bot.websites:
            try:
                api0.get_website(self.website_mangadex_host)

                self.bot.websites.append(self.website_mangadex_host)
            except comicbagi_openapi.ApiException as e:
                if seeding and e.status == 404:
                    self.bot.add_website(self.website_mangadex_host, 'MangaDex')

                    time.sleep(2)
                else:
                    raise e

        item_language_page = 1
        while True:
            response0 = api0.list_website_item_language_with_http_info(
                self.website_mangadex_host,
                page=item_language_page,
                limit=15
            )

            if not response0.data:
                break

            for item_language in response0.data:
                self.item_languages.append(item_language.language_lang)

            item_language_total_count = 0

            if response0.headers:
                for k, v in response0.headers.items():
                    if k.lower() == 'x-total-count':
                        item_language_total_count = int(v)
                        break

            if len(self.item_languages) >= item_language_total_count:
                break

            time.sleep(1)
            item_language_page += 1

        if seeding:
            item_languages = {
                self.bot.language_english_lang: 0,
                self.bot.language_indonesian_lang: 0
            }
            for k, v in item_languages.items():
                if k in self.item_languages:
                    continue

                self.bot.add_website_item_language(
                    self.website_mangadex_host,
                    k,
                    v
                )

                self.item_languages.append(k)

                time.sleep(2)

    def note(self, __lines: Iterable[str] | None = None):
        if __lines:
            self.logger.info(__lines)
            if self.bot.note_file: self.bot.note_file.writelines(__lines)

        if self.bot.note_file: self.bot.note_file.writelines("\n")

    def process(self, max_new_comic: int | None = None, max_new_comic_chapter: int | None = None):
        self.note('#')
        self.note('# Started time %s' % time.ctime())
        self.note('#')
        self.note()

        self.load(True)

        self.scrap_comics_complete(max_new_comic, max_new_comic_chapter)

        self.note()
        self.note('# Stopped time %s' % time.ctime())
        self.note()

    def __manga(self, manga: mangadex_openapi.Manga):
        comic_code, comic_exist = None, False

        if not manga.id:
            return comic_code, comic_exist

        api0 = comicbagi_openapi.ComicApi(self.bot.client)

        response0 = api0.list_comic(
            destination_link=[quote(f'linkHREF={self.website_mangadex_host}/title/{manga.id}')]
        )

        self.bot.authenticate()

        # Comic

        api1 = comicbagi_openapi.LinkApi(self.bot.client)

        if len(response0) < 1:
            manga_attributes = manga.attributes

            if not manga_attributes:
                return comic_code, comic_exist

            if manga_attributes.links:
                for k, v in manga_attributes.links.items():
                    if comic_code:
                        break

                    match k:
                        case 'mal':
                            self.note('=== ComicKing Scrap ===')

                            if not self.comicking_jikan_bot:
                                continue

                            comic_code = self.comicking_jikan_bot.get_or_add_comic_complete(int(v))

                            self.note('=== ComicKing Scrap ===')

                            time.sleep(3)
                        case _:
                            continue

            if not comic_code:
                return comic_code, comic_exist

            try:
                api0.get_comic(comic_code)
            except comicbagi_openapi.ApiException as e:
                if e.status == 404:
                    self.bot.add_comic(comic_code)

                    time.sleep(2)
                else:
                    raise e

            # Comic Destinaton Link

            comic_link = f'{self.website_mangadex_host}/title/{manga.id}'

            try:
                api1.get_link(comic_link)
            except comicbagi_openapi.ApiException as e:
                if e.status == 404:
                    self.bot.add_link(self.website_mangadex_host, f'/title/{manga.id}')

                    time.sleep(2)
                else:
                    raise e

            if manga_attributes.available_translated_languages:
                for comic_link_item_language in manga_attributes.available_translated_languages:
                    if comic_link_item_language not in self.item_languages:
                        continue

                    try:
                        api1.get_link_item_language(comic_link, comic_link_item_language)
                    except comicbagi_openapi.ApiException as e:
                        if e.status == 404:
                            self.bot.add_link_item_language(
                                comic_link,
                                comic_link_item_language,
                                machine_translate=0
                            )

                            time.sleep(2)
                        else:
                            raise e

            response02 = api0.list_comic_destination_link(
                comic_code,
                link_href=[quote(comic_link)]
            )
            if len(response02) < 1:
                comic_released_at = datetime.now()

                if manga_attributes.created_at:
                    comic_released_at = datetime.fromisoformat(manga_attributes.created_at)

                self.bot.add_comic_destinaton_link(
                    comic_code,
                    self.website_mangadex_host,
                    f'/title/{manga.id}',
                    comic_released_at
                )

                time.sleep(2)
        else:
            if len(response0) > 1:
                self.note('Detected multiple comic with same MangaDex ID %s' % manga.id)

            comic_code, comic_exist = response0[0].code, True

        return comic_code, comic_exist

    def __manga_chapter(self, comic_code: str, chapter: mangadex_openapi.Chapter):
        chapter_nv, chapter_exist = None, False

        chapter_attributes = chapter.attributes

        if not chapter.id or not chapter_attributes or not chapter_attributes.chapter:
            return chapter_nv, chapter_exist

        api0 = comicbagi_openapi.ComicChapterApi(self.bot.client)

        # Chapter

        chapter_number = float(chapter_attributes.chapter)
        try:
            chapter_number = int(chapter_attributes.chapter)
        except ValueError:
            pass

        if f'{comic_code} {chapter_number}' not in self.bot.comic_chapters:
            try:
                api0.get_comic_chapter(comic_code, str(chapter_number))

                self.bot.comic_chapters.append(f'{comic_code} {chapter_number}')

                chapter_exist = True
            except comicbagi_openapi.ApiException as e:
                if e.status == 404:
                    self.bot.add_comic_chapter(
                        comic_code,
                        chapter_number,
                        None
                    )

                    time.sleep(2)
                else:
                    raise e

        chapter_nv = str(chapter_number)

        # Chapter Destination Link

        if chapter_attributes.translated_language not in self.item_languages:
            return chapter_nv, chapter_exist

        api1 = comicbagi_openapi.LinkApi(self.bot.client)

        chapter_link = quote(f'{self.website_mangadex_host}/chapter/{chapter.id}')

        try:
            api1.get_link(chapter_link)
        except comicbagi_openapi.ApiException as e:
            if e.status == 404:
                self.bot.add_link(self.website_mangadex_host, f'/chapter/{chapter.id}')

                time.sleep(2)
            else:
                raise e

        try:
            api1.get_link_item_language(chapter_link, chapter_attributes.translated_language)
        except comicbagi_openapi.ApiException as e:
            if e.status == 404:
                self.bot.add_link_item_language(
                    chapter_link,
                    chapter_attributes.translated_language,
                    machine_translate=0
                )

                time.sleep(2)
            else:
                raise e

        response = api0.list_comic_chapter_destination_link(
            comic_code,
            chapter_nv,
            link_href=[quote(chapter_link)]
        )
        if len(response) < 1:
            chapter_released_at = datetime.now()

            if chapter_attributes.created_at:
                chapter_released_at = datetime.fromisoformat(chapter_attributes.created_at)

            self.bot.add_comic_chapter_destinaton_link(
                comic_code,
                chapter_nv,
                self.website_mangadex_host,
                f'/chapter/{chapter.id}',
                released_at=chapter_released_at
            )

            time.sleep(2)

        return chapter_nv, chapter_exist

    def scrap_comics_complete(self, max_comic: int | None = None, max_comic_chapter: int | None = None):
        api1 = mangadex_openapi.MangaApi(self.client)
        api2 = mangadex_openapi.MangaApi(self.client)

        total_comic = 0

        page = 1
        while True:
            if max_comic and total_comic > max_comic - 1:
                break

            response = api1.get_search_manga(
                limit=10,
                offset=(page-1)*10
            )
            if not response.data:
                break

            for manga in response.data:
                if max_comic and total_comic > max_comic - 1:
                    break

                if not manga.id:
                    continue

                self.note()
                self.note('Check MangaDex manga ID %s' % manga.id)

                comic_code, comic_exist = self.__manga(manga)

                if comic_code:
                    total_comic_chapter = 0

                    page1 = 1
                    while True:
                        if max_comic_chapter and total_comic_chapter > max_comic_chapter - 1:
                            break

                        response1 = api2.get_manga_id_feed(
                            manga.id,
                            limit=50,
                            offset=(page1-1)*50
                        )
                        if not response1.data:
                            break

                        for comic_chapter in response1.data:
                            if max_comic_chapter and total_comic_chapter > max_comic_chapter - 1:
                                break

                            if not comic_chapter.id:
                                continue

                            self.note('Check MangaDex chapter ID %s' % comic_chapter.id)

                            comic_chapter_nv, comic_chapter_exist = self.__manga_chapter(comic_code, comic_chapter)

                            self.note("MangaDex chapter ID %s check complete" % comic_chapter.id)

                            if comic_chapter_nv or not comic_chapter_exist:
                                total_comic_chapter += 1
                                time.sleep(5)

                        page1 += 1
                        time.sleep(3)

                self.note("MangaDex manga ID %s check complete" % manga.id)
                self.note()

                if comic_code and not comic_exist:
                    total_comic += 1
                    time.sleep(5)

            page += 1
            time.sleep(3)
