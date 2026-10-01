import time
from typing import List, Optional, Union

from rich.console import Console

from .gateways import (
    ArgenpropGateway,
    BaseGateway,
    LaVozGateway,
    MercadolibreGateway,
    ProperatiGateway,
    ZonapropGateway,
)
from .parsers import (
    ArgenpropParser,
    BaseParser,
    LaVozParser,
    MercadolibreParser,
    ProperatiParser,
    ZonapropParser,
)
from posting_app.database import Posting

console = Console()


def as_url_list(urls: Union[str, List[str], None]) -> List[str]:
    '''Accepts a single URL or a list of URLs and always returns a list.'''
    if not urls:
        return []
    if isinstance(urls, str):
        return [urls]
    return [url for url in urls if url]


class ScraperService:
    def __init__(
        self,
        pages: int,
        urls: Union[str, List[str]],
        gateway: BaseGateway,
        parser: BaseParser,
        request_delay: float = 0,
    ):
        self._pages = pages
        self._urls = as_url_list(urls)
        self._gateway = gateway
        self._parser = parser
        self._request_delay = request_delay

    def get_postings_from_scraper(self) -> List[Posting]:
        # Postings hash by sha, so the same listing found through
        # different URLs is kept only once.
        postings = set()
        pages = self._pages if self._gateway.paginated else 1
        first_request = True

        for url_index, url in enumerate(self._urls, start=1):
            console.log(f'URL {url_index} of {len(self._urls)}')
            for page in range(1, pages + 1):
                console.log(f'Page {page} of {pages}')
                if not first_request and self._request_delay:
                    time.sleep(self._request_delay)
                first_request = False

                html = self._gateway.make_request(
                    url=self._gateway.page_url(url, page)
                )
                if not html:
                    # Blocked or failed: deeper pages won't work either
                    break

                self._parser.get_soup_object(html=html)
                new_postings = self._parser.extract_data()
                console.log(f'Got {len(new_postings)} new postings')

                postings = postings.union(new_postings)

        return postings


class ScraperServiceFactory:
    @classmethod
    def build_for_zonaprop(
        cls,
        pages: int,
        full_url: Union[str, List[str]],
        request_delay: float = 0,
    ) -> ScraperService:
        return ScraperService(
            pages=pages,
            urls=full_url,
            request_delay=request_delay,
            gateway=ZonapropGateway(),
            parser=ZonapropParser(),
        )

    @classmethod
    def build_for_argenprop(
        cls,
        pages: int,
        full_url: Union[str, List[str]],
        request_delay: float = 0,
    ) -> ScraperService:
        return ScraperService(
            pages=pages,
            urls=full_url,
            request_delay=request_delay,
            gateway=ArgenpropGateway(),
            parser=ArgenpropParser(),
        )

    @classmethod
    def build_for_mercadolibre(
        cls,
        pages: int,
        full_url: Union[str, List[str]],
        request_delay: float = 0,
    ) -> ScraperService:
        return ScraperService(
            pages=pages,
            urls=full_url,
            request_delay=request_delay,
            gateway=MercadolibreGateway(),
            parser=MercadolibreParser(),
        )

    @classmethod
    def build_for_la_voz(
        cls,
        pages: int,
        full_url: Union[str, List[str]],
        request_delay: float = 0,
    ) -> ScraperService:
        return ScraperService(
            pages=pages,
            urls=full_url,
            request_delay=request_delay,
            gateway=LaVozGateway(),
            parser=LaVozParser(),
        )

    @classmethod
    def build_for_properati(
        cls,
        pages: int,
        full_url: Union[str, List[str]],
        request_delay: float = 0,
    ) -> ScraperService:
        return ScraperService(
            pages=pages,
            urls=full_url,
            request_delay=request_delay,
            gateway=ProperatiGateway(),
            parser=ProperatiParser(),
        )
