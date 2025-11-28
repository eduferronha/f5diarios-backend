from fastapi import APIRouter, HTTPException, Depends, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from db import db
from schemas import PresetBase
from config import SECRET_KEY

# Rotas para gestão de presets personalizados dos utilizadores
router = APIRouter(prefix="/presets", tags=["Presets"])

# Coleção MongoDB onde os presets são guardados
collection = db["presets"]

ALGORITHM = "HS256"


# --- Obter username a partir do JWT ---
# Extrai o token do cabeçalho Authorization e identifica o utilizador associado.
def get_current_username(request: Request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente ou inválido"
        )

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
# Regista um preset associado ao utilizador autenticado.
# Após a criação, o preset é recuperado novamente para devolver o documento completo.
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_preset(preset: PresetBase, username: str = Depends(get_current_username)):
    try:
        data = preset.dict()
        data["username"] = username

        result = collection.insert_one(data)

        new_preset = collection.find_one({"_id": result.inserted_id})

        new_preset["id"] = str(new_preset["_id"])
        new_preset.pop("_id", None)

        return jsonable_encoder(new_preset)

    except Exception as e:
        print("❌ ERRO AO CRIAR PRESET:", e)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# --- Listar presets do utilizador ---
# Lista apenas os presets pertencentes ao utilizador autenticado.
@router.get("/", status_code=status.HTTP_200_OK)
async def get_user_presets(username: str = Depends(get_current_username)):
    try:
        presets = list(collection.find({"username": username}))

        for p in presets:
            p["id"] = str(p["_id"])
            p.pop("_id", None)

        return jsonable_encoder(presets)

    except Exception as e:
        print("❌ ERRO AO LER PRESETS:", e)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# --- Eliminar preset ---
# Remove um preset pertencente ao utilizador autenticado.
@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(preset_id: str, username: str = Depends(get_current_username)):
    try:
        result = collection.delete_one({
            "_id": ObjectId(preset_id),
            "username": username
        })

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Preset não encontrado ou não pertence a este utilizador"
            )

        return None

    except Exception as e:
        print("❌ ERRO AO ELIMINAR PRESET:", e)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# --- Atualizar preset ---
# Modifica os campos enviados, mantendo os restantes inalterados.
# Apenas presets pertencentes ao utilizador atual podem ser alterados.
@router.patch("/{preset_id}", status_code=status.HTTP_200_OK)
async def update_preset_status(preset_id: str, data: dict, username: str = Depends(get_current_username)):
    try:
        preset = collection.find_one({
            "_id": ObjectId(preset_id),
            "username": username
        })

        if not preset:
            raise HTTPException(status_code=404, detail="Preset não encontrado")

        collection.update_one({"_id": ObjectId(preset_id)}, {"$set": data})

        updated = collection.find_one({"_id": ObjectId(preset_id)})
        updated["id"] = str(updated["_id"])
        updated.pop("_id", None)

        return jsonable_encoder(updated)

    except Exception as e:
        print("❌ ERRO AO ATUALIZAR PRESET:", e)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
