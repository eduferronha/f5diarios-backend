from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import ParceiroBase, ParceiroOut
from config import SECRET_KEY

partners_collection = db["partners"]
router = APIRouter(prefix="/partners", tags=["Parceiros"])


# --- Autenticação básica com JWT (mesma do módulo clientes) ---
def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente.")
    token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido.")

# --- Criar parceiro ---
@router.post("/", response_model=ParceiroOut)
def create_parceiro(parceiro: ParceiroBase, user: str = Depends(get_current_user)):
    new_parceiro = parceiro.dict()
    result = partners_collection.insert_one(new_parceiro)
    return {"id": str(result.inserted_id), **new_parceiro}

# --- Listar parceiros ---
@router.get("/", response_model=list[ParceiroOut])
def list_partners(user: str = Depends(get_current_user)):
    partners = []
    for c in partners_collection.find():
        c["id"] = str(c["_id"])
        c.pop("_id", None)
        partners.append(c)
    return partners

# --- Obter parceiro específico ---
@router.get("/{parceiro_id}", response_model=ParceiroOut)
def get_parceiro(parceiro_id: str, user: str = Depends(get_current_user)):
    parceiro = partners_collection.find_one({"_id": ObjectId(parceiro_id)})
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado.")
    parceiro["id"] = str(parceiro["_id"])
    parceiro.pop("_id", None)
    return parceiro

# --- Atualizar parceiro ---
@router.put("/{parceiro_id}")
def update_parceiro(parceiro_id: str, updated: ParceiroBase, user: str = Depends(get_current_user)):
    result = partners_collection.update_one(
        {"_id": ObjectId(parceiro_id)},
        {"$set": updated.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado.")
    return {"message": "Parceiro atualizado com sucesso!"}

# --- Eliminar Parceiro ---
@router.delete("/{parceiro_id}")
def delete_parceiro(parceiro_id: str, user: str = Depends(get_current_user)):
    result = partners_collection.delete_one({"_id": ObjectId(parceiro_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado.")
    return {"message": "Parceiro eliminado com sucesso!"}
