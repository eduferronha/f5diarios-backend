from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import ProjectBase, ProjectOut
from config import SECRET_KEY

router = APIRouter(prefix="/projects", tags=["Projetos"])

projects_collection = db["projects"]
tasks_collection = db["tasks"]


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


# --- Converter "HH:MM" em horas decimais ---
def time_to_hours(time_str: str) -> float:
    try:
        h, m = map(int, time_str.split(":"))
        return h + m / 60
    except Exception:
        return 0.0


# --- Calcular total de horas faturadas de um cliente + contrato ---
def calcular_horas_gastas(cliente: str, contrato: str) -> float:
    tarefas = tasks_collection.find({"cliente": cliente, "contrato": contrato})
    total = 0.0
    for t in tarefas:
        tempo = t.get("tempo_faturado", "00:00")
        total += time_to_hours(tempo)
    return round(total, 2)


# --- Criar projeto ---
@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectBase, user: str = Depends(get_current_user)):
    existente = projects_collection.find_one({
        "cliente": project.cliente,
        "contrato": project.contrato,
        "descricao": project.descricao
    })
    if existente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Projeto já existe para este cliente e contrato.")

    horas_gastas = calcular_horas_gastas(project.cliente, project.contrato)
    new_project = project.dict()
    new_project["horas_gastas"] = horas_gastas

    result = projects_collection.insert_one(new_project)
    return {"id": str(result.inserted_id), **new_project}


# --- Listar todos os projetos ---
@router.get("/", response_model=list[ProjectOut])
def list_projects(user: str = Depends(get_current_user)):
    projects = []
    for p in projects_collection.find():
        p["id"] = str(p["_id"])
        p.pop("_id", None)
        projects.append(p)
    return projects


# --- Obter projeto por ID ---
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: str = Depends(get_current_user)):
    project = projects_collection.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    project["id"] = str(project["_id"])
    project.pop("_id", None)
    return project


# --- Atualizar projeto ---
@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, updated_data: dict, user: str = Depends(get_current_user)):
    existing = projects_collection.find_one({"_id": ObjectId(project_id)})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": updated_data})
    updated = projects_collection.find_one({"_id": ObjectId(project_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return updated


# --- Atualizar horas gastas ---
@router.patch("/update_hours/{project_id}", response_model=ProjectOut)
def update_project_hours(project_id: str, user: str = Depends(get_current_user)):
    project = projects_collection.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")

    cliente = project["cliente"]
    contrato = project["contrato"]
    novas_horas = calcular_horas_gastas(cliente, contrato)

    projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": {"horas_gastas": novas_horas}})
    project["horas_gastas"] = novas_horas
    project["id"] = str(project["_id"])
    project.pop("_id", None)
    return project


# --- Eliminar projeto ---
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: str = Depends(get_current_user)):
    result = projects_collection.delete_one({"_id": ObjectId(project_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    return None
