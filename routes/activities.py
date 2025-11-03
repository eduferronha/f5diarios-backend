from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import activities_collection
from schemas import ActivityBase, ActivityOut
from config import SECRET_KEY

# Prefixo RESTful
router = APIRouter(prefix="/activities", tags=["Atividades"])


# --- Função auxiliar para autenticação ---
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


# --- Criar nova atividade ---
@router.post("/", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(activity: ActivityBase, user: str = Depends(get_current_user)):
    new_activity = activity.dict()
    result = activities_collection.insert_one(new_activity)
    return {"id": str(result.inserted_id), **new_activity}


# --- Listar todas as atividades ---
@router.get("/", response_model=list[ActivityOut])
def list_activities(user: str = Depends(get_current_user)):
    activities = []
    for a in activities_collection.find():
        a["id"] = str(a["_id"])
        a.pop("_id", None)
        activities.append(a)
    return activities


# --- Obter uma atividade por ID ---
@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: str, user: str = Depends(get_current_user)):
    activity = activities_collection.find_one({"_id": ObjectId(activity_id)})
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")
    activity["id"] = str(activity["_id"])
    activity.pop("_id", None)
    return activity


# --- Atualizar uma atividade ---
@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(activity_id: str, updated_data: dict, user: str = Depends(get_current_user)):
    existing = activities_collection.find_one({"_id": ObjectId(activity_id)})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")

    activities_collection.update_one({"_id": ObjectId(activity_id)}, {"$set": updated_data})
    updated = activities_collection.find_one({"_id": ObjectId(activity_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return updated


# --- Eliminar uma atividade ---
@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: str, user: str = Depends(get_current_user)):
    result = activities_collection.delete_one({"_id": ObjectId(activity_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")
    return None
