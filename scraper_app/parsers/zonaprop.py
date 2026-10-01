from typing import Set

from .base import BaseParser
from posting_app.database import Posting, PostingRepository


class ZonapropParser(BaseParser):
    # Selectors match on class fragments, not on tags: ZonaProp has already
    # changed h2/h3/h4/div for the same elements.
    base_info_class = 'postingCardLayout-module__posting-card-container'
    base_info_tag = 'div'
    link_regex = '[class*="posting-description"] a'
    price_regex = '[class*="postingPrices-module__price"]:not([class*="container"])'
    expenses_regex = '[class*="postingPrices-module__expenses"]'
    description_regex = '[class*="posting-description"]'
    address_regex = '[class*="location-address"]'
    location_regex = '[class*="location-text"]'
    features_regex = '[class*="posting-main-features-span"]'
    _base_url = 'https://www.zonaprop.com.ar'

    def extract_data(self) -> Set[Posting]:
        '''Extracting data and returning list of postings'''
        postings = set()
        base_info_soaps = self.soup.find_all(
            self.base_info_tag, class_=self.base_info_class)

        for base_info_soap in base_info_soaps:
            link_container = base_info_soap.select_one(self.link_regex)
            price_container = base_info_soap.select_one(self.price_regex)
            expenses_container = base_info_soap.select_one(self.expenses_regex)
            description_container = base_info_soap.select_one(self.description_regex)
            address_container = base_info_soap.select_one(self.address_regex)
            location_container = base_info_soap.select_one(self.location_regex)

            if not (link_container and link_container.get('href')):
                continue

            # Drop the tracking query (?n_src=Listado&n_pos=...)
            href = self._base_url + link_container['href'].split('?')[0]
            sha = self.get_id(href)

            posting_repository = PostingRepository()
            if posting_repository.touch_if_exists(sha):
                continue

            long_description = (
                self.sanitize_text(description_container.get_text())
                if description_container else ''
            )
            title = long_description[:100]
            price = self.sanitize_text(price_container.get_text()) if price_container else ''

            # "Street al 1800" + "Barrio, Capital Federal": best input for geocoding
            location = ', '.join(
                self.sanitize_text(node.get_text())
                for node in (address_container, location_container)
                if node and node.get_text(strip=True)
            )

            parts = [
                self.sanitize_text(f.get_text())
                for f in base_info_soap.select(self.features_regex)
            ]
            if expenses_container:
                parts.append(self.sanitize_text(expenses_container.get_text()))
            parts.append(long_description[:160])
            description = ' | '.join(p for p in parts if p)

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
