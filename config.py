import os
from dotenv import load_dotenv

load_dotenv()

# TODO: No futuro usar login com microsoft
# CLIENT_ID = os.getenv("CLIENT_ID")
# TENANT_ID = os.getenv("TENANT_ID")
# CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# REDIRECT_URI = os.getenv("REDIRECT_URI")

# AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
# SCOPE = ["User.Read"]

SECRET_KEY = os.getenv("SECRET_KEY")
MONGODB_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME")
API_KEY = os.getenv("API_KEY")

# print(">>> API_KEY carregada:", API_KEY)
