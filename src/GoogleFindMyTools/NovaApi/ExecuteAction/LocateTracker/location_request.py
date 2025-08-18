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


def get_location_data_for_device(canonic_device_id):
    result = None
    request_uuid = generate_random_uuid()
    # done_event = threading.Event()

    def handle_location_response(response):
        nonlocal result
        device_update = parse_device_update_protobuf(response)

        if device_update.fcmMetadata.requestUuid == request_uuid:
            result = parse_device_update_protobuf(response)
            # done_event.set()

    fcm_token = FcmReceiver().register_for_location_updates(handle_location_response)

    hex_payload = create_location_request(canonic_device_id, fcm_token, request_uuid)
    nova_request(NOVA_ACTION_API_SCOPE, hex_payload)

    # Wait for the callback to set the result, with a timeout to avoid infinite hang
    # done_event.wait(timeout=60)  # Timeout in seconds, adjust as needed
    import time

    while result is None:
        time.sleep(0.1)  # Wait for the result to be set
    # if result is None:
    #     raise TimeoutError("Location request timed out.")

    return decrypt_location_response_locations(result)


if __name__ == "__main__":
    locations = get_location_data_for_device(
        get_example_data("sample_canonic_device_id"), "Test"
    )
    print_decrypted_location_response_locations(locations)
