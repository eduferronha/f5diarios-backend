from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError
from bson import ObjectId
from db import activities_collection
from schemas import ActivityBase, ActivityOut
from config import SECRET_KEY


router = APIRouter(prefix="/activities", tags=["Atividades"])


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


@router.post("/", response_model=ActivityOut)
def create_activity(activity: ActivityBase, user: str = Depends(get_current_user)):
    new_activity = activity.dict()
    result = activities_collection.insert_one(new_activity)
    return {"id": str(result.inserted_id), **new_activity}


@router.get("/", response_model=list[ActivityOut])
def list_activities(user: str = Depends(get_current_user)):
    activities = []
    for a in activities_collection.find():
        a["id"] = str(a["_id"])
        a.pop("_id", None)
        activities.append(a)
    return activities


@router.put("/{activity_id}")
def update_activity(activity_id: str, updated: ActivityBase, user: str = Depends(get_current_user)):
    result = activities_collection.update_one(
        {"_id": ObjectId(activity_id)},
        {"$set": updated.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")
    return {"message": "Atividade atualizada com sucesso!"}


@router.delete("/{activity_id}")
def delete_activity(activity_id: str, user: str = Depends(get_current_user)):
    result = activities_collection.delete_one({"_id": ObjectId(activity_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")
    return {"message": "Atividade eliminada com sucesso!"}
