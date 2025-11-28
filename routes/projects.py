from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import ProjectBase, ProjectOut
from config import SECRET_KEY

# Rotas relacionadas com gestão de projetos
router = APIRouter(prefix="/projects", tags=["Projetos"])

# Coleções MongoDB utilizadas por este módulo
projects_collection = db["projects"]
tasks_collection = db["tasks"]


# --- Autenticação JWT ---
# Extrai e valida o token JWT enviado no cabeçalho Authorization.
# Caso seja válido, devolve o identificador (username) associado ao token.
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


# --- Converter "HH:MM" para valor decimal em horas ---
# Aceita um valor no formato "hora:minuto" e converte para número decimal.
def time_to_hours(time_str: str) -> float:
    try:
        h, m = map(int, time_str.split(":"))
        return h + m / 60
    except Exception:
        return 0.0


# --- Calcular total de horas associadas a um cliente e contrato ---
# Soma o tempo faturado em todas as tarefas que pertençam ao mesmo cliente e contrato.
def calcular_horas_gastas(cliente: str, contrato: str) -> float:
    tarefas = tasks_collection.find({"cliente": cliente, "contrato": contrato})
    total = 0.0

    for t in tarefas:
        tempo = t.get("tempo_faturado", "00:00")
        total += time_to_hours(tempo)

    return round(total, 2)


# --- Criar projeto ---
# Regista um novo projeto associado a um cliente e contrato.
# Calcula automaticamente as horas já gastas com base nas tarefas existentes.
@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectBase, user: str = Depends(get_current_user)):
    existente = projects_collection.find_one({
        "cliente": project.cliente,
        "contrato": project.contrato,
        "descricao": project.descricao
    })

    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Projeto já existe para este cliente e contrato."
        )

    horas_gastas = calcular_horas_gastas(project.cliente, project.contrato)

    new_project = project.dict()
    new_project["horas_gastas"] = horas_gastas

    result = projects_collection.insert_one(new_project)

    return {"id": str(result.inserted_id), **new_project}


# --- Listar todos os projetos ---
# Devolve a lista completa de projetos armazenados na coleção.
@router.get("/", response_model=list[ProjectOut])
def list_projects(user: str = Depends(get_current_user)):
    projects = []

    for p in projects_collection.find():
        p["id"] = str(p["_id"])
        p.pop("_id", None)
        projects.append(p)

    return projects


# --- Obter projeto ---
# Recolhe um projeto específico a partir do seu identificador.
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: str = Depends(get_current_user)):
    project = projects_collection.find_one({"_id": ObjectId(project_id)})

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado."
        )

    project["id"] = str(project["_id"])
    project.pop("_id", None)

    return project


# --- Atualizar projeto ---
# Permite modificar parcialmente os dados de um projeto.
# Apenas os campos enviados serão alterados.
@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, updated_data: dict, user: str = Depends(get_current_user)):
    existing = projects_collection.find_one({"_id": ObjectId(project_id)})

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado."
        )

    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": updated_data}
    )

    updated = projects_collection.find_one({"_id": ObjectId(project_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)

    return updated


# --- Atualizar horas gastas ---
# Recalcula as horas associadas ao projeto com base nas tarefas do mesmo cliente/contrato.
# Substitui o valor total no documento do projeto.
@router.patch("/update_hours/{project_id}", response_model=ProjectOut)
def update_project_hours(project_id: str, user: str = Depends(get_current_user)):
    project = projects_collection.find_one({"_id": ObjectId(project_id)})

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado."
        )

    cliente = project["cliente"]
    contrato = project["contrato"]

    novas_horas = calcular_horas_gastas(cliente, contrato)

    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"horas_gastas": novas_horas}}
    )

    project["horas_gastas"] = novas_horas
    project["id"] = str(project["_id"])
    project.pop("_id", None)

    return project


# --- Eliminar projeto ---
# Remove o projeto identificado pelo ID fornecido.
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: str = Depends(get_current_user)):
    result = projects_collection.delete_one({"_id": ObjectId(project_id)})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado."
        )

    return None
