import datetime
import json
import os
from html import escape
from typing import List, Set

from posting_app.database import Posting
from telegram_app.priority import get_bonuses

TEMPLATE = '''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mudanza - mapa de avisos</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
html,body,#map{height:100%;margin:0}
#info{position:absolute;z-index:1000;top:10px;right:10px;background:#fffd;padding:6px 10px;
border-radius:6px;font:13px system-ui}
</style></head><body>
<div id="map"></div><div id="info">__COUNT__ avisos · actualizado __UPDATED__ · ⭐ prioridad · círculo punteado = ubicación aproximada</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const postings = __DATA__;
const map = L.map('map').setView([-34.62, -58.45], 12);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom: 19, attribution: '© OpenStreetMap'}).addTo(map);
const bounds = [];
for (const p of postings) {
  const color = p.bonuses.length ? '#d98e04' : '#2563eb';
  const m = L.circleMarker([p.lat, p.lon], {
    radius: 8, color, fillColor: color, fillOpacity: .6,
    dashArray: p.precision === 'approx' ? '3 3' : null
  }).addTo(map);
  m.bindPopup(
    (p.bonuses.length ? '⭐ ' + p.bonuses.join(' · ') + '<br>' : '') +
    '<a href="' + p.url + '" target="_blank" rel="noopener"><b>' + p.title + '</b></a><br>' +
    p.price + '<br>' + p.location + '<br><small>' + p.description + '</small>');
  bounds.push([p.lat, p.lon]);
}
if (bounds.length) map.fitBounds(bounds, {padding: [30, 30]});
</script></body></html>
'''


def load_discarded(path: str) -> Set[str]:
    '''URLs the user doesn't want on the map: one per line, '#' comments.'''
    if not path or not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8') as fh:
        lines = (line.strip() for line in fh)
        return {l.split('#')[0].strip() for l in lines if l and not l.startswith('#')}


def build_map_data(postings: List[Posting], discarded: Set[str]) -> List[dict]:
    return [
        {
            'url': p.url,
            'title': escape(p.title or ''),
            'price': escape(p.price or ''),
            'location': escape(p.location or ''),
            'description': escape(p.description or ''),
            'lat': p.lat,
            'lon': p.lon,
            'precision': p.geo_precision,
            'bonuses': get_bonuses(p),
        }
        for p in postings
        if p.url not in discarded
    ]


def write_map(
    postings: List[Posting],
    path: str,
    discarded: Set[str] = frozenset(),
    now: datetime.datetime = None,
) -> int:
    data = build_map_data(postings, discarded)
    now = now or datetime.datetime.utcnow()
    # '</' would let a title close the <script> tag
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    html = (
        TEMPLATE.replace('__DATA__', payload)
        .replace('__COUNT__', str(len(data)))
        .replace('__UPDATED__', now.strftime('%Y-%m-%d %H:%M UTC'))
    )
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    return len(data)
