from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import clients_collection
from schemas import ClientBase, ClientOut
from config import SECRET_KEY

# Prefixo RESTful
router = APIRouter(prefix="/clients", tags=["Clientes"])

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

# --- Criar novo cliente ---
@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(client: ClientBase, user: str = Depends(get_current_user)):
    new_client = client.dict()
    result = clients_collection.insert_one(new_client)
    return {"id": str(result.inserted_id), **new_client}

# --- Listar todos os clientes ---
@router.get("/", response_model=list[ClientOut])
def list_clients(user: str = Depends(get_current_user)):
    clients = []
    for c in clients_collection.find():
        c["id"] = str(c["_id"])
        c.pop("_id", None)
        clients.append(c)
    return clients

# --- Obter cliente por ID ---
@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: str, user: str = Depends(get_current_user)):
    client = clients_collection.find_one({"_id": ObjectId(client_id)})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    client["id"] = str(client["_id"])
    client.pop("_id", None)
    return client

# --- Atualizar cliente ---
@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: str, client_data: dict, user: str = Depends(get_current_user)):
    existing = clients_collection.find_one({"_id": ObjectId(client_id)})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")

    clients_collection.update_one({"_id": ObjectId(client_id)}, {"$set": client_data})
    updated = clients_collection.find_one({"_id": ObjectId(client_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return updated

# --- Eliminar cliente ---
@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: str, user: str = Depends(get_current_user)):
    result = clients_collection.delete_one({"_id": ObjectId(client_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
    return None
