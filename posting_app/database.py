import datetime
from typing import Optional, List

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import (
    create_engine,
    Field,
    select,
    Session,
    SQLModel,
)
from sqlmodel.sql.expression import Select, SelectOfScalar

# Avoiding a warning. More info at: 
# https://github.com/tiangolo/sqlmodel/issues/189
SelectOfScalar.inherit_cache = True
Select.inherit_cache = True


class Posting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sha: str = Field(index=True, sa_column_kwargs={'unique': True})
    url: str = Field(sa_column_kwargs={'unique': True})
    title: Optional[str] = None
    price: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    sent: bool = Field(default=False, index=True)
    last_seen: Optional[datetime.datetime] = Field(
        default_factory=datetime.datetime.utcnow
    )
    lat: Optional[float] = None
    lon: Optional[float] = None
    # 'exact' (street address) | 'approx' (neighbourhood only)
    geo_precision: Optional[str] = None
    geo_failed: bool = False

    def __key(self):
        return (self.id, self.sha)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, Posting):
            return self.__key() == other.__key()
        return NotImplemented


DEFAULT_DB_PATH = 'scrapdep.db'

engine = create_engine(f'sqlite:///{DEFAULT_DB_PATH}')


def configure_engine(db_path: str):
    '''Points the repository at a different sqlite file.'''
    global engine
    engine = create_engine(f'sqlite:///{db_path}')


NEW_COLUMNS = {
    'last_seen': 'DATETIME',
    'lat': 'FLOAT',
    'lon': 'FLOAT',
    'geo_precision': 'VARCHAR',
    'geo_failed': 'BOOLEAN DEFAULT 0',
}


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # create_all doesn't add columns to existing tables: do it by hand so
    # databases created by older versions keep working.
    existing = {c['name'] for c in inspect(engine).get_columns('posting')}
    with engine.begin() as conn:
        for name, ddl in NEW_COLUMNS.items():
            if name not in existing:
                conn.execute(text(f'ALTER TABLE posting ADD COLUMN {name} {ddl}'))


class PostingRepository:
    def create_posting(self, posting: Posting) -> bool:
        '''Saves the posting. Returns False if its sha/url already exists.'''
        with Session(engine) as session:
            session.add(posting)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False
        return True

    def get_posting_by_sha(self, sha: str) -> Optional[Posting]:
        with Session(engine) as session:
            statement = select(Posting).where(Posting.sha == sha)
            posting = session.exec(statement).first()

            return posting
    
    def get_unsent_postings(self) -> List[Posting]:
        with Session(engine) as session:
            statement = select(Posting).where(Posting.sent == False)
            postings = [
                posting for posting
                in session.exec(statement)
            ]

            return postings

    def set_posting_as_sent(self, sha: str):
        with Session(engine) as session:
            statement = select(Posting).where(Posting.sha == sha)
            posting = session.exec(statement).first()
            posting.sent = True
            session.add(posting)
            session.commit()

    def touch_if_exists(self, sha: str) -> bool:
        '''Refreshes last_seen of a known posting. True if it existed.'''
        with Session(engine) as session:
            posting = session.exec(
                select(Posting).where(Posting.sha == sha)
            ).first()
            if not posting:
                return False
            posting.last_seen = datetime.datetime.utcnow()
            session.add(posting)
            session.commit()
            return True

    def get_postings_to_geocode(self, limit: int) -> List[Posting]:
        with Session(engine) as session:
            statement = (
                select(Posting)
                .where(Posting.lat == None, Posting.geo_failed == False)  # noqa: E711,E712
                .order_by(Posting.id.desc())
                .limit(limit)
            )
            return list(session.exec(statement))

    def set_geocode(self, sha: str, lat, lon, precision):
        '''Stores coordinates; lat=None marks the posting as not geocodable.'''
        with Session(engine) as session:
            posting = session.exec(
                select(Posting).where(Posting.sha == sha)
            ).first()
            if lat is None:
                posting.geo_failed = True
            else:
                posting.lat, posting.lon, posting.geo_precision = lat, lon, precision
            session.add(posting)
            session.commit()

    def get_postings_seen_since(self, since: datetime.datetime) -> List[Posting]:
        with Session(engine) as session:
            statement = select(Posting).where(
                Posting.lat != None,  # noqa: E711
                Posting.last_seen >= since,
            )
            return list(session.exec(statement))
