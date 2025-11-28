from fastapi import APIRouter, HTTPException, Depends, Request
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from schemas import UserCreate, UserLogin
from db import users_collection
from config import SECRET_KEY

# Rotas principais de autenticação (registo, login, refresh token).
router = APIRouter(prefix="/auth", tags=["Auth"])

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Contexto de encriptação para passwords (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Encripta uma password usando bcrypt.
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Verifica se uma password em texto simples corresponde ao hash guardado.
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# Cria um token JWT contendo um payload e um campo "exp" (expiração).
def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


# Lê o cabeçalho Authorization: Bearer <token>,
# valida o token e devolve o utilizador autenticado.
def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(status_code=401, detail="Token não fornecido.")

    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido.")

        # Procurar utilizador na base de dados
        db_user = users_collection.find_one({"username": username})
        if db_user is None:
            raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

        return db_user

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")


# Endpoint POST /auth/register
# Recebe username + password e cria novo utilizador.
# A password é encriptada antes de ser guardada.
@router.post("/register")
def register(user: UserCreate):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Utilizador já existe.")

    hashed = hash_password(user.password)
    users_collection.insert_one({
        "username": user.username,
        "password": hashed,
        "role": "user"   # função padrão
    })

    return {"message": "Utilizador criado com sucesso!"}


# Endpoint POST /auth/login
# Verifica credenciais e, se válidas, devolve um access_token JWT.
# Também devolve dados do utilizador (username + role).
@router.post("/login")
def login(user: UserLogin):
    db_user = users_collection.find_one({"username": user.username})

    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Credenciais inválidas")

    token_data = {
        "sub": user.username,
        "role": db_user.get("role", "user"),
    }

    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "user": {
            "username": db_user["username"],
            "role": db_user.get("role", "user")
        }
    }


# Endpoint POST /auth/refresh
# Requer um token JWT válido no cabeçalho Authorization.
# Gera um novo token com nova data de expiração (sem pedir login novamente).
@router.post("/refresh")
def refresh_token(current_user=Depends(get_current_user)):
    new_token = create_access_token({
        "sub": current_user["username"],
        "role": current_user.get("role", "user")
    })

    return {"access_token": new_token}
