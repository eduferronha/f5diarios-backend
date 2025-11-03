from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from msal import ConfidentialClientApplication
import httpx
import jwt
from jwt import PyJWKClient
from config import CLIENT_ID, CLIENT_SECRET, AUTHORITY, SCOPE, REDIRECT_URI

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.get("/login")
def login():
    app_msal = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY)
    auth_url = app_msal.get_authorization_request_url(SCOPE, redirect_uri=REDIRECT_URI)
    return RedirectResponse(auth_url)


@router.get("/callback")
def callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Código de autorização em falta.")

    app_msal = ConfidentialClientApplication(
        CLIENT_ID, CLIENT_SECRET, authority=AUTHORITY
    )
    result = app_msal.acquire_token_by_authorization_code(
        code, scopes=SCOPE, redirect_uri=REDIRECT_URI
    )

    if "id_token" not in result:
        raise HTTPException(status_code=400, detail="Falha ao obter token.")

    return {"token": result["id_token"]}


async def verify_token(token: str = Depends(lambda request: request.headers.get("Authorization"))):
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente ou inválido.")

    token = token.split(" ")[1]
    jwks_url = f"{AUTHORITY}/discovery/v2.0/keys"
    jwks_client = PyJWKClient(jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token).key

    try:
        decoded_token = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            options={"verify_exp": True},
        )
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}")
