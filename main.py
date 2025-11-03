from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes import (
    auth, clients, contracts, presets, projects,
    products, activities, tasks, partners, agenda, users
)
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")

app = FastAPI(title="F5TCI Backend - Estrutura Modular")

origins = [
    "http://localhost:3000",                       # desenvolvimento local
    "https://f5diarios-frontend.vercel.app"        # produção (Vercel)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # apenas estes domínios podem aceder
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    # Permitir livre acesso a estas rotas
    if request.url.path in ["/", "/docs", "/openapi.json"] or request.url.path.startswith((
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

    # Verificação da API key para rotas protegidas
    client_key = request.headers.get("x-api-key")
    if client_key != API_KEY:
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    return await call_next(request)


@app.get("/")
def home():
    return {"message": "API F5TCI ativa 🚀"}
