from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import ProductBase, ProductOut
from config import SECRET_KEY

products_collection = db["products"]
router = APIRouter(prefix="/products", tags=["Produtos"])

# --- Autenticação via JWT (igual aos outros módulos) ---
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

# --- Criar produto ---
@router.post("/", response_model=ProductOut)
def create_product(product: ProductBase, user: str = Depends(get_current_user)):
    new_product = product.dict()
    result = products_collection.insert_one(new_product)
    return {"id": str(result.inserted_id), **new_product}

# --- Listar produtos ---
@router.get("/", response_model=list[ProductOut])
def list_products(user: str = Depends(get_current_user)):
    products = []
    for p in products_collection.find():
        p["id"] = str(p["_id"])
        p.pop("_id", None)
        products.append(p)
    return products

# --- Atualizar produto ---
@router.put("/{product_id}")
def update_product(product_id: str, updated: ProductBase, user: str = Depends(get_current_user)):
    result = products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": updated.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return {"message": "Produto atualizado com sucesso!"}

# --- Eliminar produto ---
@router.delete("/{product_id}")
def delete_product(product_id: str, user: str = Depends(get_current_user)):
    result = products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return {"message": "Produto eliminado com sucesso!"}
