"""Tables. One row per mission day; settings are key/value floats."""
from typing import Optional
from sqlmodel import Field, SQLModel


class Entry(SQLModel, table=True):
    __tablename__ = "entries"
    day: int = Field(primary_key=True)
    sleep: Optional[float] = None
    hr: Optional[float] = None
    bp: Optional[float] = None
    glu: Optional[float] = None
    temp: Optional[float] = None
    mood: Optional[float] = None
    ex: Optional[float] = None
    dose: Optional[float] = None
    complete: bool = False
    source: str = "manual"  # manual | suit | csv | seed


class Setting(SQLModel, table=True):
    __tablename__ = "settings"
    key: str = Field(primary_key=True)
    value: float
