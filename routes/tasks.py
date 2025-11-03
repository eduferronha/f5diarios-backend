from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import tasks_collection, users_collection
from db import db
from schemas import TaskBase, TaskOut
from config import SECRET_KEY
from datetime import datetime
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()
API_KEY = os.getenv("API_KEY")
# from dependencies import get_current_user  # o teu método de auth normal

tasks_collection = db["tasks"]
router = APIRouter(prefix="/tasks", tags=["Tarefas"])

# --- Função auxiliar: obter utilizador autenticado ---
def get_current_user_full(request: Request):
    """
    Extrai o username e o role do token JWT.
    Retorna um dicionário com {"username": ..., "role": ...}
    """
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ausente ou inválido."
        )

    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        role = payload.get("role", "user")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token sem utilizador válido."
            )
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )


def get_current_user(request: Request) -> str:
    """
    Extrai o utilizador (username) do token JWT no header Authorization.
    """
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
# @router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
# def create_task(task: TaskBase, username: str = Depends(get_current_user)):
#     """
#     Cria uma nova tarefa associada ao utilizador autenticado.
#     """
#     new_task = task.dict()
#     new_task["username"] = username

#     result = tasks_collection.insert_one(new_task)
#     created_task = tasks_collection.find_one({"_id": result.inserted_id})
#     created_task["id"] = str(created_task.pop("_id"))
#     return created_task

@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: Request,
    task: TaskBase,
    username: Optional[str] = Depends(lambda request=None: None)
):
    """
    Cria uma nova tarefa.
    - Se chamada com x-api-key → modo Copilot/PowerApps (usa email do utilizador e procura nome na coleção users)
    - Se chamada com JWT → modo Website (associa ao utilizador autenticado)
    """

    # 🔍 Log do corpo recebido (Power Automate / Website)
    try:
        body = await request.json()
        print("📩 [DEBUG] Dados recebidos no POST /tasks:")
        print(body)
    except Exception as e:
        print("⚠️ [DEBUG] Erro ao ler o corpo do pedido:", e)

    client_key = request.headers.get("x-api-key")

    # 🔹 1️⃣ Chamada via PowerApps / Copilot (x-api-key)
    if client_key and client_key == API_KEY:
        new_task = task.dict()

        # Tenta identificar o utilizador a partir do email enviado no header
        user_email = request.headers.get("x-user-email")
        print(f"📧 [DEBUG] Email recebido no header: {user_email}")

        if user_email:
            user = users_collection.find_one({"email": user_email})
            if user:
                new_task["username"] = user.get("nome", user_email)
                print(f"✅ [DEBUG] Utilizador encontrado na BD: {new_task['username']}")
            else:
                new_task["username"] = user_email  # fallback — se não existir na coleção
                print(f"⚠️ [DEBUG] Email não encontrado na coleção users, usando email como username.")
        else:
            new_task["username"] = "copilot"  # fallback genérico
            print(f"⚠️ [DEBUG] Nenhum email recebido, usando 'copilot' como username.")

        result = tasks_collection.insert_one(new_task)
        created_task = tasks_collection.find_one({"_id": result.inserted_id})
        created_task["id"] = str(created_task.pop("_id"))

        print("✅ [DEBUG] Tarefa criada com sucesso via x-api-key:", created_task)
        return created_task

    # 🔹 2️⃣ Chamada via JWT (Website)
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

                print("✅ [DEBUG] Tarefa criada com sucesso via JWT:", created_task)
                return created_task
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido.")

    # 🔹 3️⃣ Caso nenhum método de autenticação funcione
    raise HTTPException(status_code=401, detail="Não autorizado")


# --- Listar tarefas do utilizador autenticado ---
# @router.get("/", response_model=list[TaskOut])
# def list_user_tasks(username: str = Depends(get_current_user)):
#     """
#     Lista todas as tarefas criadas pelo utilizador autenticado.
#     """
#     tasks = []
#     for t in tasks_collection.find({"username": username}).sort("data", -1):
#         t["id"] = str(t.pop("_id"))
#         tasks.append(t)
#     return tasks

from typing import Optional
from fastapi import Query

