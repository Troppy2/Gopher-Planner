from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
import pytest

from tests.conftest import sqlite_only

from app.extensions import db
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext


def test_existing_users_survive_profile_migration(app):
    downgrade(directory="migrations", revision="dedead669720")
    db.session.execute(text("""
        INSERT INTO users (google_sub, email, created_at, updated_at)
        VALUES ('synthetic', 'synthetic@example.invalid', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """))
    db.session.commit()
    upgrade(directory="migrations")
    row = db.session.execute(text("SELECT credit_load, onboarded FROM users")).one()
    assert tuple(row) == (15, 0)


def test_migrations_upgrade_empty_database_and_downgrade_to_base(app):
    assert {"users", "user_sessions"} <= set(inspect(db.engine).get_table_names())
    downgrade(directory="migrations", revision="base")
    assert set(inspect(db.engine).get_table_names()) == {"alembic_version"}


def test_migrated_schema_has_no_model_drift(app):
    with db.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_server_default": True})
        assert compare_metadata(context, db.metadata) == []


def test_reports_revision_preserves_existing_accounts(app, make_user):
    user_id = make_user().id
    db.session.remove()
    downgrade(directory="migrations", revision="a1d4e7f93c20")
    assert "data_reports" not in inspect(db.engine).get_table_names()
    assert db.session.scalar(text("SELECT id FROM users")) == user_id
    db.session.remove()
    upgrade(directory="migrations")
    assert "data_reports" in inspect(db.engine).get_table_names()
    assert db.session.scalar(text("SELECT id FROM users")) == user_id


@sqlite_only
def test_sqlite_test_connections_enforce_foreign_keys(app):
    assert db.session.scalar(text("PRAGMA foreign_keys")) == 1


def test_unknown_term_index_upgrade_and_downgrade_preserve_populated_coursework(app, make_user):
    from app.models import Coursework

    user = make_user()
    values = dict(user_id=user.id, code="CSCI 1001", title="Synthetic course",
                  credits=3, status="done", term=None, source="manual")
    db.session.add(Coursework(**values))
    db.session.commit()
    before = db.session.execute(text("SELECT * FROM coursework")).all()
    db.session.remove()
    downgrade(directory="migrations", revision="cf8c0dfdbb15")
    assert "uq_coursework_user_code_unknown_term" not in {
        index["name"] for index in inspect(db.engine).get_indexes("coursework")
    }
    upgrade(directory="migrations")
    assert db.session.execute(text("SELECT * FROM coursework")).all() == before
    db.session.add(Coursework(**values))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert db.session.execute(text("SELECT * FROM coursework")).all() == before


def test_unknown_term_upgrade_stops_without_repairing_legacy_duplicates(app, make_user, capfd):
    from app.models import Coursework

    user_id = make_user().id
    db.session.remove()
    downgrade(directory="migrations", revision="cf8c0dfdbb15")
    values = dict(user_id=user_id, code="CSCI 1001", title="Synthetic course",
                  credits=3, status="done", term=None, source="manual")
    db.session.add_all([Coursework(**values), Coursework(**values)])
    db.session.commit()
    before = db.session.execute(text("SELECT * FROM coursework ORDER BY id")).all()
    db.session.remove()
    # Flask-Migrate translates migration RuntimeError into a CLI failure.
    with pytest.raises(SystemExit) as error:
        upgrade(directory="migrations")
    assert error.value.code == 1
    assert "require explicit data repair" in capfd.readouterr().err
    db.session.rollback()
    assert db.session.execute(text("SELECT * FROM coursework ORDER BY id")).all() == before
    assert db.session.scalar(text("SELECT version_num FROM alembic_version")) == "cf8c0dfdbb15"


def test_plan_catalog_term_migration_preserves_existing_plans_as_unconfirmed(app, make_user):
    user_id = make_user().id
    db.session.remove()
    downgrade(directory="migrations", revision="e4b7c2a91d06")
    assert "catalog_term" not in {column["name"] for column in inspect(db.engine).get_columns("plans")}
    db.session.execute(text("INSERT INTO plans (user_id, created_at, updated_at) VALUES (:user, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"),
                       {"user": user_id})
    db.session.commit()
    db.session.remove()
    upgrade(directory="migrations")
    assert db.session.execute(text("SELECT user_id, catalog_term FROM plans")).one() == (user_id, None)
    db.session.execute(text("UPDATE plans SET catalog_term = 'Fall 2026'"))
    db.session.commit()
    db.session.remove()
    downgrade(directory="migrations", revision="e4b7c2a91d06")
    assert db.session.execute(text("SELECT user_id FROM plans")).scalar() == user_id
    db.session.remove()
    upgrade(directory="migrations")
    assert db.session.execute(text("SELECT catalog_term FROM plans")).scalar() is None


def test_plan_model_persists_a_selected_catalog_term(app, make_user):
    from app.models import Plan

    plan = Plan(user_id=make_user().id, catalog_term="Fall 2026")
    db.session.add(plan)
    db.session.commit()
    assert db.session.execute(text("SELECT catalog_term FROM plans")).scalar() == "Fall 2026"


from tests.conftest import postgres_only  # noqa: E402


@postgres_only
def test_every_public_table_has_row_level_security(app):
    """Supabase's Data API must not reach application tables; the backend owns them and bypasses RLS."""
    unprotected = db.session.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND NOT rowsecurity")).scalars().all()
    assert unprotected == []
