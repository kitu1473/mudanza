from .base import BaseGateway


class ProperatiGateway(BaseGateway):
    def __init__(self):
        self._name = 'Properati'

    def page_url(self, url: str, page: int) -> str:
        if '{}' in url or page == 1:
            return super().page_url(url, page)
        separator = '&' if '?' in url else '?'
        return '{}{}page={}'.format(url, separator, page)
