from pymongo import MongoClient
from config import MONGODB_URL, DB_NAME

# Conexão com o MongoDB
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
