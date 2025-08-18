#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#

# import asyncio
# import threading

from GoogleFindMyTools.Auth.fcm_receiver import FcmReceiver
from GoogleFindMyTools.example_data_provider import get_example_data
from GoogleFindMyTools.NovaApi.ExecuteAction.LocateTracker.decrypt_locations import (
    decrypt_location_response_locations,
    print_decrypted_location_response_locations,
)
from GoogleFindMyTools.NovaApi.ExecuteAction.nbe_execute_action import (
    create_action_request,
    serialize_action_request,
)
from GoogleFindMyTools.NovaApi.nova_request import nova_request
from GoogleFindMyTools.NovaApi.scopes import NOVA_ACTION_API_SCOPE
from GoogleFindMyTools.NovaApi.util import generate_random_uuid
from GoogleFindMyTools.ProtoDecoders import DeviceUpdate_pb2
from GoogleFindMyTools.ProtoDecoders.decoder import parse_device_update_protobuf


def create_location_request(canonic_device_id, fcm_registration_id, request_uuid):
    action_request = create_action_request(
        canonic_device_id, fcm_registration_id, request_uuid=request_uuid
    )

    # Random values, can be arbitrary
    action_request.action.locateTracker.lastHighTrafficEnablingTime.seconds = 1732120060
    action_request.action.locateTracker.contributorType = (
        DeviceUpdate_pb2.SpotContributorType.FMDN_ALL_LOCATIONS
    )

    # Convert to hex string
    hex_payload = serialize_action_request(action_request)

    return hex_payload


def get_location_data_for_device(canonic_device_id: str, timeout: float = 60.0):
    receiver = FcmReceiver()
    receiver.ensure_started()

    request_uuid = generate_random_uuid()
    fut = receiver.prepare_request(request_uuid)

    try:
        fcm_token = receiver.get_fcm_token()
        hex_payload = create_location_request(
            canonic_device_id, fcm_token, request_uuid
        )

        # Envoi de la requête (HTTP/gRPC/whatever) – synchrone côté appelant
        nova_request(NOVA_ACTION_API_SCOPE, hex_payload)

        # Attend la réponse corrélée par request_uuid
        hex_response = fut.result(timeout=timeout)

        # Transforme le résultat
        device_update = parse_device_update_protobuf(hex_response)
        return decrypt_location_response_locations(device_update)

    except Exception as e:
        # Nettoyage en cas d’erreur/timeout
        receiver.cancel_request(request_uuid, exc=e)
        raise


if __name__ == "__main__":
    locations = get_location_data_for_device(
        get_example_data("sample_canonic_device_id"), "Test"
    )
    print_decrypted_location_response_locations(locations)
