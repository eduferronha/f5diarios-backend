from fastapi import APIRouter, HTTPException
from msal import ConfidentialClientApplication
from config import SECRET_KEY, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET, ENTRA_TENANT_ID
from datetime import datetime, timedelta
from jose import jwt
from db import users_collection

router = APIRouter(prefix="/auth/entra", tags=["Auth Microsoft"])

ALGORITHM = "HS256"
REDIRECT_URI = "https://f5diarios-frontend.vercel.app/auth/callback"

# --- Microsoft Entra OAuth Config ---
AUTHORITY = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}"
SCOPES = ["User.Read"]


app_msal = ConfidentialClientApplication(
    ENTRA_CLIENT_ID,
    authority=AUTHORITY,
    client_credential=ENTRA_CLIENT_SECRET
)


@router.get("/entra-login")
def entra_login():
    auth_url = app_msal.get_authorization_request_url(
        SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return {"auth_url": auth_url}


@router.get("/entra-callback")
def entra_callback(code: str):
    result = app_msal.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    if "access_token" not in result:
        raise HTTPException(status_code=401, detail="Falha na autenticação Microsoft.")

    # Dados do utilizador (email)
    email = result["id_token_claims"].get("preferred_username")

    # --- Procurar utilizador na tua BD pelo email ---
    db_user = users_collection.find_one({"email": email})

    if not db_user:
        raise HTTPException(
            status_code=403,
            detail="O seu email Microsoft não está registado no sistema."
        )

    # --- Criar token JWT igual ao login normal ---
    token_data = {
        "sub": db_user["username"],
        "role": db_user.get("role", "user"),
        "exp": datetime.utcnow() + timedelta(minutes=60)
    }

    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": access_token,
        "user": {
            "username": db_user["username"],
            "role": db_user.get("role", "user")
        }
    }
