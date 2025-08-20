import asyncio
import base64
import binascii
from typing import Dict, Optional

from GoogleFindMyTools.Auth.firebase_messaging import FcmPushClient, FcmRegisterConfig
from GoogleFindMyTools.Auth.token_cache import get_cached_value, set_cached_value
from GoogleFindMyTools.ProtoDecoders.decoder import parse_device_update_protobuf


class FcmReceiver:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._listening = False
        self._start_lock = asyncio.Lock()
        self._pending: Dict[str, asyncio.Future] = {}

        # Expose the event loop
        self._loop = asyncio.get_event_loop()

        self.credentials = get_cached_value("fcm_credentials")
        self.pc = FcmPushClient(
            self._on_notification,
            FcmRegisterConfig(
                project_id="google.com:api-project-289722593072",
                app_id="1:289722593072:android:3cfcf5bc359f0308",
                api_key="AIzaSyD_gko3P392v6how2H7UpdeXQ0v2HLettc",
                messaging_sender_id="289722593072",
                bundle_id="com.google.android.apps.adm",
            ),
            self.credentials,
            self._on_credentials_updated,
        )

    @property
    def loop(self):
        """Expose the asyncio event loop used by this receiver."""
        return self._loop

    async def ensure_started(self):
        async with self._start_lock:
            if not self._listening:
                await self._register_for_fcm_and_listen()
                self._listening = True

    def get_fcm_token(self) -> str:
        return self.credentials["fcm"]["registration"]["token"]

    def get_android_id(self) -> str:
        return self.credentials["gcm"]["android_id"]

    def prepare_request(self, request_uuid: str) -> asyncio.Future:
        if request_uuid in self._pending:
            raise RuntimeError(f"Duplicate request_uuid: {request_uuid}")
        fut = self._loop.create_future()
        self._pending[request_uuid] = fut
        return fut

    def cancel_request(self, request_uuid: str, exc: Optional[BaseException] = None):
        fut = self._pending.pop(request_uuid, None)
        if fut and not fut.done():
            fut.set_exception(exc) if exc else fut.cancel()

    def _on_notification(self, obj, *_):
        try:
            payload = obj.get("data", {}).get("com.google.android.apps.adm.FCM_PAYLOAD")
            if not payload:
                return
            hex_string = binascii.hexlify(base64.b64decode(payload)).decode()
            device_update = parse_device_update_protobuf(hex_string)
            request_uuid = getattr(
                getattr(device_update, "fcmMetadata", None), "requestUuid", None
            )
            if request_uuid:
                fut = self._pending.pop(request_uuid, None)
                if fut and not fut.done():
                    fut.set_result(hex_string)
        except Exception:
            pass

    def _on_credentials_updated(self, creds):
        self.credentials = creds
        set_cached_value("fcm_credentials", self.credentials)

    async def _register_for_fcm(self, retries=5):
        for _ in range(retries):
            try:
                return await self.pc.checkin_or_register()
            except Exception:
                await self.pc.stop()
                await asyncio.sleep(5)
        raise RuntimeError("Unable to register for FCM after retries")

    async def _register_for_fcm_and_listen(self):
        await self._register_for_fcm()
        if not self._listening:
            await self.pc.start()


if __name__ == "__main__":
    receiver = FcmReceiver()
    print(receiver.get_android_id())
