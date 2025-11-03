from fastapi import APIRouter, HTTPException
from jose import jwt
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
