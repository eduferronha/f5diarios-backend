from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import ContractBase, ContractOut
from config import SECRET_KEY

# Coleção MongoDB onde os contratos são armazenados
contracts_collection = db["contracts"]

# Rota principal para gestão de contratos (prefixo /contracts)
# Inclui endpoints CRUD para criar, listar, obter, atualizar e eliminar contratos.
router = APIRouter(prefix="/contracts", tags=["Contratos"])


# --- Autenticação JWT ---
# Função dependência para extrair e validar token JWT do cabeçalho Authorization:
#   "Authorization: Bearer <token>"
# Decodifica o token com SECRET_KEY e algoritmo HS256.
# Se for válido, devolve o campo 'sub' (username).
# Caso contrário, devolve erro 401.
def get_current_user(request: Request):
    token = request.headers.get("Authorization")

    if not token or not token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente."
        )

    token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )


# --- Criar contrato ---
# Endpoint POST /contracts/
# Recebe um ContractBase, guarda na base de dados e devolve o contrato criado.
# Converte _id → id para compatibilidade com o schema ContractOut.
@router.post("/", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(contract: ContractBase, user: str = Depends(get_current_user)):
    new_contract = contract.dict()

    result = contracts_collection.insert_one(new_contract)

    return {"id": str(result.inserted_id), **new_contract}


# --- Listar contratos ---
# Endpoint GET /contracts/
# Devolve todos os contratos existentes.
# Converte _id para id (string) e remove _id antes de devolver.
@router.get("/", response_model=list[ContractOut])
def list_contracts(user: str = Depends(get_current_user)):
    contracts = []

    for c in contracts_collection.find():
        c["id"] = str(c["_id"])
        c.pop("_id", None)
        contracts.append(c)

    return contracts


# --- Obter contrato específico ---
# Endpoint GET /contracts/{contract_id}
# Procura um contrato pelo ID.
# Caso não exista, devolve 404.
# Converte _id → id antes de devolver.
@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: str, user: str = Depends(get_current_user)):
    contract = contracts_collection.find_one({"_id": ObjectId(contract_id)})

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato não encontrado."
        )

    contract["id"] = str(contract["_id"])
    contract.pop("_id", None)

    return contract


# --- Atualizar contrato ---
# Endpoint PATCH /contracts/{contract_id}
# Permite atualização parcial: apenas os campos enviados são modificados.
# Se o contrato não existir, devolve 404.
# Após atualização, devolve o documento atualizado.
@router.patch("/{contract_id}", response_model=ContractOut)
def update_contract(contract_id: str, updated_data: dict, user: str = Depends(get_current_user)):
    existing = contracts_collection.find_one({"_id": ObjectId(contract_id)})

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato não encontrado."
        )

    contracts_collection.update_one(
        {"_id": ObjectId(contract_id)},
        {"$set": updated_data}
    )

    updated = contracts_collection.find_one({"_id": ObjectId(contract_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)

    return updated


# --- Eliminar contrato ---
# Endpoint DELETE /contracts/{contract_id}
# Remove um contrato da base de dados.
# Se não existir, devolve 404.
# Em caso de sucesso, devolve apenas HTTP 204 (sem conteúdo).
@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: str, user: str = Depends(get_current_user)):
    result = contracts_collection.delete_one({"_id": ObjectId(contract_id)})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contrato não encontrado."
        )

    return None
