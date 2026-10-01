from .base import BaseGateway


class ProperatiGateway(BaseGateway):
    def __init__(self):
        self._name = 'Properati'

    def page_url(self, url: str, page: int) -> str:
        # Page N lives in the path: /s/alquiler/2?filters...
        if '{}' in url or page == 1:
            return super().page_url(url, page)
        path, sep, query = url.partition('?')
        return '{}/{}{}{}'.format(path.rstrip('/'), page, sep, query)
