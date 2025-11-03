from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import ContractBase, ContractOut
from config import SECRET_KEY

contracts_collection = db["contracts"]
router = APIRouter(prefix="/contracts", tags=["Contratos"])


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

# --- Criar contrato ---
@router.post("/", response_model=ContractOut)
def create_contract(contract: ContractBase, user: str = Depends(get_current_user)):
    new_contract = contract.dict()
    result = contracts_collection.insert_one(new_contract)
    return {"id": str(result.inserted_id), **new_contract}

# --- Listar contratos ---
@router.get("/", response_model=list[ContractOut])
def list_contracts(user: str = Depends(get_current_user)):
    contracts = []
    for c in contracts_collection.find():
        c["id"] = str(c["_id"])
        c.pop("_id", None)
        contracts.append(c)
    return contracts

# --- Obter contrato específico ---
@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: str, user: str = Depends(get_current_user)):
    contract = contracts_collection.find_one({"_id": ObjectId(contract_id)})
    if not contract:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    contract["id"] = str(contract["_id"])
    contract.pop("_id", None)
    return contract

# --- Atualizar contrato ---
@router.put("/{contract_id}")
def update_contract(contract_id: str, updated: ContractBase, user: str = Depends(get_current_user)):
    result = contracts_collection.update_one(
        {"_id": ObjectId(contract_id)},
        {"$set": updated.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    return {"message": "Contrato atualizado com sucesso!"}

# --- Eliminar contrato ---
@router.delete("/{contract_id}")
def delete_contract(contract_id: str, user: str = Depends(get_current_user)):
    result = contracts_collection.delete_one({"_id": ObjectId(contract_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    return {"message": "Contrato eliminado com sucesso!"}
