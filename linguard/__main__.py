import argparse
import atexit
import os
from logging import warning

from flask import Flask
from flask_login import LoginManager

from linguard.common.models.user import users
from linguard.core.config.web import config as web_config
from linguard.core.managers.config import config_manager
from linguard.core.managers.cron import cron_manager
from linguard.core.managers.wireguard import wireguard_manager
from linguard.web.router import router
from linguard.web.static.assets.resources import APP_NAME

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id, None)


parser = argparse.ArgumentParser(description="Welcome to Linguard, the best WireGuard's web GUI :)")
parser.add_argument("config", type=str, help="Path to the configuration file.")
parser.add_argument("--debug", help="Start flask in debug mode.", action="store_true")
args = parser.parse_args()

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
config_manager.load(os.path.abspath(args.config))
app.config['SECRET_KEY'] = web_config.secret_key
app.register_blueprint(router)
login_manager.init_app(app)
wireguard_manager.start()
cron_manager.start()


@atexit.register
def on_exit():
    warning(f"Shutting down {APP_NAME}...")
    cron_manager.stop()
    wireguard_manager.stop()


if __name__ == "__main__":
    warning("Running development server...")
    app.run(debug=args.debug, port=8080)