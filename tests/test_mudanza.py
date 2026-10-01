import pytest

from posting_app.database import (
    Posting, PostingRepository, configure_engine, create_db_and_tables,
)
from scraper_app.gateways import (
    ArgenpropGateway, ProperatiGateway, ZonapropGateway,
)
from scraper_app.parsers.base import BaseParser
from scraper_app.services import ScraperService, as_url_list
from telegram_app.priority import get_bonuses, sort_by_priority
from telegram_app.services import TelegramService
import main as main_module


class FakeGateway(ZonapropGateway):
    def __init__(self, pages_by_url):
        super().__init__()
        self.pages_by_url = pages_by_url
        self.requested = []

    def make_request(self, url):
        self.requested.append(url)
        return self.pages_by_url.get(url, '')


class FakeParser(BaseParser):
    def get_soup_object(self, html):
        self.html = html

    def extract_data(self):
        return {
            Posting(sha=sha, url=f'https://x/{sha}', title=sha)
            for sha in self.html.split(',') if sha
        }


def test_as_url_list():
    assert as_url_list(None) == []
    assert as_url_list('a') == ['a']
    assert as_url_list(['a', '', 'b']) == ['a', 'b']


def test_multiple_urls_are_deduplicated_by_sha():
    gw = FakeGateway({'u1': 'a,b', 'u2': 'b,c'})
    svc = ScraperService(pages=1, urls=['u1', 'u2'], gateway=gw, parser=FakeParser())
    found = svc.get_postings_from_scraper()
    assert sorted(p.sha for p in found) == ['a', 'b', 'c']
    assert gw.requested == ['u1', 'u2']


def test_failed_request_stops_paging_that_url_only():
    gw = FakeGateway({'u2.html': 'z'})
    svc = ScraperService(pages=3, urls=['u1.html', 'u2.html'], gateway=gw, parser=FakeParser())
    found = svc.get_postings_from_scraper()
    assert [p.sha for p in found] == ['z']
    assert gw.requested[0] == 'u1.html'          # u1 fails on page 1, no page 2
    assert gw.requested[1] == 'u2.html'


def test_page_urls():
    z = 'https://www.zonaprop.com.ar/x-orden-publicado-descendente.html'
    assert ZonapropGateway().page_url(z, 1) == z
    assert ZonapropGateway().page_url(z, 3).endswith('descendente-pagina-3.html')
    a = 'https://www.argenprop.com/x?con-ambiente-balcon&orden-masnuevos'
    assert ArgenpropGateway().page_url(a, 2).endswith('&pagina-2')
    assert ArgenpropGateway().page_url('https://a/x', 2) == 'https://a/x?pagina-2'
    p = 'https://www.properati.com.ar/s/alquiler?geos=1'
    assert ProperatiGateway().page_url(p, 1) == p
    assert ProperatiGateway().page_url(p, 2) == 'https://www.properati.com.ar/s/alquiler/2?geos=1'
    assert ZonapropGateway().page_url('https://a/b-pagina-{}.html', 4) == 'https://a/b-pagina-4.html'


def test_bonuses_and_sorting():
    plain = Posting(sha='1', url='u1', title='PH 2 amb', description='patio')
    ac = Posting(sha='2', url='u2', title='Depto con aire acondicionado')
    full = Posting(sha='3', url='u3', title='Casa', description='cochera, dueño directo, split')
    assert get_bonuses(plain) == []
    assert get_bonuses(ac) == ['Aire acondicionado']
    assert get_bonuses(full) == ['Aire acondicionado', 'Cochera', 'Dueño directo']
    assert [p.sha for p in sort_by_priority([plain, ac, full])] == ['3', '2', '1']


def test_message_has_bonus_line_first():
    msg = TelegramService('t', 'c').format_posting_to_message(
        Posting(sha='3', url='u', title='Casa con cochera'))
    assert msg.startswith('⭐ Cochera')


def test_repository_create_posting_ignores_duplicates(tmp_path):
    configure_engine(str(tmp_path / 't.db'))
    create_db_and_tables()
    repo = PostingRepository()
    assert repo.create_posting(Posting(sha='a', url='ua')) is True
    assert repo.create_posting(Posting(sha='a', url='ua')) is False


