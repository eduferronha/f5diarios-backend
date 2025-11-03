from fastapi import FastAPI
from routes import auth, clients, contracts, presets, projects, products, activities, tasks, partners, agenda,users
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")


app = FastAPI(title="F5TCI Backend - Estrutura Modular")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui as rotas do backend
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(contracts.router)
app.include_router(products.router)
app.include_router(activities.router)
app.include_router(partners.router)
app.include_router(tasks.router)
app.include_router(agenda.router)
app.include_router(users.router)
app.include_router(presets.router)
app.include_router(projects.router)

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    # Permitir sempre o método OPTIONS (pré-flight CORS)
    if request.method == "OPTIONS":
        response = JSONResponse(content={"detail": "CORS preflight"})
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, x-api-key"
        return response

    # Permitir livre acesso a algumas rotas
    if request.url.path in [
        "/",
        "/docs",
        "/openapi.json"
    ] or request.url.path.startswith((
        "/auth",
        "/tasks",
        "/clients",
        "/contracts",
        "/products",
        "/activities",
        "/partners",
        "/agenda",
        "/users",
        "/presets",
        "/projects",
    )):
        return await call_next(request)

    # Verificação da API key
    client_key = request.headers.get("x-api-key")
    if client_key != API_KEY:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    return await call_next(request)



@app.get("/")
def home():
    return {"message": "API F5TCI ativa 🚀"}