@router.get("", response_model=list[dict])
@router.get("/", response_model=list[dict])
def list_user_tasks(
    request: Request,
    username: Optional[str] = Depends(lambda request=None: None),
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

    """
    Lista tarefas do utilizador autenticado (JWT)
    OU todas as tarefas se for chamada via x-api-key (Copilot/PowerApps),
    com possibilidade de filtrar por qualquer campo do schema TaskBase.
    """
    client_key = request.headers.get("x-api-key")

    # --- 1️⃣ Autenticação via API Key (Copilot/PowerApps) ---
    if client_key and client_key == API_KEY:
        filtro = {}

        # Cria o filtro dinâmico com base nos parâmetros recebidos
        params = {
            "descricao": descricao,
            "cliente": cliente,
            "parceiro": parceiro,
            "produto": produto,
            "contrato": contrato,
            "atividade": atividade,
            "data": data,
            "distancia_viagem": distancia_viagem,
            "tempo_viagem": tempo_viagem,
            "tempo_atividade": tempo_atividade,
            "tempo_faturado": tempo_faturado,
            "faturavel": faturavel,
            "viagem_faturavel": viagem_faturavel,
            "local": local,
            "valor_euro": valor_euro,
        }

        for campo, valor in params.items():
            if valor is not None:
                # Strings → pesquisa flexível (regex, case-insensitive)
                if isinstance(valor, str):
                    filtro[campo] = {"$regex": valor, "$options": "i"}
                else:
                    filtro[campo] = valor

        # 🔹 Query ao MongoDB com os filtros aplicados
        tasks = []
        for t in tasks_collection.find(filtro).sort("data", -1).limit(200):
            t["id"] = str(t.pop("_id"))
            tasks.append(t)
        return tasks

    # --- 2️⃣ Autenticação via JWT (modo Website) ---
    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        try:
            payload = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
            username = payload.get("sub")
            if username:
                filtro = {"username": username}

                # Também aplica filtros adicionais se o utilizador quiser filtrar
                params = {
                    "descricao": descricao,
                    "cliente": cliente,
                    "parceiro": parceiro,
                    "produto": produto,
                    "contrato": contrato,
                    "atividade": atividade,
                    "data": data,
                    "distancia_viagem": distancia_viagem,
                    "tempo_viagem": tempo_viagem,
                    "tempo_atividade": tempo_atividade,
                    "tempo_faturado": tempo_faturado,
                    "faturavel": faturavel,
                    "viagem_faturavel": viagem_faturavel,
                    "local": local,
                    "valor_euro": valor_euro,
                }

                for campo, valor in params.items():
                    if valor is not None:
                        if isinstance(valor, str):
                            filtro[campo] = {"$regex": valor, "$options": "i"}
                        else:
                            filtro[campo] = valor

                tasks = []
                for t in tasks_collection.find(filtro).sort("data", -1).limit(200):
                    t["id"] = str(t.pop("_id"))
                    tasks.append(t)
                return tasks
        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido.")

    # --- 3️⃣ Caso nenhum método de autenticação funcione ---
    raise HTTPException(status_code=401, detail="Não autorizado")


# --- Atualizar tarefa ---
@router.put("/{task_id}", status_code=status.HTTP_200_OK)
def update_task(task_id: str, updated: TaskBase, username: str = Depends(get_current_user)):
    """
    Atualiza uma tarefa, apenas se pertencer ao utilizador autenticado.
    """
    try:
        obj_id = ObjectId(task_id)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID inválido.")

    task = tasks_collection.find_one({"_id": obj_id})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada.")
    if task.get("username") != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para editar esta tarefa.")

    tasks_collection.update_one({"_id": obj_id}, {"$set": updated.dict()})
    return {"message": "Tarefa atualizada com sucesso!"}

# --- Eliminar tarefa ---
@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: str, username: str = Depends(get_current_user)):
    """
    Elimina uma tarefa, apenas se pertencer ao utilizador autenticado.
    """
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
    return {"message": "Tarefa eliminada com sucesso!"}



@router.get("/atividade")
def get_atividade(request: Request, mes: int):
    """
    Retorna todas as tarefas do mês selecionado (de todos os utilizadores),
    acessível apenas para administradores.
    """
    # 🔹 Extrai username e role diretamente do token (sem Depends)
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente ou inválido.")

    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        role = payload.get("role", "user")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido.")

    if role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado — apenas administradores podem ver todas as atividades.")

    # 🔹 Busca todas as tarefas do mês
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

        if not data:
            continue

        if data.month == mes:
            resultados.append({
                "username": t.get("username"),
                "cliente": t.get("cliente"),
                "contrato": t.get("contrato"),
                "data": data.strftime("%Y-%m-%d"),
                # "horas": t.get("tempo_atividade") or t.get("tempo_faturado") or "00:00"
                "tempo_atividade": t.get("tempo_atividade")
            })

    resultados.sort(key=lambda x: (x["username"], x["data"]))
    return resultados
