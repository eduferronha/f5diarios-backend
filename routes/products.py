from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt, JWTError
from bson import ObjectId
from db import db
from schemas import ProductBase, ProductOut
from config import SECRET_KEY

products_collection = db["products"]
router = APIRouter(prefix="/products", tags=["Produtos"])


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


# --- Criar produto ---
@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
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


# --- Obter produto específico ---
@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, user: str = Depends(get_current_user)):
    product = products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.")
    product["id"] = str(product["_id"])
    product.pop("_id", None)
    return product


# --- Atualizar produto ---
@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: str, updated_data: dict, user: str = Depends(get_current_user)):
    existing = products_collection.find_one({"_id": ObjectId(product_id)})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.")
    products_collection.update_one({"_id": ObjectId(product_id)}, {"$set": updated_data})
    updated = products_collection.find_one({"_id": ObjectId(product_id)})
    updated["id"] = str(updated["_id"])
    updated.pop("_id", None)
    return updated


# --- Eliminar produto ---
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str, user: str = Depends(get_current_user)):
    result = products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.")
    return None
