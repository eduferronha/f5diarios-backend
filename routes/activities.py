from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import activities_collection
from schemas import ActivityBase, ActivityOut
from config import SECRET_KEY

# Rota principal para atividades (prefixo /activities).
# Contém endpoints CRUD para criar, consultar, atualizar e eliminar atividades.
router = APIRouter(prefix="/activities", tags=["Atividades"])


# --- Autenticação JWT ---
# Função dependência usada nas rotas para extrair e validar o token JWT.
# Espera o cabeçalho "Authorization: Bearer <token>".
# Decodifica o token com SECRET_KEY e algoritmo HS256.
# Se o token for válido, devolve o campo 'sub' (username) presente no JWT.
# Caso o token esteja ausente ou inválido, lança HTTP 401.
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


# --- Criar nova atividade ---
# Endpoint POST /activities/
# Recebe um objeto ActivityBase, converte para dict e guarda na base de dados.
# Devolve a atividade criada com o campo id (string) em vez de _id.
@router.post("/", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(activity: ActivityBase, user: str = Depends(get_current_user)):
    new_activity = activity.dict()

    result = activities_collection.insert_one(new_activity)

    return {"id": str(result.inserted_id), **new_activity}


# --- Listar todas as atividades ---
# Endpoint GET /activities/
# Devolve lista de atividades presentes na coleção.
# Converte _id → id (string) e remove o campo _id original.
@router.get("/", response_model=list[ActivityOut])
def list_activities(user: str = Depends(get_current_user)):
    activities = []

    for a in activities_collection.find():
        a["id"] = str(a["_id"])
        a.pop("_id", None)
        activities.append(a)

    return activities


# --- Obter uma atividade por ID ---
# Endpoint GET /activities/{activity_id}
# Procura uma atividade pelo seu ObjectId.
# Se não existir, devolve HTTP 404.
# Converte _id → id antes de devolver.
@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: str, user: str = Depends(get_current_user)):
    activity = activities_collection.find_one({"_id": ObjectId(activity_id)})

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atividade não encontrada."
        )

    activity["id"] = str(activity["_id"])
    activity.pop("_id", None)

    return activity


# --- Atualizar uma atividade ---
# Endpoint PATCH /activities/{activity_id}
# Recebe apenas os campos que devem ser atualizados.
# Se a atividade não existir, retorna 404.
# Após atualizar, busca novamente o documento e devolve-o com id em formato string.
@router.patch("/{activity_id}", response_model=ActivityOut)
def update_activity(activity_id: str, updated_data: dict, user: str = Depends(get_current_user)):
    existing = activities_collection.find_one({"_id": ObjectId(activity_id)})

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atividade não encontrada."
        )

    activities_collection.update_one(
        {"_id": ObjectId(activity_id)},
        {"$set": updated_data}
    )

    updated = activities_collection.find_one({"_id": ObjectId(activity_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)

    return updated


# --- Eliminar uma atividade ---
# Endpoint DELETE /activities/{activity_id}
# Remove o documento correspondente ao ID fornecido.
# Retorna HTTP 204 (sem conteúdo) em caso de sucesso.
# Se não existir, devolve 404.
@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: str, user: str = Depends(get_current_user)):
    result = activities_collection.delete_one({"_id": ObjectId(activity_id)})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atividade não encontrada."
        )

    return None
