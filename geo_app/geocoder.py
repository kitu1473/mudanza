import time
from typing import Callable, Optional, Tuple

import requests
from rich.console import Console

console = Console()

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
# Nominatim's usage policy: identify the app and max 1 request per second
USER_AGENT = 'mudanza-bot/1.0 (personal apartment search)'
MIN_INTERVAL = 1.1
# Rough bounding box of CABA, to discard homonymous streets elsewhere
CABA_BOX = (-58.54, -34.71, -58.33, -34.52)  # lon_min, lat_min, lon_max, lat_max

Coords = Tuple[float, float]


def _nominatim_fetch(query: str) -> Optional[Coords]:
    res = requests.get(
        NOMINATIM_URL,
        params={
            'q': query,
            'format': 'jsonv2',
            'limit': 1,
            'countrycodes': 'ar',
            'viewbox': '{},{},{},{}'.format(
                CABA_BOX[0], CABA_BOX[3], CABA_BOX[2], CABA_BOX[1]
            ),
            'bounded': 1,
        },
        headers={'User-Agent': USER_AGENT},
        timeout=15,
    )
    res.raise_for_status()
    data = res.json()
    if not data:
        return None
    return float(data[0]['lat']), float(data[0]['lon'])


class Geocoder:
    '''
    Geocodes the free-text `location` of a posting.

    Tries the full address first ('exact'); if that fails, falls back to the
    last comma-separated part that is a neighbourhood ('approx').
    `fetch` is injectable for tests.
    '''

    def __init__(
        self,
        fetch: Callable[[str], Optional[Coords]] = _nominatim_fetch,
        interval: float = MIN_INTERVAL,
    ):
        self._fetch = fetch
        self._interval = interval
        self._last_call = 0.0
        self._cache = {}

    def _lookup(self, query: str) -> Optional[Coords]:
        if query in self._cache:
            return self._cache[query]
        wait = self._interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            result = self._fetch(query)
        except Exception as ex:
            console.log(f'Geocoding error for {query!r}: {ex!r}', style='red')
            return None  # transient: don't cache
        finally:
            self._last_call = time.monotonic()
        self._cache[query] = result
        return result

    def geocode(self, location: str) -> Tuple[Optional[Coords], Optional[str]]:
        parts = [p.strip() for p in (location or '').split(',') if p.strip()]
        if not parts:
            return None, None

        coords = self._lookup(', '.join(parts) + ', Buenos Aires, Argentina')
        if coords:
            return coords, 'exact' if any(c.isdigit() for c in parts[0]) else 'approx'

        # Fallback: neighbourhood only (usually the second part: "street, barrio, city")
        if len(parts) > 1:
            coords = self._lookup(f'{parts[1]}, Ciudad de Buenos Aires, Argentina')
            if coords:
                return coords, 'approx'
        return None, None
