from typing import Set

from bs4 import BeautifulSoup

from .base import BaseParser
from posting_app.database import Posting, PostingRepository


class ArgenpropParser(BaseParser):
    base_info_class = 'listing__item'
    url_base = "https://www.argenprop.com"

    base_info_tag = "div"
    link_regex = "a.card"
    price_regex = "p.card__price"
    features_regex = "ul.card__main-features"
    expenses_regex = "p.card__expenses"
    agent_regex = "div.card__agent-description"
    info_regex = "p.card__info"
    location_regex = "p.card__address"
    title_regex = "h2.card__title, p.card__title--primary"

    def build_description(self, card) -> str:
        '''Features | expensas | who publishes | start of the ad text.'''
        parts = []
        for regex, limit in (
            (self.features_regex, None),
            (self.expenses_regex, None),
            (self.agent_regex, None),
            (self.info_regex, 160),
        ):
            node = card.select_one(regex)
            if node:
                text = self.sanitize_text(node.get_text())
                parts.append(text[:limit] if limit else text)
        return ' | '.join(parts)

    def extract_data(self) -> Set[Posting]:
        """Extracting data and returning list of objects"""
        postings = set()
        base_info_soaps = self.soup.find_all(
            self.base_info_tag, class_=self.base_info_class)

        for base_info_soap in base_info_soaps:
            link_container = base_info_soap.select_one(self.link_regex)
            price_container = base_info_soap.select_one(self.price_regex)
            location_container = base_info_soap.select_one(self.location_regex)
            title_container = base_info_soap.select_one(self.title_regex)

            # require link and title; description/location may be missing on listing page
            if not (link_container and title_container):
                continue

            href = "{}{}".format(self.url_base, link_container.get("href", ""))
            title = self.sanitize_text(title_container.get_text())
            sha = self.get_id(href)
            price = self.sanitize_text(price_container.get_text()) if price_container else ''
            location = (
                self.sanitize_text(location_container.get_text())
                if location_container else ''
            )
            description = self.build_description(base_info_soap)

            posting_repository = PostingRepository()
            if posting_repository.touch_if_exists(sha):
                continue

            new_posting = Posting(
                sha=sha,
                url=href,
                title=title,
                price=price,
                description=description,
                location=location,
            )
            postings.add(new_posting)

        return postings
