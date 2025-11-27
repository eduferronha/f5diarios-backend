from fastapi import APIRouter, HTTPException, Depends, Request
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from schemas import UserCreate, UserLogin, UserOut
from db import users_collection
from config import SECRET_KEY

router = APIRouter(prefix="/auth", tags=["Auth"])

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Login Management


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register")
def register(user: UserCreate):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Utilizador já existe.")
    hashed = hash_password(user.password)
    users_collection.insert_one({"username": user.username, "password": hashed})
    return {"message": "Utilizador criado com sucesso!"}

@router.post("/login")
def login(user: UserLogin):
    db_user = users_collection.find_one({"username": user.username})
    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Credenciais inválidas")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # ✅ inclui o role também no token JWT
    to_encode = {
        "sub": user.username,
        "role": db_user.get("role", "user"),  # 👈 ESSENCIAL
        "exp": datetime.utcnow() + access_token_expires
    }

    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": access_token,
        "user": {
            "username": db_user["username"],
            "role": db_user.get("role", "user")
        }
    }


@router.post("/refresh")
def refresh_token(current_user = Depends(get_current_user)):
    # Criar um novo token com +1 hora
    new_token = create_access_token({
        "sub": current_user["username"],
        "role": current_user.get("role", "user")
    })

    return {"access_token": new_token}


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

        db_user = users_collection.find_one({"username": username})

        if db_user is None:
            raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

        return db_user

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
