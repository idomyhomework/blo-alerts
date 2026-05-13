from pydantic import BaseModel, Field

# --- Request schemas (datos que entran) ---


class RequestOTPIn(BaseModel):
    # Formato E.164: +34 seguido de 9 dígitos
    phone: str = Field(..., pattern=r"^\+[1-9]\d{6,14}$")


class VerifyOTPIn(BaseModel):
    phone: str = Field(..., pattern=r"^\+[1-9]\d{6,14}$")
    code: str = Field(..., pattern=r"^\d{6}$")
    fcm_token: str | None = None  # Token FCM del dispositivo, opcional


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


# --- Response schemas (datos que salen) ---


class RequestOTPOut(BaseModel):
    # Mensaje genérico: no revelamos si el número está registrado o no
    message: str = "Si el número es válido, recibirás un SMS con un código."


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
