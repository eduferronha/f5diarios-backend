from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError
from bson import ObjectId
from db import clients_collection
from schemas import ClientBase, ClientOut
from config import SECRET_KEY


router = APIRouter(prefix="/clients", tags=["Clientes"])

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

@router.post("/", response_model=ClientOut)
def create_client(client: ClientBase, user: str = Depends(get_current_user)):
    new_client = client.dict()
    result = clients_collection.insert_one(new_client)
    return {"id": str(result.inserted_id), **new_client}

@router.get("/", response_model=list[ClientOut])
def list_clients(user: str = Depends(get_current_user)):
    clients = []
    for c in clients_collection.find():
        c["id"] = str(c["_id"])
        c.pop("_id", None)
        clients.append(c)
    return clients