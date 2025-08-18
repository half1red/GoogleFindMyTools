#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#

import json
import os

from dotenv import load_dotenv

load_dotenv()

# GFINDMY_SECRETS_FILE = "secrets.json"


def get_cached_value_or_set(name: str, generator: callable):
    existing_value = get_cached_value(name)

    if existing_value is not None:
        return existing_value

    value = generator()
    set_cached_value(name, value)
    return value


def get_cached_value(name: str):
    secrets_file = _get_secrets_file()

    if os.path.exists(secrets_file):
        with open(secrets_file, "r") as file:
            try:
                data = json.load(file)
                value = data.get(name)
                if value:
                    return value
            except json.JSONDecodeError:
                return None
    return None


def set_cached_value(name: str, value: str):
    secrets_file = _get_secrets_file()

    if os.path.exists(secrets_file):
        with open(secrets_file, "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                raise Exception("Could not read secrets file. Aborting.")
    else:
        data = {}
    data[name] = value
    with open(secrets_file, "w") as file:
        json.dump(data, file)


def _get_secrets_file():
    GFINDMY_SECRETS_FILE = os.getenv("GFINDMY_SECRETS_FILE")
    if GFINDMY_SECRETS_FILE:
        return GFINDMY_SECRETS_FILE

    return os.path.realpath(
        os.path.expanduser(os.path.join("~/", ".gfindmy_secrets.json"))
    )


def delete_secrets_file(name: str):
    secrets_file = _get_secrets_file()

    if os.path.exists(secrets_file):
        os.remove(secrets_file)
