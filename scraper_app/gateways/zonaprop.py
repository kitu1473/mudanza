from .base import BaseGateway


class ZonapropGateway(BaseGateway):
    def __init__(self):
        self._name = 'Zonaprop'

    def page_url(self, url: str, page: int) -> str:
        if '{}' in url or page == 1:
            return super().page_url(url, page)
        if url.endswith('.html'):
            return '{}-pagina-{}.html'.format(url[:-len('.html')], page)
        return url
