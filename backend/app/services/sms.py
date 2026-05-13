import logging

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """Wrapper sobre Twilio. Centraliza el envío para auditar y testear."""

    def __init__(self):
        # ── En desarrollo sin credenciales reales, el cliente queda como None ─
        # El router ya gestiona el caso sent=False en ENV=development
        has_credentials = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)
        self._client = (
            Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            if has_credentials
            else None
        )
        self._from = settings.TWILIO_FROM_NUMBER

    def send_otp(self, phone: str, code: str) -> bool:
        """Envía OTP por SMS. Devuelve True si OK, False si falla."""
        body = settings.TWILIO_OTP_TEMPLATE.format(code=code)
        return self._send(phone, body, kind="otp")

    def send_critical_notice(self, phone: str, title: str, body: str) -> bool:
        """SMS de aviso crítico (fallback cuando el push ha fallado)."""
        text = f"[AVISO MUNICIPAL CRÍTICO] {title}: {body[:120]}"
        return self._send(phone, text, kind="critical")

    def _send(self, phone: str, body: str, kind: str) -> bool:
        if self._client is None:
            logger.warning("SMS no enviado: cliente Twilio no configurado (dev mode)")
            return False
        try:
            # NO loguear el body: puede contener el OTP en claro
            logger.info("Enviando SMS", extra={"phone": phone, "kind": kind})
            message = self._client.messages.create(
                to=phone,
                from_=self._from,
                body=body,
            )
            logger.info(
                "SMS enviado",
                extra={"phone": phone, "sid": message.sid, "kind": kind},
            )
            return True
        except TwilioRestException as exc:
            logger.error(
                "Fallo al enviar SMS",
                extra={"phone": phone, "kind": kind, "error": str(exc)},
            )
            return False


# Instancia lazy: se crea cuando se importa pero no conecta hasta el primer uso
_sms_service: SMSService | None = None


def get_sms_service() -> SMSService:
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
