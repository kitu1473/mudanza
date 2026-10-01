from abc import ABC

import cloudscraper
from requests.exceptions import RequestException
from rich.console import Console

console = Console()


class BaseGateway(ABC):
    paginated = True

    def page_url(self, url: str, page: int) -> str:
        '''
        Returns the URL for the given page (1-indexed). URLs that contain
        a `{}` placeholder are formatted with the page number; otherwise
        each gateway appends its own pagination suffix.
        '''
        if '{}' in url:
            return url.format(page)
        return url

    def make_request(self, url: str) -> str:
        '''
        Makes the request to the full_url using cloudscraper
        and returns the html in it. Returns an empty string on any failure.
        '''
        console.log(
            'On my way to [bold cyan]GET[/bold cyan] [u]{}[/u]'.format(
                self._name
            )
        )

        try:
            scraper = cloudscraper.create_scraper()
            res = scraper.get(url, timeout=30)
        except RequestException as e:
            console.log(
                '[bold u]ERROR[/bold u]: {} request failed.\n {}'.format(
                    self._name, e
                ),
                style='red'
            )
            return ''

        if res.ok:
            if res.encoding in (None, 'ISO-8859-1'):
                # requests defaults to latin-1 when the header has no charset
                res.encoding = 'utf-8'
            console.log(
                '{} responded OK!'.format(self._name),
                style='green'
            )
            return res.text

        console.log(
            (
                '[bold u]ERROR[/bold u]: {} responded'
                ' with error [red bold]{}[/red bold]!'.format(
                    self._name, res.status_code
                )
            ),
            style='red'
        )
        return ''
