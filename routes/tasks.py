from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
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

tasks_collection = db["tasks"]
router = APIRouter(prefix="/tasks", tags=["Tarefas"])


# --- Autenticação completa (username + role) ---
# Obtém tanto o utilizador autenticado como o papel associado (user/admin).
def get_current_user_full(request: Request):
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


# --- Autenticação simples (apenas username) ---
# Utilizado por operações que apenas necessitam identificar o autor da tarefa.
def get_current_user(request: Request) -> str:
    token = request.headers.get("Authorization")

    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente ou inválido.")

    token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")

        if not username:
            raise HTTPException(status_code=401, detail="Token sem utilizador válido.")

        return username

    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido.")


# --- Criar nova tarefa ---
# Este endpoint suporta dois modos:
# 1) x-api-key → utilizado por Copilot/PowerApps
# 2) JWT → utilizado pelo website
@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: Request,
    task: TaskBase,
    username: Optional[str] = Depends(lambda request=None: None)
):
    """
    Regista uma nova tarefa associada a um utilizador.
    Suporta dois tipos de origem:
    • PowerApps / Copilot — identifica o utilizador através de headers especiais
    • Website — utiliza o JWT de autenticação
    """

    # Log de depuração do corpo recebido
    try:
        body = await request.json()
        print("📩 [DEBUG] Dados recebidos no POST /tasks:")
        print(body)
    except Exception as e:
        print("⚠️ [DEBUG] Erro ao ler o corpo do pedido:", e)

    client_key = request.headers.get("x-api-key")

    # --- 1️⃣ Origem PowerApps / Copilot ---
    if client_key and client_key == API_KEY:
        new_task = task.dict()

        # Tenta identificar o utilizador com base no email enviado no header
        user_email = request.headers.get("x-user-email")
        print(f"📧 [DEBUG] Email recebido no header: {user_email}")

        if user_email:
            user = users_collection.find_one({"email": user_email})

            if user:
                new_task["username"] = user.get("nome", user_email)
                print(f"✅ [DEBUG] Utilizador encontrado: {new_task['username']}")
            else:
                new_task["username"] = user_email
                print("⚠️ [DEBUG] Email não registado, usando o próprio email como username.")
        else:
            new_task["username"] = "copilot"
            print("⚠️ [DEBUG] Nenhum email recebido — usando 'copilot'.")

        result = tasks_collection.insert_one(new_task)
        created_task = tasks_collection.find_one({"_id": result.inserted_id})
        created_task["id"] = str(created_task.pop("_id"))

        print("✅ [DEBUG] Tarefa criada via x-api-key:", created_task)
        return created_task

    # --- 2️⃣ Origem Website via JWT ---
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

                print("✅ [DEBUG] Tarefa criada via JWT:", created_task)
                return created_task

        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido.")

    # --- 3️⃣ Sem autenticação válida ---
    raise HTTPException(status_code=401, detail="Não autorizado")


# --- Listar tarefas ---
# Permite listar tarefas com filtros dinâmicos.
# Suporta:
# • PowerApps/Copilot — acesso a todas as tarefas
# • Website — apenas tarefas do utilizador autenticado
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
    Lista tarefas, com opção de aplicar filtros flexíveis.
    O comportamento depende da origem:
    • PowerApps/Copilot → acesso completo
    • Website → apenas tarefas associadas ao utilizador autenticado
    """

    client_key = request.headers.get("x-api-key")

    # --- 1️⃣ Modo PowerApps/Copilot (x-api-key) ---
    if client_key and client_key == API_KEY:
        filtro = {}

        # Prepara dinamicamente os filtros
        parametros = {
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
            "valor_euro": valor_euro
        }

        for campo, valor in parametros.items():
            if valor is not None:
                filtro[campo] = (
                    {"$regex": valor, "$options": "i"} if isinstance(valor, str) else valor
                )

        tasks = []
        for t in tasks_collection.find(filtro).sort("data", -1).limit(200):
            t["id"] = str(t.pop("_id"))
            tasks.append(t)

        return tasks

    # --- 2️⃣ Modo Website (JWT) ---
    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        try:
            payload = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
            username = payload.get("sub")

            if username:
                filtro = {"username": username}

                # Também aplica filtros opcionais fornecidos pelo utilizador
                parametros = {
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
                    "valor_euro": valor_euro
                }

                for campo, valor in parametros.items():
                    if valor is not None:
                        filtro[campo] = (
                            {"$regex": valor, "$options": "i"} if isinstance(valor, str) else valor
                        )

                tasks = []
                for t in tasks_collection.find(filtro).sort("data", -1).limit(200):
                    t["id"] = str(t.pop("_id"))
                    tasks.append(t)

                return tasks

        except JWTError:
            raise HTTPException(status_code=401, detail="Token inválido.")

    # --- 3️⃣ Sem autenticação válida ---
    raise HTTPException(status_code=401, detail="Não autorizado")


# --- Administrador: listar todas as tarefas ---
@router.get("/all", response_model=list[dict])
def list_all_tasks_admin(request: Request):
    """
    Lista todas as tarefas existentes,
    acessível apenas para utilizadores com papel de administrador.
    """

    token = request.headers.get("Authorization")

    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente ou inválido.")

    token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role", "user")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido.")

    if role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado.")

    tasks = []
    for t in tasks_collection.find().sort("data", -1):
        t["id"] = str(t.pop("_id"))
        tasks.append(t)

    return tasks


# --- Atualizar tarefa ---
@router.put("/{task_id}", status_code=status.HTTP_200_OK)
def update_task(task_id: str, updated: TaskBase, username: str = Depends(get_current_user)):
    """
    Atualiza os detalhes de uma tarefa,
    desde que esta pertença ao utilizador autenticado.
    """

    try:
        obj_id = ObjectId(task_id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido.")

    task = tasks_collection.find_one({"_id": obj_id})

    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    if task.get("username") != username:
        raise HTTPException(status_code=403, detail="Sem permissão para editar esta tarefa.")

    tasks_collection.update_one({"_id": obj_id}, {"$set": updated.dict()})
    return {"message": "Tarefa atualizada com sucesso!"}


# --- Eliminar tarefa ---
@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: str, username: str = Depends(get_current_user)):
    """
    Elimina uma tarefa pertencente ao utilizador autenticado.
    """

    try:
        obj_id = ObjectId(task_id)
    except:
        raise HTTPException(status_code=400, detail="ID inválido.")

    task = tasks_collection.find_one({"_id": obj_id})

    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    if task.get("username") != username:
        raise HTTPException(status_code=403, detail="Sem permissão para eliminar esta tarefa.")

    tasks_collection.delete_one({"_id": obj_id})
    return {"message": "Tarefa eliminada com sucesso!"}


# --- Administrador: obter atividade mensal ---
@router.get("/atividade")
def get_atividade(request: Request, mes: int):
    """
    Obtém todas as tarefas de um mês específico,
    acessível apenas para utilizadores administradores.
    """

    token = request.headers.get("Authorization")

    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente ou inválido.")

    token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role", "user")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido.")

    if role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado.")

    tarefas = list(tasks_collection.find({}))
    resultados = []

    # Avalia vários formatos de data suportados
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
                "tempo_atividade": t.get("tempo_atividade")
            })

    resultados.sort(key=lambda x: (x["username"], x["data"]))
    return resultados
