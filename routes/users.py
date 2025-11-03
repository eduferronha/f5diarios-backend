from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import users_collection
from schemas import UserBase, UserOut
from config import SECRET_KEY

router = APIRouter(prefix="/users", tags=["Utilizadores"])


# --- Autenticação JWT ---
def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente.")
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")


# --- Criar utilizador ---
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserBase, current_user: str = Depends(get_current_user)):
    new_user = user.dict()
    result = users_collection.insert_one(new_user)
    return {"id": str(result.inserted_id), **new_user}


# --- Listar utilizadores ---
@router.get("/", response_model=list[UserOut])
def list_users(current_user: str = Depends(get_current_user)):
    users = []
    for u in users_collection.find():
        u["id"] = str(u["_id"])
        u.pop("_id", None)
        users.append(u)
    return users


# --- Obter utilizador por ID ---
@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, current_user: str = Depends(get_current_user)):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado.")
    user["id"] = str(user["_id"])
    user.pop("_id", None)
    return user


# --- Atualizar utilizador ---
@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, updated_data: dict, current_user: str = Depends(get_current_user)):
    existing_user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado.")
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})
    updated_user = users_collection.find_one({"_id": ObjectId(user_id)})
    updated_user["id"] = str(updated_user["_id"])
    updated_user.pop("_id", None)
    return updated_user


# --- Eliminar utilizador ---
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: str = Depends(get_current_user)):
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado.")
    return None
