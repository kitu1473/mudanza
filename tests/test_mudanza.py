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
    assert ProperatiGateway().page_url(p, 2) == p + '&page=2'
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
        'dry_run: true\nrequest_delay: 0\npages: 1\n'
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
