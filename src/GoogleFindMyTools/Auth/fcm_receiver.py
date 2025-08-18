import asyncio
import base64
import binascii
import threading
from concurrent.futures import Future
from typing import Dict, Optional

from GoogleFindMyTools.Auth.firebase_messaging import FcmPushClient, FcmRegisterConfig
from GoogleFindMyTools.Auth.token_cache import get_cached_value, set_cached_value
from GoogleFindMyTools.ProtoDecoders.decoder import parse_device_update_protobuf


class FcmReceiver:
    _instance = None

    # Loop et thread unique pour tout le process
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _loop_thread: Optional[threading.Thread] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FcmReceiver, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        # Define Firebase project configuration
        project_id = "google.com:api-project-289722593072"
        app_id = "1:289722593072:android:3cfcf5bc359f0308"
        api_key = "AIzaSyD_gko3P392v6how2H7UpdeXQ0v2HLettc"
        message_sender_id = "289722593072"

        fcm_config = FcmRegisterConfig(
            project_id=project_id,
            app_id=app_id,
            api_key=api_key,
            messaging_sender_id=message_sender_id,
            bundle_id="com.google.android.apps.adm",
        )

        self.credentials = get_cached_value("fcm_credentials")
        self.pc = FcmPushClient(
            self._on_notification,
            fcm_config,
            self.credentials,
            self._on_credentials_updated,
        )

        # Gestion de l'état
        self._listening = False
        self._start_lock = threading.Lock()

        # Registre de corrélation: request_uuid -> Future
        self._pending: Dict[str, Future] = {}
        self._pending_lock = threading.Lock()

        # Démarre la boucle en arrière-plan au premier import
        if FcmReceiver._loop is None:
            FcmReceiver._loop = asyncio.new_event_loop()
            FcmReceiver._loop_thread = threading.Thread(
                target=self._run_loop, args=(FcmReceiver._loop,), daemon=True
            )
            FcmReceiver._loop_thread.start()

    # --- Loop management

    def _run_loop(self, loop: asyncio.AbstractEventLoop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def _run_coro(self, coro):
        """Soumet un coroutine à la boucle de fond et attend le résultat (thread-safe)."""
        fut = asyncio.run_coroutine_threadsafe(coro, FcmReceiver._loop)
        return fut.result()

    def ensure_started(self):
        """Démarre l'enregistrement FCM et l'écoute une seule fois, de façon thread-safe."""
        if self._listening:
            return
        with self._start_lock:
            if self._listening:
                return
            self._run_coro(self._register_for_fcm_and_listen())
            self._listening = True

    # --- Public helpers

    def get_fcm_token(self) -> str:
        """Assure le démarrage et renvoie le token FCM."""
        self.ensure_started()
        return self.credentials["fcm"]["registration"]["token"]

    def get_android_id(self) -> str:
        """Assure le démarrage et renvoie l'android_id."""
        self.ensure_started()
        return self.credentials["gcm"]["android_id"]

    # --- Corrélation request/response

    def prepare_request(self, request_uuid: str) -> Future:
        """Crée et enregistre une Future pour ce request_uuid."""
        fut = Future()
        with self._pending_lock:
            if request_uuid in self._pending:
                raise RuntimeError(f"Duplicate request_uuid: {request_uuid}")
            self._pending[request_uuid] = fut
        return fut

    def cancel_request(self, request_uuid: str, exc: Optional[BaseException] = None):
        """Annule et nettoie une requête en attente (timeout, erreur réseau, etc.)."""
        with self._pending_lock:
            fut = self._pending.pop(request_uuid, None)
        if fut and not fut.done():
            if exc:
                fut.set_exception(exc)
            else:
                fut.cancel()

    # --- Notification handler

    def _on_notification(self, obj, notification, data_message):
        """Callback appelée par FcmPushClient sur réception d'une notif FCM."""
        try:
            if (
                "data" in obj
                and "com.google.android.apps.adm.FCM_PAYLOAD" in obj["data"]
            ):
                base64_string = obj["data"]["com.google.android.apps.adm.FCM_PAYLOAD"]
                decoded_bytes = base64.b64decode(base64_string)
                hex_string = binascii.hexlify(decoded_bytes).decode("utf-8")

                # On parse pour extraire requestUuid et corréler
                device_update = parse_device_update_protobuf(hex_string)
                request_uuid = getattr(
                    getattr(device_update, "fcmMetadata", None), "requestUuid", None
                )

                if request_uuid:
                    with self._pending_lock:
                        fut = self._pending.pop(request_uuid, None)
                    if fut and not fut.done():
                        # On renvoie la payload hex brute (ou device_update si tu préfères)
                        fut.set_result(hex_string)
                else:
                    # Pas de requestUuid: ignorer ou logguer
                    pass
            else:
                # Payload non trouvée: ignorer ou logguer
                pass
        except Exception as e:
            # En cas d'erreur de parsing, on ne casse pas tout: log possible.
            pass

    def _on_credentials_updated(self, creds):
        self.credentials = creds
        set_cached_value("fcm_credentials", self.credentials)

    # --- Async internals

    async def _register_for_fcm(self):
        fcm_token = None
        while fcm_token is None:
            try:
                fcm_token = await self.pc.checkin_or_register()
            except Exception:
                await self.pc.stop()
                await asyncio.sleep(5)

    async def _register_for_fcm_and_listen(self):
        await self._register_for_fcm()
        if not self._listening:
            await self.pc.start()
        # Ne pas print en prod


if __name__ == "__main__":
    receiver = FcmReceiver()
    print(receiver.get_android_id())
