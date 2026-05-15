from minio import Minio
from minio.error import S3Error
from datetime import timedelta
import magic  # python-magic: detecta MIME real por bytes, no extensión
import uuid, io
from app.config import settings

ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_MIMES = {"video/mp4", "video/quicktime", "audio/mpeg", "audio/mp4"}


class MediaService:

    def __init__(self):
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_USE_SSL,
        )
        self._bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Crea el bucket si no existe. MinIO no tiene namespaces, así que usamos un bucket único."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload_file(self, file_bytes: bytes, kind: str) -> str:
        """
        Sube un archivo. kind ∈ {'image', 'video'}.
        Devuelve la 'key' (path interno) que se guarda en notice.media_keys.
        """

        # 1. Validación de tamaño (defensa adicional al límite de FastAPI)
        max_mb = (
            settings.NOTICE_MAX_IMAGE_MB
            if kind == "image"
            else settings.NOTICE_MAX_VIDEO_MB
        )
        if len(file_bytes) > max_mb * 1024 * 1024:
            raise ValueError(f"Archivo supera {max_mb} MB.")
        # 2. Detección de MIME real (no confiar en la extensión)
        mime = magic.from_buffer(file_bytes[:2048], mime=True)
        allowed = ALLOWED_IMAGE_MIMES if kind == "image" else ALLOWED_VIDEO_MIMES
        if mime not in allowed:
            raise ValueError(f"Tipo de archivo no permitido: {mime}")
        # 3. Generar key único: {kind}/{uuid4}_{original_filename}
        ext = mime.split("/")[-1]
        key = f"{kind}/{uuid.uuid4()}.{ext}"
        # 4. Subir a MinIO con metadatos
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=mime,
        )
        return key

    def signed_url(self, key: str, expires_minutes: int = 60) -> str:
        """Genera una URL firmada para acceder al archivo. Útil para mostrar imágenes/videos sin exponer el bucket."""
        return self._client.presigned_get_object(
            self._bucket, key, expires=timedelta(minutes=expires_minutes)
        )

    def delete(self, key: str) -> None:
        """Elimina un archivo por su key."""
        try:
            self._client.remove_object(self._bucket, key)
        except S3Error as e:
            # Loguear el error pero no interrumpir el flujo (ej: si el archivo ya no existe)
            pass


media_service = MediaService()
