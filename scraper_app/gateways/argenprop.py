from .base import BaseGateway


class ArgenpropGateway(BaseGateway):
    def __init__(self):
        self._name = 'Argenprop'

    def page_url(self, url: str, page: int) -> str:
        if '{}' in url or page == 1:
            return super().page_url(url, page)
        separator = '&' if '?' in url else '?'
        return '{}{}pagina-{}'.format(url, separator, page)
