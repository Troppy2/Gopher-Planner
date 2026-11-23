from flask_migrate import upgrade
from sqlalchemy import delete, select, func, text


def test_runtime_sqlite_enforces_user_deletion_cascades(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "synthetic-client")
    monkeypatch.setenv("JWT_SECRET", "synthetic-test-value")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'runtime.db').as_posix()}")
    from app import create_app
    from app.extensions import db
    from app.models import Plan, User

    application = create_app()
    with application.app_context():
        try:
            upgrade(directory="migrations")
            assert db.session.scalar(text("PRAGMA foreign_keys")) == 1
            user = User(google_sub="synthetic", email="synthetic@example.invalid")
            db.session.add(user)
            db.session.flush()
            db.session.add(Plan(user_id=user.id))
            db.session.commit()
            db.session.execute(delete(User).where(User.id == user.id))
            db.session.commit()
            assert db.session.scalar(select(func.count()).select_from(Plan)) == 0
        finally:
            db.session.remove()
            db.engine.dispose()
