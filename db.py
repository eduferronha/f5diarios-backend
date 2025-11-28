import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Carrega variáveis do .env (funciona localmente)
load_dotenv()

# Lê variáveis de ambiente (Railway também usa estas)
MONGODB_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME")



# Verificação para evitar erro se faltar variável
if not MONGODB_URL:
    raise ValueError("❌ MONGO_URI não foi definida. Verifica as variáveis no Railway.")
if not DB_NAME:
    raise ValueError("❌ DB_NAME não foi definida. Verifica as variáveis no Railway.")

# Conexão com MongoDB
client = MongoClient(MONGODB_URL)
db = client[DB_NAME]


# Coleções principais da base de dados
users_collection = db["users"]
clients_collection = db["clients"]
contracts_collection = db["contracts"]
products_collection = db["products"]
partners_collection = db["partners"]
activities_collection = db["activities"]
projects_collection = db["projects"]
presets_collection = db["presets"]
tasks_collection = db["tasks"]



