from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from jose import jwt, JWTError
from bson import ObjectId
from db import db, tasks_collection, users_collection
from schemas import TaskBase, TaskOut
from config import SECRET_KEY
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")

router = APIRouter(prefix="/tasks", tags=["Tarefas"])


# --- Autenticação JWT ---
def get_current_user(request: Request) -> str:
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente ou inválido.")
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sem utilizador válido.")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")


# --- Criar nova tarefa ---
@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(request: Request, task: TaskBase):
    client_key = request.headers.get("x-api-key")

    # --- 1️⃣ Modo PowerApps / Copilot ---
    if client_key and client_key == API_KEY:
        new_task = task.dict()
        user_email = request.headers.get("x-user-email")

        if user_email:
            user = users_collection.find_one({"email": user_email})
            new_task["username"] = user.get("nome", user_email) if user else user_email
        else:
            new_task["username"] = "copilot"

        result = tasks_collection.insert_one(new_task)
        created_task = tasks_collection.find_one({"_id": result.inserted_id})
        created_task["id"] = str(created_task.pop("_id"))
        return created_task

    # --- 2️⃣ Modo Website (JWT) ---
    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        try:
            payload = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
            username = payload.get("sub")
            if username:
                new_task = task.dict()
                new_task["username"] = username
                result = tasks_collection.insert_one(new_task)
                created_task = tasks_collection.find_one({"_id": result.inserted_id})
                created_task["id"] = str(created_task.pop("_id"))
                return created_task
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")


# --- Listar tarefas ---
@router.get("/", response_model=list[dict])
def list_tasks(
    request: Request,
    descricao: Optional[str] = Query(None),
    cliente: Optional[str] = Query(None),
    parceiro: Optional[str] = Query(None),
    produto: Optional[str] = Query(None),
    contrato: Optional[str] = Query(None),
    atividade: Optional[str] = Query(None),
    data: Optional[str] = Query(None),
    distancia_viagem: Optional[float] = Query(None),
    tempo_viagem: Optional[str] = Query(None),
    tempo_atividade: Optional[str] = Query(None),
    tempo_faturado: Optional[str] = Query(None),
    faturavel: Optional[str] = Query(None),
    viagem_faturavel: Optional[str] = Query(None),
    local: Optional[str] = Query(None),
    valor_euro: Optional[float] = Query(None)
):
    client_key = request.headers.get("x-api-key")

    # --- 1️⃣ Autenticação via API Key ---
    if client_key and client_key == API_KEY:
        filtro = {}
        params = locals()
        for campo, valor in params.items():
            if campo not in ["request", "client_key"] and valor is not None:
                filtro[campo] = {"$regex": valor, "$options": "i"} if isinstance(valor, str) else valor

        tasks = []
        for t in tasks_collection.find(filtro).sort("data", -1).limit(200):
            t["id"] = str(t.pop("_id"))
            tasks.append(t)
        return tasks

    # --- 2️⃣ Autenticação via JWT ---
    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        try:
            payload = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
            username = payload.get("sub")
            if username:
                filtro = {"username": username}
                params = locals()
                for campo, valor in params.items():
                    if campo not in ["request", "client_key", "token", "username"] and valor is not None:
                        filtro[campo] = {"$regex": valor, "$options": "i"} if isinstance(valor, str) else valor

                tasks = []
                for t in tasks_collection.find(filtro).sort("data", -1).limit(200):
                    t["id"] = str(t.pop("_id"))
                    tasks.append(t)
                return tasks
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")


# --- Atualizar tarefa ---
@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, updated_data: dict, username: str = Depends(get_current_user)):
    try:
        obj_id = ObjectId(task_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID inválido.")

    task = tasks_collection.find_one({"_id": obj_id})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada.")
    if task.get("username") != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para editar esta tarefa.")

    tasks_collection.update_one({"_id": obj_id}, {"$set": updated_data})
    updated = tasks_collection.find_one({"_id": obj_id})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return updated


# --- Eliminar tarefa ---
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, username: str = Depends(get_current_user)):
    try:
        obj_id = ObjectId(task_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID inválido.")

    task = tasks_collection.find_one({"_id": obj_id})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada.")
    if task.get("username") != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para eliminar esta tarefa.")

    tasks_collection.delete_one({"_id": obj_id})
    return None


# --- Atividade mensal (admin only) ---
@router.get("/atividade")
def get_atividade(request: Request, mes: int):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente ou inválido.")

    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role", "user")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado — apenas administradores podem ver todas as atividades.")

    tarefas = list(tasks_collection.find({}))
    resultados = []

    for t in tarefas:
        data_str = t.get("data")
        if not data_str:
            continue
        data = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                data = datetime.strptime(data_str, fmt)
                break
            except ValueError:
                continue
        if data and data.month == mes:
            resultados.append({
                "username": t.get("username"),
                "cliente": t.get("cliente"),
                "contrato": t.get("contrato"),
                "data": data.strftime("%Y-%m-%d"),
                "tempo_atividade": t.get("tempo_atividade")
            })

    resultados.sort(key=lambda x: (x["username"], x["data"]))
    return resultados
