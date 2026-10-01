from typing import Set

from .base import BaseParser
from posting_app.database import Posting, PostingRepository


class ProperatiParser(BaseParser):
    base_info_class = 'snippet'
    base_info_tag = 'article'
    link_regex = 'a.title'
    price_regex = 'div.price'
    location_regex = 'div.location'
    properties_regex = (
        'span[class*="properties__"], span[class*="amenity__"], '
        'span.agency__name'
    )
    _base_url = 'https://www.properati.com.ar'

    def extract_data(self) -> Set[Posting]:
        '''Extracting data and returning list of postings'''
        postings = set()
        base_info_soaps = self.soup.find_all(
            self.base_info_tag, class_=self.base_info_class)

        for base_info_soap in base_info_soaps:
            link_container = base_info_soap.select_one(self.link_regex)
            price_container = base_info_soap.select_one(self.price_regex)
            location_container = base_info_soap.select_one(self.location_regex)

            if not (link_container and link_container.get('href')):
                continue

            href = link_container['href']
            if href.startswith('/'):
                href = self._base_url + href
            title = self.sanitize_text(link_container.text)
            sha = self.get_id(href)
            price = (
                self.sanitize_text(price_container.text)
                if price_container else ''
            )
            location = (
                self.sanitize_text(location_container.text)
                if location_container else ''
            )
            description = ' | '.join(
                self.sanitize_text(node.text)
                for node in base_info_soap.select(self.properties_regex)
            )

            posting_repository = PostingRepository()
            if posting_repository.touch_if_exists(sha):
                continue

            new_posting = Posting(
                sha=sha,
                url=href,
                title=title,
                price=price,
                location=location,
                description=description,
            )
            postings.add(new_posting)

        return postings
