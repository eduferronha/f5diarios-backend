from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import (
    auth, clients, contracts, presets, projects,
    products, activities, tasks, partners, agenda, users, auth_microsoft
)
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="F5TCI Backend - Estrutura Modular")

# Lista de origens autorizadas (local + produção)
origins = [
    "http://localhost:3000",                       
    "https://f5diarios-frontend.vercel.app"        
]

# Middleware CORS configurado corretamente
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registo das rotas
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
app.include_router(auth_microsoft.router)

@app.get("/")
def home():
    return {"message": "API F5TCI ativa 🚀"}
