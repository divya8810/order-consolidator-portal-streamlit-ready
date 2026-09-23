from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from backend.config import Config
from backend.models import db

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "frontend" / "templates"),
        static_folder=str(BASE_DIR / "frontend" / "static"),
    )
    app.config.from_object(config_class)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["OUTPUT_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from backend.routes import bp as main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
