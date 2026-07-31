from flask import Flask

from app.api.v1 import auth, data, email, logs, model


def register_blueprints(app: Flask) -> None:
    for blueprint in (auth.bp, data.bp, model.bp, email.bp, logs.bp):
        app.register_blueprint(blueprint)
