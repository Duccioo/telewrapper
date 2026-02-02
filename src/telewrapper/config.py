import argparse
import configparser
import os
import yaml

DEFAULT_UPDATE_INTERVAL = 5.0


def load_config():
    """Parses command line arguments and loads configuration files."""
    parser = argparse.ArgumentParser(description="Telegram Command Wrapper")
    parser.add_argument(
        "command", nargs="?", help="Il comando da eseguire (tra virgolette)"
    )
    parser.add_argument("--token", help="Bot Token Telegram")
    parser.add_argument("--chat_id", help="Chat ID Telegram")
    parser.add_argument("--config", help="Path al file di config")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Esegui un test di connessione e funzionalità",
    )

    args = parser.parse_args()

    token = args.token
    chat_id = args.chat_id
    update_interval = None

    # Parsing config file (supporta YAML e INI)
    if args.config and os.path.exists(args.config):
        config_path = args.config

        if config_path.endswith((".yaml", ".yml")):
            # YAML config
            try:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                if config:
                    telegram_config = config.get("telegram", {})
                    if not token:
                        token = telegram_config.get("token")
                    if not chat_id:
                        chat_id = telegram_config.get("chat_id")
                    # Leggi update_interval dalla config
                    settings = config.get("settings", {})
                    update_interval = settings.get("update_interval", update_interval)
            except Exception as e:
                print(f"Error loading YAML config: {e}")
        else:
            # INI config (retrocompatibilità)
            try:
                ini_config = configparser.ConfigParser()
                ini_config.read(config_path)
                if "Telegram" in ini_config:
                    if not token:
                        token = ini_config["Telegram"].get("token")
                    if not chat_id:
                        chat_id = ini_config["Telegram"].get("chat_id")
                if "Settings" in ini_config:
                    update_interval = ini_config["Settings"].getfloat(
                        "update_interval", fallback=update_interval
                    )
            except Exception as e:
                print(f"Error loading INI config: {e}")

    if not token:
        token = os.environ.get("TELEGRAM_TOKEN")
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

    if update_interval is None:
        update_interval = DEFAULT_UPDATE_INTERVAL

    return args.command, token, chat_id, update_interval, args.test
