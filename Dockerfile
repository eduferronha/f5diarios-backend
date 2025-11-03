# Etapa base
FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Copia o backend para dentro da imagem
COPY backend/ /app

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta padrão do Railway
EXPOSE 8000

# Comando para arrancar o servidor FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
