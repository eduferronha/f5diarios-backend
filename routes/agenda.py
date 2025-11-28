from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import AgendaBase, AgendaOut
from config import SECRET_KEY

# Coleção MongoDB dedicada à agenda (marcação de eventos).
agenda_collection = db["agenda"]

# Rota principal para marcações (prefixo /agenda).
# Contém endpoints CRUD para gerir eventos.
router = APIRouter(prefix="/agenda", tags=["Agenda"])


# --- Autenticação JWT ---
# Função dependência usada nas rotas para extrair e validar o token JWT.
# Requer o cabeçalho: "Authorization: Bearer <token>".
# Decodifica o JWT com SECRET_KEY e algoritmo HS256.
# Se for válido, devolve o campo 'sub' (username).
# Se estiver ausente ou inválido, responde com HTTP 401 (não autorizado).
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


# --- Criar marcação ---
# Endpoint POST /agenda/
# Recebe um objeto AgendaBase, converte-o para dict e insere-o na base de dados.
# Converte _id → id para o formato esperado pelo schema.
@router.post("/", response_model=AgendaOut, status_code=status.HTTP_201_CREATED)
def create_agenda(evento: AgendaBase, user: str = Depends(get_current_user)):
    new_event = evento.dict()

    result = agenda_collection.insert_one(new_event)
    new_event["id"] = str(result.inserted_id)

    return new_event


# --- Listar marcações ---
# Endpoint GET /agenda/
# Retorna todas as marcações registadas.
# Para cada documento, converte _id → id e remove o campo _id original.
@router.get("/", response_model=list[AgendaOut])
def list_agenda(user: str = Depends(get_current_user)):
    eventos = []

    for e in agenda_collection.find():
        e["id"] = str(e["_id"])
        e.pop("_id", None)
        eventos.append(e)

    return eventos


# --- Obter marcação por ID ---
# Endpoint GET /agenda/{agenda_id}
# Procura uma marcação pelo ID fornecido.
# Se não existir, devolve HTTP 404.
# Converte _id para id antes de devolver.
@router.get("/{agenda_id}", response_model=AgendaOut)
def get_agenda(agenda_id: str, user: str = Depends(get_current_user)):
    evento = agenda_collection.find_one({"_id": ObjectId(agenda_id)})

    if not evento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marcação não encontrada."
        )

    evento["id"] = str(evento["_id"])
    evento.pop("_id", None)

    return evento


# --- Atualizar marcação ---
# Endpoint PATCH /agenda/{agenda_id}
# Permite atualização parcial, recebendo apenas os campos modificados.
# Se a marcação não existir, devolve 404.
# Após atualizar, busca novamente o documento já modificado para devolver ao cliente.
@router.patch("/{agenda_id}", response_model=AgendaOut)
def update_agenda(agenda_id: str, updated_data: dict, user: str = Depends(get_current_user)):
    existing = agenda_collection.find_one({"_id": ObjectId(agenda_id)})

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marcação não encontrada."
        )

    agenda_collection.update_one(
        {"_id": ObjectId(agenda_id)},
        {"$set": updated_data}
    )

    updated = agenda_collection.find_one({"_id": ObjectId(agenda_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)

    return updated


# --- Eliminar marcação ---
# Endpoint DELETE /agenda/{agenda_id}
# Remove uma marcação existente pelo seu ID.
# Se não for encontrada, devolve 404.
# Em caso de sucesso, responde com HTTP 204 (sem conteúdo).
@router.delete("/{agenda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agenda(agenda_id: str, user: str = Depends(get_current_user)):
    result = agenda_collection.delete_one({"_id": ObjectId(agenda_id)})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Marcação não encontrada."
        )

    return None
