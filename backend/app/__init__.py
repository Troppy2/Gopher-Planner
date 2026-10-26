
from flask import Flask, app
from flask_cors import CORS

from app.api.v1.auth import auth_bp
from app.api.v1.courses import courses_bp
from app.api.v1.profile import profile_bp
from app.api.v1.transcripts import transcripts_bp
from app.core.config import Settings
from app.extensions import db, migrate
from app import models


def create_app() -> Flask:
    app = Flask(__name__)

    settings = Settings.from_env()
    app.config["SETTINGS"] = settings

    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    CORS(
        app,
        resources={r"/api/*": {"origins": settings.frontend_origin}},
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(transcripts_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
