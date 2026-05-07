"""
deed-sync scraper.py  (v2 — Infosimples API)
Orquestrador principal para emissão automatizada de certidões.

Certidões cobertas:
  - TST/CNDT      → Infosimples API (paralelo)
  - TRF6 Cível    → Infosimples API (paralelo)           [PJE]
  - TRF6 EPROC    → Playwright (paralelo)                [EPROC — Fase 3.5]
  - TRT3/CEAT     → Infosimples API (paralelo)
  - PGFN          → Infosimples API (paralelo, com fallback 2via → nova)
  - TJMG/RUPE     → Playwright + Gmail OTP

Uso via API:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Uso via CLI:
    python scraper.py <CPF_ou_CNPJ> <Nome> [birthdate_AAAA-MM-DD]
    python scraper.py 11773105620 "Pedro Ivo Batista Clemente" 1990-01-15
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

from infosimples_client import consultar_pgfn, consultar_trf6, consultar_trt3, consultar_tst
from trf6_eproc_scraper import consultar_trf6_eproc
from tjmg_scraper import consultar_tjmg

# ─── Configuração ──────────────────────────────────────────────────────────────

# Carrega variáveis de ambiente do arquivo credenciais.env (2 níveis acima deste arquivo)
_ENV_PATH = Path(__file__).parents[2] / "credenciais.env"
load_dotenv(dotenv_path=_ENV_PATH)

# Configura logging para stdout com timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("deed-sync.scraper")

OUTPUT_BASE = Path(__file__).parent / "output" / "pdfs"

# Dados fixos do solicitante (usados pelo TJMG na Fase 3)
SOLICITANTE = {
    "nome":  "Pedro Ivo Batista Clemente",
    "cpf":   "117.731.056-20",
    "email": "contato@clementeassessoria.com",
}

# Timeout global: 10 minutos (Infosimples pode demorar até ~10 min em horários de pico)
GLOBAL_TIMEOUT_SECONDS = 600


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _sanitizar_documento(doc: str) -> str:
    """Remove todos os caracteres não-numéricos."""
    return "".join(c for c in doc if c.isdigit())


def _detectar_tipo(documento: str) -> str:
    """Retorna 'PF' para CPF (11 dígitos) ou 'PJ' para CNPJ (14 dígitos)."""
    if len(documento) == 11:
        return "PF"
    elif len(documento) == 14:
        return "PJ"
    else:
        raise ValueError(
            f"Documento inválido: esperado 11 (CPF) ou 14 (CNPJ) dígitos, "
            f"recebido {len(documento)} dígitos."
        )


def _timestamp_arquivo() -> str:
    """Retorna timestamp no formato YYYYMMDD_HHMMSS para nome de arquivo."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _caminho_pdf(documento: str, endpoint: str, ts: str) -> Path:
    """Monta o caminho absoluto do PDF: output/pdfs/{documento}/{endpoint}_{ts}.pdf"""
    pasta = OUTPUT_BASE / documento
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"{endpoint}_{ts}.pdf"


def _validar_pdf(caminho: Path) -> bool:
    """Valida que os primeiros 4 bytes são '%PDF'."""
    try:
        with open(caminho, "rb") as f:
            return f.read(4) == b"%PDF"
    except Exception:
        return False


def _resultado_excecao(endpoint_nome: str, exc: Exception) -> dict:
    """Constrói resultado de erro para exceção não tratada do consultar_*.

    Última linha de defesa: se uma exceção escapou do try/except interno
    do infosimples_client, captura aqui e mantém estrutura consistente.
    """
    logger.error("%s — exceção não tratada chegou ao orquestrador: %s", endpoint_nome, exc)
    base = {
        "sucesso": False,
        "code": None,
        "code_message": None,
        "pdf_path": None,
        "pdf_url_temporaria": None,
        "dados": None,
        "erro": f"Exceção não tratada em {endpoint_nome}: {exc}",
    }
    if endpoint_nome.upper() == "PGFN":
        base["modo"] = None
        base["tentativas"] = 0
    return base


# ─── Download de PDF ───────────────────────────────────────────────────────────

