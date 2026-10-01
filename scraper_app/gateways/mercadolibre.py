from .base import BaseGateway

PAGE_SIZE = 48


class MercadolibreGateway(BaseGateway):
    def __init__(self):
        self._name = 'Mercadolibre'

    def page_url(self, url: str, page: int) -> str:
        # Page N is `_Desde_<offset>` placed before the filters segment:
        # .../villa-luro/_Desde_49_PriceRange_0ARS-1300000ARS_NoIndex_True
        if '{}' in url or page == 1:
            return super().page_url(url, page)
        head, slash, last = url.rpartition('/')
        if not last.startswith('_'):
            return url
        offset = (page - 1) * PAGE_SIZE + 1
        return f'{head}{slash}_Desde_{offset}{last}'
