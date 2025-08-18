#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#


from NovaApi.ExecuteAction.LocateTracker.location_request import (
    get_location_data_for_device,
)
from NovaApi.ListDevices.nbe_list_devices import request_device_list
from ProtoDecoders.decoder import get_canonic_ids, parse_device_list_protobuf
from SpotApi.UploadPrecomputedPublicKeyIds.upload_precomputed_public_key_ids import (
    refresh_custom_trackers,
)


def list_devices():
    result_hex = request_device_list()

    device_list = parse_device_list_protobuf(result_hex)

    refresh_custom_trackers(device_list)
    canonic_ids = get_canonic_ids(device_list)
    return canonic_ids


def device_locations(canonic_ids):
    return get_location_data_for_device(canonic_ids)


if __name__ == "__main__":
    print("Fetching devices...")
    print("Devices are :")
    devices = list_devices()
    print(devices)
    if devices:
        print("Getting location for first device...")
        locations = device_locations(devices[0][1])
        print(locations)
