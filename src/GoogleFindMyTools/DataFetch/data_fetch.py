#
#  GoogleFindMyTools - A set of tools to interact with the Google Find My API
#  Copyright © 2024 Leon Böttger. All rights reserved.
#


import asyncio

from GoogleFindMyTools.NovaApi.ExecuteAction.LocateTracker.location_request import (
    get_location_data_for_device,
)
from GoogleFindMyTools.NovaApi.ListDevices.nbe_list_devices import request_device_list
from GoogleFindMyTools.ProtoDecoders.decoder import (
    get_canonic_ids,
    parse_device_list_protobuf,
)
from GoogleFindMyTools.SpotApi.UploadPrecomputedPublicKeyIds.upload_precomputed_public_key_ids import (
    refresh_custom_trackers,
)


def list_devices():
    result_hex = request_device_list()

    device_list = parse_device_list_protobuf(result_hex)

    refresh_custom_trackers(device_list)
    canonic_ids = get_canonic_ids(device_list)
    return canonic_ids


async def device_locations(canonic_ids):
    return await get_location_data_for_device(canonic_ids)


if __name__ == "__main__":
    print("Fetching devices...")
    print("Devices are :")
    devices = list_devices()
    print(devices)
    # if devices:
    #     print("Getting location for first device...")
    #     locations = device_locations(devices[0][1])
    #     print(locations)
    device_ids = [device[1] for device in devices]

    async def runner():
        for dev_id in device_ids:
            print(f"Getting location for device: {dev_id}")
            result = await get_location_data_for_device(dev_id)
            print(dev_id, result)
        print("All tasks completed. Closing after all waits done")
        # for task in asyncio.all_tasks():
        #     print(task)

    # Une seule fois dans tout le programme
    asyncio.run(runner())
    # for device in devices:
    #     print(f"Getting location for device: {device[1]}")
    #     locations = asyncio.run(device_locations(device[1]))
    #     print(locations)
