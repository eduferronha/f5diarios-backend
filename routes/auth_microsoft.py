from fastapi import APIRouter, HTTPException
from msal import ConfidentialClientApplication
from config import SECRET_KEY, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET, ENTRA_TENANT_ID
from datetime import datetime, timedelta
from jose import jwt
from db import users_collection

# Rotas relacionadas com autenticação via Microsoft Entra ID (OAuth 2.0).
router = APIRouter(prefix="/auth/entra", tags=["Auth Microsoft"])

ALGORITHM = "HS256"

# URL para onde a Microsoft redireciona o utilizador após login.
REDIRECT_URI = "https://diarios.f5tci.com/auth/callback"
# REDIRECT_URI = "https://polite-meadow-092d44603.3.azurestaticapps.net/auth/entra/entra-callback"
# REDIRECT_URI = "https://f5diarios-frontend.vercel.app/auth/callback"


# --- Configuração Microsoft Entra OAuth ---
# Microsoft Entra (Azure AD) usa o tenant ID para identificar a instância do diretório.
AUTHORITY = f"https://login.microsoftonline.com/{ENTRA_TENANT_ID}"

# Permissão mínima necessária para obter informação básica do utilizador.
SCOPES = ["User.Read"]

# Cliente MSAL para gerir autorização OAuth 2.0 com Microsoft Entra.
app_msal = ConfidentialClientApplication(
    ENTRA_CLIENT_ID,
    authority=AUTHORITY,
    client_credential=ENTRA_CLIENT_SECRET
)


# --- Iniciar login Microsoft Entra ---
# Endpoint GET /auth/entra/entra-login
# Gera um URL de autorização Microsoft onde o utilizador deve autenticar-se.
# O frontend redireciona o utilizador para este URL.
@router.get("/entra-login")
def entra_login():
    auth_url = app_msal.get_authorization_request_url(
        SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return {"auth_url": auth_url}


# --- Callback Microsoft Entra ---
# Endpoint GET /auth/entra/entra-callback
# Este endpoint recebe o parâmetro "code" enviado pela Microsoft após o utilizador fazer login.
# O código de autorização é trocado por um access_token e id_token (com dados do utilizador).
@router.get("/entra-callback")
def entra_callback(code: str):
    result = app_msal.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    # Se não houver token válido, o login falhou.
    if "access_token" not in result:
        raise HTTPException(
            status_code=401,
            detail="Falha na autenticação Microsoft."
        )

    # --- Obter email do utilizador autenticado ---
    # No id_token_claims vêm os dados do utilizador devolvidos pela Microsoft.
    email = result["id_token_claims"].get("preferred_username")

    # --- Verificar se este email existe na tua base de dados local ---
    db_user = users_collection.find_one({"email": email})

    if not db_user:
        raise HTTPException(
            status_code=403,
            detail="O seu email Microsoft não está registado no sistema."
        )

    # --- Criar token JWT local, igual ao fluxo de login interno ---
    token_data = {
        "sub": db_user["username"],                         # Username usado pela tua API
        "role": db_user.get("role", "user"),                # Papel do utilizador (user/admin)
        "exp": datetime.utcnow() + timedelta(minutes=60)    # Validade de 1h
    }

    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # Dados devolvidos ao frontend
    return {
        "access_token": access_token,
        "user": {
            "username": db_user["username"],
            "role": db_user.get("role", "user")
        }
    }
