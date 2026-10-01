from typing import Optional, List

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


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


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