def test_dry_run_end_to_end(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / 'c.yaml'
    cfg.write_text(
        'dry_run: true\nrequest_delay: 0\npages: 1\ngeocode: false\nmap_output: ' + str(tmp_path / 'm.html') + '\n'
        f'db_path: {tmp_path}/d.db\n'
        'zonaprop_full_url:\n  - u1.html\n  - u2.html\n'
    )
    pages = {'u1.html': 'a,b', 'u2.html': 'b,c'}
    monkeypatch.setattr(ZonapropGateway, 'make_request', lambda self, url: pages.get(url, ''))
    from scraper_app.parsers import ZonapropParser
    monkeypatch.setattr(ZonapropParser, 'get_soup_object', FakeParser.get_soup_object)
    monkeypatch.setattr(ZonapropParser, 'extract_data', FakeParser.extract_data)
    monkeypatch.setattr(
        TelegramService, '_post_message',
        lambda *a, **k: pytest.fail('dry_run must not call Telegram'))

    main_module.main(str(cfg))
    configure_engine(str(tmp_path / 'd.db'))
    repo = PostingRepository()
    unsent = repo.get_unsent_postings()
    assert sorted(p.sha for p in unsent) == ['a', 'b', 'c']   # saved, still unsent


def test_geocoder_exact_then_approx_fallback():
    from geo_app.geocoder import Geocoder
    calls = []

    def fetch(q):
        calls.append(q)
        return (-34.6, -58.4) if q.startswith('Flores,') else None

    g = Geocoder(fetch=fetch, interval=0)
    coords, prec = g.geocode('Av. Rivadavia 7000, Flores, Capital Federal')
    assert coords == (-34.6, -58.4) and prec == 'approx'
    assert len(calls) == 2
    assert g.geocode('') == (None, None)


def test_geocoder_exact_when_street_number():
    from geo_app.geocoder import Geocoder
    g = Geocoder(fetch=lambda q: (1.0, 2.0), interval=0)
    assert g.geocode('Rivadavia 7000, Flores')[1] == 'exact'


def test_geocoder_error_is_not_cached():
    from geo_app.geocoder import Geocoder
    n = {'c': 0}

    def fetch(q):
        n['c'] += 1
        raise RuntimeError('boom')

    g = Geocoder(fetch=fetch, interval=0)
    assert g.geocode('A 1, B') == (None, None)
    g.geocode('A 1, B')
    assert n['c'] >= 4  # retried, nothing cached


def test_geocode_state_and_map(tmp_path):
    import datetime
    from geo_app.mapfile import load_discarded, write_map
    configure_engine(str(tmp_path / 'g.db'))
    create_db_and_tables()
    repo = PostingRepository()
    repo.create_posting(Posting(sha='a', url='ua', title='</script>x', location='L'))
    repo.create_posting(Posting(sha='b', url='ub', title='B', location='L'))
    repo.create_posting(Posting(sha='c', url='uc', title='C', location='L'))
    assert len(repo.get_postings_to_geocode(10)) == 3
    repo.set_geocode('a', -34.6, -58.4, 'exact')
    repo.set_geocode('b', -34.6, -58.4, 'approx')
    repo.set_geocode('c', None, None, None)
    assert repo.get_postings_to_geocode(10) == []          # c marked failed
    past = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    shown = repo.get_postings_seen_since(past)
    assert sorted(p.sha for p in shown) == ['a', 'b']       # c has no coords

    disc = tmp_path / 'd.txt'
    disc.write_text('# comment\nub  # no me gusto\n')
    assert load_discarded(str(disc)) == {'ub'}
    out = tmp_path / 'map.html'
    assert write_map(shown, str(out), load_discarded(str(disc))) == 1
    html = out.read_text()
    assert '</script>x' not in html and 'ub' not in html.split('const postings')[1].split(';')[0]


def test_touch_if_exists_refreshes_last_seen(tmp_path):
    import datetime
    configure_engine(str(tmp_path / 't2.db'))
    create_db_and_tables()
    repo = PostingRepository()
    old = datetime.datetime(2020, 1, 1)
    repo.create_posting(Posting(sha='a', url='ua', last_seen=old))
    assert repo.touch_if_exists('a') is True
    assert repo.touch_if_exists('zz') is False
    assert repo.get_postings_seen_since(old + datetime.timedelta(days=1)) == []  # no coords yet
    repo.set_geocode('a', 1.0, 2.0, 'exact')
    assert len(repo.get_postings_seen_since(old + datetime.timedelta(days=1))) == 1


def test_migration_adds_columns_to_old_db(tmp_path):
    import sqlite3
    db = tmp_path / 'old.db'
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE posting (id INTEGER PRIMARY KEY, sha VARCHAR, url VARCHAR, '
                'title VARCHAR, price VARCHAR, location VARCHAR, description VARCHAR, sent BOOLEAN)')
    con.execute("INSERT INTO posting (sha, url, sent) VALUES ('a', 'ua', 1)")
    con.commit(); con.close()
    configure_engine(str(db))
    create_db_and_tables()
    assert PostingRepository().get_posting_by_sha('a').geo_failed in (False, 0, None)


def test_mercadolibre_page_url():
    from scraper_app.gateways import MercadolibreGateway
    u = 'https://inmuebles.mercadolibre.com.ar/ph/alquiler/x-o-y/_PriceRange_0ARS-1300000ARS_NoIndex_True'
    g = MercadolibreGateway()
    assert g.page_url(u, 1) == u
    assert g.page_url(u, 2) == u.replace('/_Price', '/_Desde_49_Price')
    assert g.page_url(u, 3) == u.replace('/_Price', '/_Desde_97_Price')


FIXTURES = __import__('pathlib').Path(__file__).parent / 'fixtures'


@pytest.mark.parametrize('portal, parser_name, expected_host', [
    ('zonaprop', 'ZonapropParser', 'www.zonaprop.com.ar'),
    ('argenprop', 'ArgenpropParser', 'www.argenprop.com'),
    ('properati', 'ProperatiParser', 'www.properati.com.ar'),
])
def test_parsers_on_real_cards(tmp_path, portal, parser_name, expected_host):
    # Cards captured from the live sites (Oct 2026). If a portal changes its
    # HTML, refresh the fixture and fix the parser.
    import scraper_app.parsers as parsers
    configure_engine(str(tmp_path / f'{portal}.db'))
    create_db_and_tables()
    parser = getattr(parsers, parser_name)()
    parser.get_soup_object((FIXTURES / f'{portal}_cards.html').read_text(encoding='utf-8'))
    found = parser.extract_data()
    assert len(found) == 2
    for p in found:
        assert p.url.startswith(f'https://{expected_host}/') and '?' not in p.url
        assert p.title and p.price and p.location


def test_zonaprop_page_2_matches_real_site_url():
    # URL of page 2 copied from the real site
    base = ('https://www.zonaprop.com.ar/casas-departamentos-ph-alquiler-flores-con-balcon-'
            'desde-2-hasta-3-ambientes-menos-1300000-pesos-orden-publicado-descendente')
    gw = ZonapropGateway()
    assert gw.page_url(base + '.html', 2) == base + '-pagina-2.html'
