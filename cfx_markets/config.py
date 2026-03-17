import json
import os
from importlib import resources as impresources

DEFAULT_CONFIG_FILE = "config.json"
USER_CONFIG_FILE = os.path.expanduser("~/cfx_client/config.json")


def load_config():
    """Loads configuration with user overrides."""
    conf = {}

    # Load default configuration from the package
    try:
        with impresources.open_text("cfx_markets", DEFAULT_CONFIG_FILE) as f:
            conf = json.load(f)
    except FileNotFoundError:
        conf = {}

    # Check if the user has a custom config file
    if os.path.exists(USER_CONFIG_FILE):
        with open(USER_CONFIG_FILE, "r") as f:
            user_config = json.load(f)
            conf = user_config

    return conf


# Load configuration at import time
conf = load_config()

AWS_CLIENT_ID = conf.get("AWS_CLIENT_ID", "default_client_id")
AWS_COGNITO_URL = conf.get("AWS_COGNITO_URL", "default_cognito_url")
