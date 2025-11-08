from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from passlib.context import CryptContext
from db import users_collection
from schemas import UserBase, UserOut
from config import SECRET_KEY

router = APIRouter(prefix="/users", tags=["Utilizadores"])

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Autenticação JWT ---
def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente."
        )
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido."
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido."
        )


# --- Criar utilizador ---
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserBase, current_user: str = Depends(get_current_user)):
    new_user = user.dict()

    # 🔐 Encriptar password antes de gravar
    if "password" in new_user:
        new_user["password"] = pwd_context.hash(new_user["password"])

    result = users_collection.insert_one(new_user)
    return {"id": str(result.inserted_id), **new_user}


# --- Listar utilizadores ---
@router.get("/", response_model=list[UserOut])
def list_users(current_user: str = Depends(get_current_user)):
    users = []
    for u in users_collection.find():
        u["id"] = str(u["_id"])
        u.pop("_id", None)
        u.pop("password", None)  # 🔒 nunca devolver password
        users.append(u)
    return users


# --- Obter utilizador por ID ---
@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, current_user: str = Depends(get_current_user)):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado."
        )
    user["id"] = str(user["_id"])
    user.pop("_id", None)
    user.pop("password", None)
    return user


# --- Atualizar utilizador ---
@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, updated_data: dict, current_user: str = Depends(get_current_user)):
    existing_user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado."
        )

    # 🔐 Encriptar password se for atualizada
    if "password" in updated_data:
        updated_data["password"] = pwd_context.hash(updated_data["password"])

    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})
    updated_user = users_collection.find_one({"_id": ObjectId(user_id)})
    updated_user["id"] = str(updated_user["_id"])
    updated_user.pop("_id", None)
    updated_user.pop("password", None)
    return updated_user


# --- Eliminar utilizador ---
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: str = Depends(get_current_user)):
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado."
        )
    return None


# --- ✅ Alterar password ---
@router.post("/change-password")
def change_password(request: Request, body: dict, current_user: str = Depends(get_current_user)):
    username = current_user
    current_password = body.get("current_password")
    new_password = body.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Campos obrigatórios em falta.")

    # 🔍 Buscar utilizador na base de dados
    user = users_collection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

    # 🔑 Verificar password atual
    if not pwd_context.verify(current_password, user["password"]):
        raise HTTPException(status_code=401, detail="Password atual incorreta.")

    # 🔐 Atualizar password encriptada
    hashed_new_password = pwd_context.hash(new_password)
    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hashed_new_password}}
    )

    return {"message": "Password alterada com sucesso!"}
