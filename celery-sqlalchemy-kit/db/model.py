import uuid

from celery.schedules import crontab
from sqlalchemy import Column, String, JSON, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import as_declarative


@as_declarative()
class Base:
    __name__: str
    __mapper_args__ = {"eager_defaults": True}

    def to_dict(self, exclude=None) -> dict:
        if not exclude:
            exclude = []
        return dict([(k, getattr(self, k)) for k in self.__dict__.keys() if not k.startswith("_") and k not in exclude])


class Routine(Base):
    __tablename__ = "routines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), index=True, nullable=False)
    task = Column(String(50), nullable=False)
    schedule = Column(JSON, nullable=False)
    last_run_at = Column(DateTime, index=True)
    total_run_count = Column(Integer, default=0)
    active = Column(Boolean, default=True, nullable=False)
    kwargs = Column(JSON)
    options = Column(JSON)

    @property
    def schedule_object(self):
        if "timedelta" in self.schedule:
            return self.schedule["timedelta"]
        minute = self.schedule["minute"] if "minute" in self.schedule else "*"
        hour = self.schedule["hour"] if "hour" in self.schedule else "*"
        day_of_week = self.schedule["day_of_week"] if "day_of_week" in self.schedule else "*"
        day_of_month = self.schedule["day_of_month"] if "day_of_month" in self.schedule else "*"
        month_of_year = self.schedule["month_of_year"] if "month_of_year" in self.schedule else "*"
        if all(x == "*" for x in [minute, hour, day_of_week, day_of_month, month_of_year]):
            raise TypeError("No schedule set.")
        return crontab(
            minute=minute,
            hour=hour,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
        )
