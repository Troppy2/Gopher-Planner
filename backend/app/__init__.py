"""Flask application factory; never connect or modify schema at startup."""

import click
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import load_settings
from app.extensions.database import check_database, init_database


def create_app() -> Flask:
    settings = load_settings()
    app = Flask(__name__)
    app.config.update(
        APP_ENV=settings.app_env,
        ENABLE_DEV_STUDENT_API=settings.enable_dev_student_api,
    )
    init_database(app, settings.database_url)
    if settings.app_env == 'development' and settings.enable_dev_student_api:
        from app.api.v1.dev_student import blueprint
        app.register_blueprint(blueprint)

    @app.get('/api/v1/health')
    def health():
        # Liveness only; success does not imply a working database.
        return {'status': 'ok'}

    @app.cli.command('check-db')
    def check_db_command():
        """Verify PostgreSQL without creating or updating any tables."""
        try:
            check_database(app.extensions['database_engine'])
        except SQLAlchemyError:
            raise click.ClickException(
                'PostgreSQL connection failed. Check the local service and DATABASE_URL.'
            ) from None
        except ValueError as error:
            raise click.ClickException(str(error)) from None
        click.echo('PostgreSQL connection verified (version >= 15).')

    return app
