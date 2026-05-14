from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, db: Session, model: type[ModelT]) -> None:
        self.db = db
        self.model = model

    def get_by_id(self, id_: UUID) -> ModelT | None:
        return self.db.get(self.model, id_)

    # Raw SQL, if ever needed, must use SQLAlchemy parameter binding.
