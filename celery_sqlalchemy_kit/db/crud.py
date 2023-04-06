from typing import List, Dict, Any, Type
from uuid import UUID, uuid4

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from . import Routine


class CRUDRoutine:
    def __init__(self, model: Type[Routine]) -> None:
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model
        self.model_name = model.__name__

    @staticmethod
    def get_multiple(
            db: Session, *, skip: int = 0, limit: int = 100, name: str = None, active: bool = None
    ) -> List[Routine]:
        """
        Find Routines in Database.
                        **Parameters**
        * `db`: Database Session
        * `skip`: How many rows should be skipped.
        * `limit`: Maximum number of returned Routines.
        * `name`: Filter search by name of Routine.
        * `active`: Filter search by active status. True = active, False = inactive
        """
        stmt = select(Routine)
        if name:
            stmt = stmt.where(Routine.name == name)
        if active:
            stmt = stmt.where(Routine.active == active)
        stmt = stmt.offset(skip).limit(limit).execution_options(populate_existing=True)
        result = db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    def find_by_name(db: Session, name: str) -> Routine:
        stmt = select(Routine)
        stmt = stmt.where(Routine.name == name)
        result = db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def create(db: Session, *, routine_in: Routine) -> None:
        """
        Create multiple Routines in Database.
        """
        db.add(routine_in)

    @staticmethod
    def create_multiple(db: Session, *, routines_in: List[Routine]) -> None:
        """
        Create multiple Routines in Database.
        """
        db.add_all(routines_in)

    def update(self, db: Session, *, db_obj: Routine, obj_in: Dict[str, Any]) -> Any:
        """
        Update routine in Database.
                **Parameters**

        * `db_obj`: Routine Database Object that should be updated.
        * `obj_in`: Updated Routine as dict.
        """
        obj_data = [a for a in dir(db_obj) if not a.startswith("_") and not callable(getattr(db_obj, a))]
        update_data = obj_in
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        return self.get_by_id(db, entry_id=db_obj.id)

    def get_by_id(self, db: Session, entry_id: UUID) -> Routine | None:
        stmt = select(self.model).where(self.model.id == entry_id).execution_options(populate_existing=True)
        result = db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def remove_by_name(db: Session, *, names: List[str]) -> None:
        """
        Delete routines by task names.
        """
        statement = delete(Routine).where(Routine.name.in_(names))
        db.execute(statement)

    @staticmethod
    def remove_all(db: Session) -> None:
        stmt = delete(Routine)
        db.execute(stmt)
        db.commit()

    @staticmethod
    def generate_uuid() -> UUID:
        return uuid4()


crud = CRUDRoutine(Routine)
