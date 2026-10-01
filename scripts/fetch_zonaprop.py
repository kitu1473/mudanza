'''
Guarda el HTML de una búsqueda de ZonaProp para poder revisar el parser.
Correr desde una PC con IP residencial (desde un datacenter Cloudflare bloquea).

  python scripts/fetch_zonaprop.py            # usa la 1ra URL de config.example.yaml
  python scripts/fetch_zonaprop.py <URL>

Guarda zonaprop_sample.html. Si cloudscraper recibe el challenge ("Just a
moment...") reintenta con un navegador real (pip install playwright &&
playwright install chromium).
'''
import sys

import cloudscraper
import yaml


def default_url():
    with open('config.example.yaml') as fh:
        return yaml.safe_load(fh)['zonaprop_full_url'][0]


def with_cloudscraper(url):
    res = cloudscraper.create_scraper().get(url, timeout=30)
    print(f'cloudscraper: HTTP {res.status_code}')
    return res.text if res.ok else None


def with_browser(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(10000)  # deja pasar el challenge
        html = page.content()
        browser.close()
    print(f'navegador: {len(html)} bytes')
    return html if 'Just a moment' not in html[:3000] else None


def main(argv):
    url = argv[0] if argv else default_url()
    html = with_cloudscraper(url)
    if not html:
        print('Probando con navegador...')
        html = with_browser(url)
    if not html:
        sys.exit('No se pudo obtener el HTML (bloqueado).')
    with open('zonaprop_sample.html', 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'OK: zonaprop_sample.html ({len(html)} bytes), tiene avisos: {"postingCard" in html}')


if __name__ == '__main__':
    main(sys.argv[1:])
