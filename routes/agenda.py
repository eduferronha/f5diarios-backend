from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import AgendaBase, AgendaOut
from config import SECRET_KEY

agenda_collection = db["agenda"]
router = APIRouter(prefix="/agenda", tags=["Agenda"])

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

# Criar marcação
@router.post("/", response_model=AgendaOut)
def create_agenda(evento: AgendaBase, user: str = Depends(get_current_user)):
    new_event = evento.dict()
    result = agenda_collection.insert_one(new_event)
    # ✅ Converter ObjectId para string antes de devolver
    new_event["id"] = str(result.inserted_id)
    return new_event

# Listar marcações
@router.get("/", response_model=list[AgendaOut])
def list_agenda(user: str = Depends(get_current_user)):
    eventos = []
    for e in agenda_collection.find():
        e["id"] = str(e["_id"])  # ✅ conversão obrigatória
        e.pop("_id", None)
        eventos.append(e)
    return eventos

@router.put("/{agenda_id}")
def update_agenda(agenda_id: str, updated: AgendaBase, user: str = Depends(get_current_user)):
    result = agenda_collection.update_one(
        {"_id": ObjectId(agenda_id)},
        {"$set": updated.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Marcação não encontrada.")
    return {"message": "Marcação atualizada com sucesso!"}


@router.delete("/{agenda_id}")
def delete_agenda(agenda_id: str, user: str = Depends(get_current_user)):
    result = agenda_collection.delete_one({"_id": ObjectId(agenda_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Marcação não encontrada.")
    return {"message": "Marcação eliminada com sucesso!"}
