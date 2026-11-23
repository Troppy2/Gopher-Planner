
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLiteConnection


@event.listens_for(Engine, "connect")
def enforce_sqlite_foreign_keys(connection, record):
    if isinstance(connection, SQLiteConnection):
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
        finally:
            cursor.close()


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
