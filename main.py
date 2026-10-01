import datetime
import os

import yaml
from time import sleep
from typing import List, Optional, Union

import typer
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
from rich.console import Console
from rich.progress import track

from geo_app.geocoder import Geocoder
from geo_app.mapfile import load_discarded, write_map

from posting_app.database import (
    configure_engine,
    create_db_and_tables,
    PostingRepository,
)
from posting_app.services import PostingServiceFactory
from telegram_app.priority import sort_by_priority
from telegram_app.services import TelegramService

console = Console()


UrlSetting = Optional[Union[str, List[str]]]


class Config(BaseModel):
    pages: Optional[int] = 3
    # MercadoLibre has no pagination support: this only applies to the others
    sleep_time: Optional[int] = 5
    request_delay: Optional[float] = 1.5
    # Without bot_token/chat_room, falls back to the TELEGRAM_BOT_TOKEN /
    # TELEGRAM_CHAT_ID environment variables (used by GitHub Actions)
    bot_token: Optional[str] = None
    chat_room: Optional[str] = None
    persist: Optional[bool] = False
    # dry_run: scrape and print the messages, but don't send to Telegram
    # nor mark anything as sent.
    dry_run: Optional[bool] = False
    db_path: Optional[str] = 'scrapdep.db'
    # Map: geocode new postings (max `geocode_limit` per run, Nominatim is
    # 1 req/s) and regenerate a static HTML map with the recent ones.
    geocode: Optional[bool] = True
    geocode_limit: Optional[int] = 40
    map_output: Optional[str] = 'mapa.html'
    map_max_age_days: Optional[int] = 14  # not seen for longer => off the map
    discarded_file: Optional[str] = 'descartados.txt'  # URLs to hide, one per line
    zonaprop_base_url: Optional[str] = None
    zonaprop_full_url: UrlSetting = None
    argenprop_full_url: UrlSetting = None
    mercadolibre_full_url: UrlSetting = None
    la_voz_full_url: UrlSetting = None
    properati_full_url: UrlSetting = None


PORTALS = [
    ('zonaprop', 'build_for_zonaprop'),
    ('argenprop', 'build_for_argenprop'),
    ('mercadolibre', 'build_for_mercadolibre'),
    ('la_voz', 'build_for_la_voz'),
    ('properati', 'build_for_properati'),
]


def main(config_path: str):
    # LOAD CONFIG
    with open(config_path) as config_json:
        config_dict = yaml.safe_load(config_json)

    try:
        config = Config(**config_dict)
    except ValidationError as ex:
        console.log(
            '[bold u]ERROR[/bold u]: Config error.\n', ex, style='red'
        )
        return
    config.bot_token = config.bot_token or os.environ.get('TELEGRAM_BOT_TOKEN')
    config.chat_room = config.chat_room or os.environ.get('TELEGRAM_CHAT_ID')
    if not config.dry_run and not (config.bot_token and config.chat_room):
        console.log(
            '[bold u]ERROR[/bold u]: bot_token and chat_room are required '
            'unless dry_run is true.',
            style='red'
        )
        return
    # Environment overrides (used by the GitHub Actions workflow)
    if os.environ.get('PAGES'):
        config.pages = int(os.environ['PAGES'])
    if os.environ.get('DRY_RUN'):
        config.dry_run = os.environ['DRY_RUN'].lower() == 'true'
    if os.environ.get('DB_PATH'):
        config.db_path = os.environ['DB_PATH']
    console.log('Configuration read correctly', style='italic bold green')
    if config.dry_run:
        console.log('DRY RUN: nothing will be sent to Telegram', style='bold yellow')
    
    # LOAD DATABASE
    configure_engine(config.db_path)
    create_db_and_tables()
    console.log('Database loaded', style='italic bold green')

    while(True):
        # SCRAP POSTINGS
        for portal, builder_name in PORTALS:
            full_url = getattr(config, f'{portal}_full_url')
            if not full_url:
                continue
            try:
                service = getattr(PostingServiceFactory, builder_name)(
                    pages=config.pages,
                    full_url=full_url,
                    request_delay=config.request_delay,
                )
                service.scrap_and_create_postings()
            except Exception as ex:  # one broken portal must not stop the rest
                console.log(
                    f'[bold u]ERROR[/bold u]: {portal} failed: {ex!r}',
                    style='red'
                )

        console.log('Postings scrapped', style='italic bold green')

        # GEOCODE + MAP
        if config.geocode:
            geocoder = Geocoder()
            repository = PostingRepository()
            for posting in repository.get_postings_to_geocode(config.geocode_limit):
                coords, precision = geocoder.geocode(posting.location)
                repository.set_geocode(
                    posting.sha,
                    *(coords or (None, None)),
                    precision,
                )
        if config.map_output:
            since = datetime.datetime.utcnow() - datetime.timedelta(
                days=config.map_max_age_days
            )
            shown = write_map(
                PostingRepository().get_postings_seen_since(since),
                config.map_output,
                load_discarded(config.discarded_file),
            )
            console.log(f'Map written with {shown} postings: {config.map_output}')

        # SEND POSTINGS
        posting_repository = PostingRepository()
        unsent_postings = sort_by_priority(
            posting_repository.get_unsent_postings()
        )

        telegram_service = TelegramService(
            bot_token=config.bot_token,
            chat_room=config.chat_room,
        )
        console.log(f'About to send [u]{len(unsent_postings)}[/u] postings')
        if config.dry_run:
            for posting in unsent_postings:
                console.print(telegram_service.format_posting_to_message(posting))
                console.print('---')
            unsent_postings = []
        for posting in track(unsent_postings, description='Sending postings...'):
            # Try sending with automatic retries and backoff (respects Telegram's retry_after when detected)
            ok = telegram_service.send_with_retries(posting, max_retries=3, backoff_base=2)
            if ok:
                posting_repository.set_posting_as_sent(posting.sha)
            else:
                console.log(
                    (
                        '[bold u]WARNING[/bold u]: '
                        f'Unable to send {posting.title} after retries. '
                        'It will be retried later automatically.'
                    ),
                    style='yellow'
                )
        console.log('Postings sent', style='italic bold green')

        if not config.persist:
            break
        
        sleep(config.sleep_time)


if __name__ == '__main__':
    typer.run(main)