async def _baixar_pdf(
    url: str,
    destino: Path,
    session: aiohttp.ClientSession,
    endpoint_nome: str,
) -> bool:
    """
    Baixa o PDF da URL temporária e salva em destino.

    Retorna True se sucesso (arquivo válido), False caso contrário.
    Não levanta exceção — falha de download é tratada como não-fatal.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=120)
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            conteudo = await resp.read()

        # Verifica assinatura PDF antes de salvar
        if len(conteudo) < 4 or conteudo[:4] != b"%PDF":
            logger.warning(
                "%s — Conteúdo baixado não é um PDF válido (primeiros bytes: %s)",
                endpoint_nome, conteudo[:4],
            )
            return False

        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
        logger.info("%s — PDF salvo: %s (%d bytes)", endpoint_nome, destino.name, len(conteudo))
        return True

    except Exception as exc:
        logger.error("%s — Falha ao baixar PDF: %s", endpoint_nome, exc)
        return False


# ─── Orquestrador de downloads ─────────────────────────────────────────────────

async def _processar_e_baixar(
    endpoint_nome: str,
    resultado_api: dict,
    destino: Path,
    session: aiohttp.ClientSession,
) -> dict:
    """
    Complementa o resultado da API com o download do PDF.

    Popula resultado["pdf_path"] se o download for bem-sucedido.
    Não altera resultado["sucesso"] — falha de download é separada da falha de API.
    """
    resultado = dict(resultado_api)  # cópia para não modificar o original

    if resultado.get("sucesso") and resultado.get("pdf_url_temporaria"):
        url = resultado["pdf_url_temporaria"]
        ok = await _baixar_pdf(url, destino, session, endpoint_nome)
        if ok:
            resultado["pdf_path"] = str(destino.resolve())
        else:
            logger.warning(
                "%s — API retornou code 200, mas o download do PDF falhou. "
                "Os dados da certidão foram preservados.",
                endpoint_nome,
            )
            resultado["pdf_path"] = None
    else:
        # API falhou OU não veio URL temporária
        resultado["pdf_path"] = None

    return resultado


# ─── Função principal ──────────────────────────────────────────────────────────

async def emitir_certidoes(
    documento: str,
    nome: str,
    birthdate: str | None = None,
) -> dict:
    """
    Emite as certidões para o CPF ou CNPJ informado.

    Args:
        documento: CPF (11 dígitos) ou CNPJ (14 dígitos), somente números.
                   Aceita também formatos com pontuação (serão removidos).
        nome:      Nome completo do consultado.
        birthdate: Data de nascimento em formato AAAA-MM-DD.
                   Obrigatório se documento for CPF (PF).

    Returns:
        Dict estruturado com resultados de todas as certidões.

    Raises:
        ValueError: Se documento inválido (não tem 11 nem 14 dígitos).
    """
    inicio = time.monotonic()
    ts_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    # ── Sanitização e validação de entrada ────────────────────────────────────
    doc = _sanitizar_documento(documento)
    tipo = _detectar_tipo(doc)  # levanta ValueError se inválido

    if tipo == "PF" and not birthdate:
        return {
            "sucesso_geral": False,
            "documento": doc,
            "tipo": tipo,
            "nome": nome,
            "timestamp": ts_iso,
            "duracao_segundos": 0.0,
            "erro_validacao": "birthdate é obrigatório para consultas de pessoa física (CPF).",
            "certidoes": {},
            "tjmg": {"status": "não executado", "mensagem": "Validação falhou antes da execução."},
        }

    ts_arquivo = _timestamp_arquivo()

    logger.info("=" * 60)
    logger.info("deed-sync — Iniciando emissão de certidões")
    logger.info("Tipo: %s | Documento: %s*** | Nome: %s", tipo, doc[:4], nome)
    logger.info("=" * 60)

    # ── Caminhos de destino dos PDFs ──────────────────────────────────────────
    destinos = {
        "tst":      _caminho_pdf(doc, "tst",      ts_arquivo),
        "trf6":     _caminho_pdf(doc, "trf6",     ts_arquivo),
        "trt3":     _caminho_pdf(doc, "trt3",     ts_arquivo),
        "pgfn":     _caminho_pdf(doc, "pgfn",     ts_arquivo),
    }

    # ── Chamadas paralelas à API Infosimples ──────────────────────────────────
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:

        logger.info("Disparando 5 consultas em paralelo: TST, TRF6, TRF6_EPROC, TRT3, PGFN...")

        # IMPORTANTE: return_exceptions=True garante que se 1 endpoint levantar
        # exceção não tratada, os outros continuam e suas certidões são
        # preservadas. Sem isso, 1 falha aborta tudo e perdemos chamadas pagas.
        # NOTA: consultar_trf6_eproc usa Playwright (não precisa de session),
        #       mas roda em paralelo perfeitamente via asyncio.gather.
        try:
            resultados_brutos = await asyncio.wait_for(
                asyncio.gather(
                    consultar_tst(doc, session),
                    consultar_trf6(doc, session),
                    consultar_trt3(doc, session),
                    consultar_pgfn(doc, birthdate, session),
                    consultar_trf6_eproc(doc),          # ← NOVO: EPROC via Playwright
                    return_exceptions=True,
                ),
                timeout=GLOBAL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error("Timeout global de %ds atingido — todas as consultas abortadas.", GLOBAL_TIMEOUT_SECONDS)
            return _montar_resposta_erro_global(doc, tipo, nome, ts_iso, inicio)

        # Mapeia resultados, transformando qualquer exceção em resultado de erro
        nomes_endpoints = ["TST", "TRF6", "TRT3", "PGFN", "TRF6_EPROC"]
        resultados_api = []
        for nome_ep, resultado in zip(nomes_endpoints, resultados_brutos):
            if isinstance(resultado, BaseException):
                resultados_api.append(_resultado_excecao(nome_ep, resultado))
            else:
                resultados_api.append(resultado)

        resultado_tst_api, resultado_trf6_api, resultado_trt3_api, resultado_pgfn_api, resultado_trf6_eproc_raw = resultados_api

        # ── Downloads dos PDFs em paralelo (Infosimples) ──────────────────────
        # Nota: TRF6_EPROC já gerencia o próprio PDF via Playwright —
        # não entra no _processar_e_baixar (que é exclusivo pra Infosimples).
        logger.info("APIs responderam. Iniciando download dos PDFs (Infosimples)...")

        nomes_infosimples = ["TST", "TRF6", "TRT3", "PGFN"]
        apis_infosimples  = [resultado_tst_api, resultado_trf6_api, resultado_trt3_api, resultado_pgfn_api]

        # return_exceptions=True também aqui pelo mesmo motivo
        resultados_finais_brutos = await asyncio.gather(
            _processar_e_baixar("TST",  resultado_tst_api,  destinos["tst"],  session),
            _processar_e_baixar("TRF6", resultado_trf6_api, destinos["trf6"], session),
            _processar_e_baixar("TRT3", resultado_trt3_api, destinos["trt3"], session),
            _processar_e_baixar("PGFN", resultado_pgfn_api, destinos["pgfn"], session),
            return_exceptions=True,
        )

        # Se download falhou catastroficamente, mantém o resultado da API original
        # (os dados foram preservados, só não temos PDF baixado)
        resultados_finais = []
        for idx, (nome_ep, original) in enumerate(zip(nomes_infosimples, apis_infosimples)):
            r = resultados_finais_brutos[idx]
            if isinstance(r, BaseException):
                logger.error(
                    "%s — _processar_e_baixar levantou exceção: %s. "
                    "Mantendo resultado original da API.",
                    nome_ep, r,
                )
                fallback = dict(original)
                fallback["pdf_path"] = None
                resultados_finais.append(fallback)
            else:
                resultados_finais.append(r)

    resultado_tst, resultado_trf6, resultado_trt3, resultado_pgfn = resultados_finais

    # TRF6 EPROC — resultado já vem pronto do Playwright (pdf_path incluso)
    resultado_trf6_eproc = resultado_trf6_eproc_raw

    # ── Stub TJMG (Fase 3) ────────────────────────────────────────────────────
    try:
        resultado_tjmg = await consultar_tjmg(
            cpf=doc,
            nome_consultado=nome,                    # nome do consultado — obrigatório pela Fase 3
            nome_solicitante=SOLICITANTE["nome"],
            cpf_solicitante=SOLICITANTE["cpf"],
            email_solicitante=SOLICITANTE["email"],
        )
    except Exception as exc:
        logger.error("TJMG (stub) — exceção: %s", exc)
        resultado_tjmg = {"status": "erro", "mensagem": f"Exceção no stub TJMG: {exc}"}

    # ── Montagem do retorno ───────────────────────────────────────────────────
    certidoes = {
        "tst":        resultado_tst,
        "trf6":       resultado_trf6,       # PJE (Infosimples)
        "trf6_eproc": resultado_trf6_eproc,  # EPROC (Playwright)
        "trt3":       resultado_trt3,
        "pgfn":       resultado_pgfn,
    }

    # sucesso_geral: Infosimples usa "sucesso", EPROC usa "status"
    sucesso_infosimples = all(
        r.get("sucesso", False)
        for k, r in certidoes.items()
        if k != "trf6_eproc"
    )
    sucesso_eproc = resultado_trf6_eproc.get("status") == "concluido"
    sucesso_geral = sucesso_infosimples and sucesso_eproc
    duracao = round(time.monotonic() - inicio, 1)

    # Log resumo
    logger.info("=" * 60)
    logger.info("Resumo da emissão (%.1fs):", duracao)
    for nome_cert, res in certidoes.items():
        if nome_cert == "trf6_eproc":
            status_icon = "✓" if res.get("status") == "concluido" else "✗"
            pdf = Path(res.get("pdf_path") or "").name if res.get("pdf_path") else "—"
            logger.info("  %s %s | status: %s | pdf: %s", status_icon, nome_cert.upper(), res.get("status", "N/A"), pdf)
        else:
            status_icon = "✓" if res.get("sucesso") else "✗"
            code = res.get("code", "N/A")
            pdf = Path(res.get("pdf_path") or "").name if res.get("pdf_path") else "—"
            logger.info("  %s %s | code: %s | pdf: %s", status_icon, nome_cert.upper(), code, pdf)
    logger.info("TJMG: %s", resultado_tjmg.get("status", "N/A"))
    logger.info("Sucesso geral: %s", sucesso_geral)
    logger.info("=" * 60)

    return {
        "sucesso_geral": sucesso_geral,
        "documento": doc,
        "tipo": tipo,
        "nome": nome,
        "timestamp": ts_iso,
        "duracao_segundos": duracao,
        "certidoes": certidoes,
        "tjmg": resultado_tjmg,
    }


def _montar_resposta_erro_global(
    doc: str,
    tipo: str,
    nome: str,
    ts_iso: str,
    inicio: float,
    detalhe: str = "Timeout global atingido.",
) -> dict:
    """Monta resposta de erro quando o gather global falha (timeout)."""
    erro_cert = {
        "sucesso": False,
        "code": None,
        "code_message": None,
        "pdf_path": None,
        "pdf_url_temporaria": None,
        "dados": None,
        "erro": detalhe,
    }
    return {
        "sucesso_geral": False,
        "documento": doc,
        "tipo": tipo,
        "nome": nome,
        "timestamp": ts_iso,
        "duracao_segundos": round(time.monotonic() - inicio, 1),
        "certidoes": {
            "tst":        {**erro_cert},
            "trf6":       {**erro_cert},
            "trf6_eproc": {"status": "não executado", "pdf_path": None, "duracao_segundos": 0, "erro": detalhe, "detalhes_tecnicos": None},
            "trt3":       {**erro_cert},
            "pgfn":       {**erro_cert, "modo": None, "tentativas": 0},
        },
        "tjmg": {"status": "não executado", "mensagem": "Falha antes da execução."},
    }


# ─── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Uso: python scraper.py <CPF_ou_CNPJ> <Nome> [birthdate_AAAA-MM-DD]\n"
            "Exemplos:\n"
            "  python scraper.py 11773105620 'Pedro Ivo Batista Clemente' 1990-01-15\n"
            "  python scraper.py 00000000000191 'Empresa SA'\n"
        )
        sys.exit(1)

    _documento_cli = sys.argv[1]
    _nome_cli = sys.argv[2]
    _birthdate_cli = sys.argv[3] if len(sys.argv) > 3 else None

    resultado_cli = asyncio.run(
        emitir_certidoes(_documento_cli, _nome_cli, _birthdate_cli)
    )
    print(json.dumps(resultado_cli, ensure_ascii=False, indent=2, default=str))