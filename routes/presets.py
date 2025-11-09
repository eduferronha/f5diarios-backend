from fastapi import APIRouter, HTTPException, Depends, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import PresetBase
from config import SECRET_KEY
from fastapi.encoders import jsonable_encoder


router = APIRouter(prefix="/presets", tags=["Presets"])

collection = db["presets"]
users_collection = db["users"]
ALGORITHM = "HS256"


# --- Obter username do token JWT ---
def get_current_username(request: Request):
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


# --- Criar novo preset ---
# @router.post("/", status_code=status.HTTP_201_CREATED)
# async def create_preset(preset: PresetBase, username: str = Depends(get_current_username)):
#     data = preset.dict()
#     data["username"] = username
#     result = collection.insert_one(data)
#     return {"id": str(result.inserted_id), **data}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_preset(preset: PresetBase, username: str = Depends(get_current_username)):
    try:
        data = preset.dict()
        data["username"] = username
        result = collection.insert_one(data)
        # ✅ Converter dados para tipos compatíveis com JSON
        clean_data = jsonable_encoder(data)
        clean_data["id"] = str(result.inserted_id)
        return clean_data
    except Exception as e:
        print("❌ ERRO AO CRIAR PRESET:", e)
        raise HTTPException(status_code=500, detail=str(e))



# --- Listar presets do utilizador autenticado ---
@router.get("/", status_code=status.HTTP_200_OK)
async def get_user_presets(username: str = Depends(get_current_username)):
    presets = list(collection.find({"username": username}))
    for p in presets:
        p["id"] = str(p["_id"])
        del p["_id"]
    return presets


# --- Eliminar preset ---
@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(preset_id: str, username: str = Depends(get_current_username)):
    result = collection.delete_one({"_id": ObjectId(preset_id), "username": username})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Preset não encontrado ou não pertence a este utilizador")
    return None


# --- Atualizar campo 'ativo' (ou qualquer outro) ---
@router.patch("/{preset_id}", status_code=status.HTTP_200_OK)
async def update_preset_status(preset_id: str, data: dict, username: str = Depends(get_current_username)):
    preset = collection.find_one({"_id": ObjectId(preset_id), "username": username})
    if not preset:
        raise HTTPException(status_code=404, detail="Preset não encontrado")

    collection.update_one({"_id": ObjectId(preset_id)}, {"$set": data})
    updated = collection.find_one({"_id": ObjectId(preset_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return updated
