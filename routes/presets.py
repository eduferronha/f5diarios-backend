from fastapi import APIRouter, HTTPException, Depends, Request, status
from jose import jwt, JWTError
from db import db
from schemas import PresetBase
from bson import ObjectId
from config import SECRET_KEY

router = APIRouter(prefix="/presets", tags=["Presets"])

collection = db["presets"]
users_collection = db["users"]
ALGORITHM = "HS256"


def get_current_username(request: Request):
    """Extrai o username do token JWT"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente ou inválido")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.post("/")
async def create_preset(preset: PresetBase, username: str = Depends(get_current_username)):
    """Cria um novo preset para o utilizador autenticado"""
    try:
        data = preset.dict()
        data["username"] = username  # 🔹 garante que é sempre o dono correto
        result = collection.insert_one(data)
        return {"id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao criar preset: {e}")


@router.get("/")
async def get_user_presets(username: str = Depends(get_current_username)):
    """Obtém todos os presets do utilizador autenticado"""
    presets = list(collection.find({"username": username}))
    for p in presets:
        p["id"] = str(p["_id"])
        del p["_id"]
    return presets


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str, username: str = Depends(get_current_username)):
    """Apaga um preset do utilizador autenticado"""
    result = collection.delete_one({"_id": ObjectId(preset_id), "username": username})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Preset não encontrado ou não pertence a este utilizador")
    return {"msg": "Preset removido com sucesso"}
