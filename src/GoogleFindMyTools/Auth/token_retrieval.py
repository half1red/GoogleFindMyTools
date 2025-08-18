#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#

import gpsoauth

from GoogleFindMyTools.Auth.aas_token_retrieval import get_aas_token
from GoogleFindMyTools.Auth.fcm_receiver import FcmReceiver
from GoogleFindMyTools.Auth.token_cache import delete_secrets_file


def request_token(username, scope, play_services=False):
    aas_token = get_aas_token()
    android_id = FcmReceiver().get_android_id()
    request_app = (
        "com.google.android.gms" if play_services else "com.google.android.apps.adm"
    )

    auth_response = gpsoauth.perform_oauth(
        username,
        aas_token,
        android_id,
        service="oauth2:https://www.googleapis.com/auth/" + scope,
        app=request_app,
        client_sig="38918a453d07199354f8b19af05ec6562ced5788",
    )
    if "Auth" not in auth_response:
        print("Failed to retrieve auth token. Please check your credentials.")
        res = input("Do you want to delete saved credentials? (y/n): ")
        if res.lower() == "y":
            delete_secrets_file()
        raise ValueError(
            "Failed to retrieve auth token, check your credentials and try again."
        )
    token = auth_response["Auth"]

    return token
