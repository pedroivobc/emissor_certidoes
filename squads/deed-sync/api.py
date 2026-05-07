"""
deed-sync api.py
API FastAPI local para emissão automatizada de certidões.

Uso:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Endpoint:
    POST /emitir
    Body: { "cpf": "000.000.000-00", "nome": "Nome Completo" }
"""
import re
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from scraper import emitir_certidoes

app = FastAPI(
    title="deed-sync API",
    description="Emissão automatizada de 6 certidões de pessoa física brasileira.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Schema ─────────────────────────────────────────────────────────────────────

class EmitirRequest(BaseModel):
    cpf: str
    nome: str
    birthdate: str | None = None  # AAAA-MM-DD, obrigatório para PF

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: str) -> str:
        digitos = re.sub(r"\D", "", v)
        if len(digitos) not in (11, 14):
            raise ValueError("CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos numéricos.")
        return v

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Nome deve ter ao menos 3 caracteres.")
        return v


class EmitirResponse(BaseModel):
    """Resposta flexível — reflete a estrutura do novo scraper Infosimples."""
    sucesso_geral: bool
    documento: str
    tipo: str
    nome: str
    timestamp: str
    duracao_segundos: float
    certidoes: dict
    tjmg: dict

    model_config = {"extra": "allow"}  # permite campos extras sem erro


# ─── Endpoints ───────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {"service": "deed-sync", "status": "online", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.post("/emitir", response_model=EmitirResponse, tags=["Certidões"])
async def emitir(req: EmitirRequest):
    """
    Emite as certidões para o CPF/CNPJ e Nome informados.

    - **cpf**: CPF (11 dígitos) ou CNPJ (14 dígitos) do consultado (com ou sem formatação)
    - **nome**: Nome completo do consultado
    - **birthdate**: Data de nascimento em formato AAAA-MM-DD (obrigatório para CPF/PF)

    Retorna o status de cada certidão, dados estruturados e caminhos dos PDFs gerados.
    """
    try:
        resultado = await emitir_certidoes(req.cpf, req.nome, req.birthdate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno na automação: {str(e)}")

    return resultado
