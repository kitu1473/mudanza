import re
from typing import List, Tuple

from posting_app.database import Posting

# (label, regex) — matched against title + description, case-insensitive.
BONUSES = [
    (
        'Aire acondicionado',
        r'aire\s+acondicionado|\ba\s*/\s*a\b|\bsplit\b|climatizad',
    ),
    (
        'Cochera',
        r'cochera|garage|garaje',
    ),
    (
        'Dueño directo',
        r'due[ñn]o\s+directo|directo\s+(?:de\s+)?due[ñn]o|de\s+due[ñn]o'
        r'|due[ñn]o\s+alquila|alquila\s+due[ñn]o|sin\s+inmobiliaria'
        r'|sin\s+comisi[oó]n|propietario\s+directo',
    ),
]
_COMPILED = [(label, re.compile(rx, re.I)) for label, rx in BONUSES]


def get_bonuses(posting: Posting) -> List[str]:
    text = f'{posting.title or ""} {posting.description or ""}'
    return [label for label, rx in _COMPILED if rx.search(text)]


def sort_by_priority(postings: List[Posting]) -> List[Posting]:
    '''Postings with more bonuses first; keeps original order otherwise.'''
    return sorted(postings, key=lambda p: -len(get_bonuses(p)))


def format_bonus_line(posting: Posting) -> Tuple[str, int]:
    bonuses = get_bonuses(posting)
    if not bonuses:
        return '', 0
    return '⭐ ' + ' · '.join(bonuses) + '\n', len(bonuses)
