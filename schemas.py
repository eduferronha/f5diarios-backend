from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime

# --- Utilizadores ---

class UserBase(BaseModel):
    nome: Optional[str] = None
    username: str
    email: Optional[str] = None
    empresa_base: Optional[str] = None
    chave: Optional[str] = None
    role: Optional[str] = "user"  # valores possíveis: "admin" ou "user"


# Modelo para criação (exige password)
class UserCreate(UserBase):
    password: str


# Modelo para login (username + password)
class UserLogin(BaseModel):
    username: str
    password: str


# Modelo de saída (usado em listagem e edição no admin)
class UserOut(UserBase):
    id: str


# Modelo de resposta ao login (retorna token JWT)
class UserToken(BaseModel):
    token: str
    username: str
    role: str

# --- Clientes ---

class ClientBase(BaseModel):
    nome: str
    empresa: Optional[str] = None
    pais: Optional[str] = None
    distancia_km: Optional[float] = None
    tempo_viagem: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    localidade: Optional[str] = None

class ClientOut(ClientBase):
    id: str


# --- Contratos ---
class ContractBase(BaseModel):
    contrato: str
    estado: str
    empresa: str
    cliente: str
    p_manager: Optional[str] = None
    comercial: Optional[str] = None
    data_inicio: str
    data_fim: str
    valor_d: Optional[float] = None
    valor_euro: Optional[float] = None

class ContractOut(ContractBase):
    id: str

# --- Produtos ---


class ProductBase(BaseModel):
    produto: str
    empresa: Optional[str] = None

class ProductOut(ProductBase):
    id: str


# --- Atividades ---

class ActivityBase(BaseModel):
    atividade: str
    custo_hora: float = 0

class ActivityOut(ActivityBase):
    id: str


# --- Tarefas ---

class TaskBase(BaseModel):
    descricao: Optional[str] = None
    cliente: Optional[str] = None
    parceiro: Optional[str] = None
    produto: Optional[str] = None
    contrato: Optional[str] = None
    atividade: Optional[str] = None
    data: Optional[str] = None
    distancia_viagem: Optional[Union[str, float]] = 0
    tempo_viagem: Optional[str] = "00:00"
    tempo_atividade: Optional[str] = "00:00"
    tempo_faturado: Optional[str] = "00:00"
    faturavel: Optional[str] = "No"
    viagem_faturavel: Optional[str] = "No"
    local: Optional[str] = "Employee House"
    valor_euro: Optional[Union[str, float]] = 0

class TaskOut(TaskBase):
    id: str
    username: str


# --- Parceiros ---

class ParceiroBase(BaseModel):
    parceiro: Optional[str] = None
    empresa: Optional[str] = None
    pais: Optional[str] = None
    localidade: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None

class ParceiroOut(ParceiroBase):
    id: str


# --- Agenda ---

class AgendaBase(BaseModel):
    utilizador: str
    data: str
    hora_inicio: str
    hora_fim: str
    descricao: Optional[str] = None

class AgendaOut(AgendaBase):
    id: str


# --- Projetos ---

class ProjectBase(BaseModel):
    cliente: str  # nome do cliente
    contrato: str  # contrato associado ao cliente
    descricao: Optional[str] = None
    horas_contratadas: Optional[float] = 0.0
    horas_gastas: Optional[float] = 0.0  # será calculado com base nas tarefas


class ProjectOut(ProjectBase):
    id: str


# --- Presets ----

class PresetBase(BaseModel):
    nome: str                            # nome amigável do preset (ex: "Cliente X - Suporte")
    descricao: Optional[str] = None
    cliente: Optional[str] = None
    parceiro: Optional[str] = None
    produto: Optional[str] = None
    contrato: Optional[str] = None
    atividade: Optional[str] = None
    data: Optional[str] = None
    distancia_viagem: Optional[Union[str, float]] = 0
    tempo_viagem: Optional[str] = "00:00"
    tempo_atividade: Optional[str] = "00:00"
    tempo_faturado: Optional[str] = "00:00"
    faturavel: Optional[str] = "No"
    viagem_faturavel: Optional[str] = "No"
    local: Optional[str] = "Employee House"
    valor_euro: Optional[Union[str, float]] = 0
    # username: str   
    username: Optional[str] = None


class PresetOut(PresetBase):
    id: str