"""
tjmg_scraper.py — VERSÃO DIAGNÓSTICA
Esta versão NÃO é pra produção — adiciona logs verbosos e pausa de 30s
antes de fechar o browser pra investigar como o RUPE entrega o PDF.

Após capturar as URLs / responses, voltaremos à versão limpa.

Variáveis de ambiente:
  TJMG_HEADLESS=false   → abre browser visível (recomendado pra diagnóstico)

CLI de teste:
  python tjmg_scraper.py <CPF_ou_CNPJ> "<Nome Completo>"
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import (
    TimeoutError as PlaywrightTimeout,
    async_playwright,
)

from gmail_reader import GmailReader

# ─── Configuração ──────────────────────────────────────────────────────────────

logger = logging.getLogger("deed-sync.tjmg_scraper")

HEADLESS = os.getenv("TJMG_HEADLESS", "true").lower() not in ("false", "0", "no")

TIMEOUT_OTP_SEGUNDOS = 180

# Pausa diagnóstica antes de fechar o browser
PAUSA_DIAGNOSTICA_SEGUNDOS = 30

OUTPUT_BASE = Path(__file__).parent / "output" / "pdfs"

URL_CRIAR = (
    "https://rupe.tjmg.jus.br/rupe/justica/publico/certidoes/"
    "criarSolicitacaoCertidao.rupe?solicitacaoPublica=true"
)
URL_ACOMPANHAR = (
    "https://rupe.tjmg.jus.br/rupe/justica/publico/certidoes/"
    "consultarAndamentoSolicitacaoCertidao.rupe?solicitacaoPublica=true"
)

# Dados fixos do solicitante Pedro Ivo (usados internamente — não logar)
_SOLICITANTE_NOME = "PEDRO IVO BATISTA CLEMENTE"
_SOLICITANTE_CPF = "117.731.056-20"
_SOLICITANTE_EMAIL = "contato@clementeassessoria.com"

REGEX_PROTOCOLO = re.compile(r"[Pp]rotocolo[:\s#]*(\d[\d./\-]+)", re.IGNORECASE)
# Detectar também o formato real visto: "Solicitação de certidão de número 2026..."
REGEX_PROTOCOLO_SOLICITACAO = re.compile(
    r"[Ss]olicita[çc][ãa]o\s+de\s+certid[ãa]o\s+de\s+n[úu]mero\s+(\d+)",
    re.IGNORECASE,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _formatar_cpf(d: str) -> str:
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def _formatar_cnpj(d: str) -> str:
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _destino_pdf(documento: str) -> Path:
    pasta = OUTPUT_BASE / documento
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"tjmg_{_timestamp()}.pdf"


def _resultado_base() -> dict:
    return {
        "status": None,
        "pdf_path": None,
        "protocolo": None,
        "cpf_solicitante": _SOLICITANTE_CPF,
        "url_acompanhamento": URL_ACOMPANHAR,
        "instrucao": None,
        "duracao_segundos": None,
        "erro": None,
        "detalhes_tecnicos": None,
        "diagnostico": {},  # NOVO: capturas pra debug
    }


def _finalizar(resultado: dict, inicio: float) -> dict:
    resultado["duracao_segundos"] = round(time.monotonic() - inicio, 1)
    return resultado


# ─── Preenchimento (igual à versão anterior) ───────────────────────────────────

async def _preencher_secao_certidao(page) -> None:
    logger.info("Preenchendo seção Certidão...")
    try:
        await page.get_by_label("1ª Instância").check(timeout=5000)
    except Exception:
        await page.locator("input[type=radio][value*='1']").first.check(timeout=5000)
    try:
        await page.get_by_label("Cível").check(timeout=5000)
    except Exception:
        await page.locator("input[type=radio][value*='ivel']").first.check(timeout=5000)
    try:
        await page.get_by_label("Tipo").select_option(label="Normal", timeout=5000)
    except Exception:
        await page.locator("select").filter(has_text="Normal").select_option(
            label="Normal", timeout=5000
        )
    try:
        await page.get_by_label("Comarca").select_option(label="JUIZ DE FORA", timeout=5000)
    except Exception:
        selects = page.locator("select")
        count = await selects.count()
        for i in range(count):
            sel = selects.nth(i)
            opts = await sel.inner_text()
            if "JUIZ DE FORA" in opts:
                await sel.select_option(label="JUIZ DE FORA", timeout=5000)
                break
    logger.info("Seção Certidão preenchida.")


async def _preencher_secao_dados(page, documento: str, nome: str) -> None:
    logger.info("Preenchendo seção Dados do Consultado...")
    if len(documento) == 11:
        doc_formatado = _formatar_cpf(documento)
        try:
            await page.get_by_label("Física").check(timeout=5000)
        except Exception:
            await page.locator("input[type=radio]").filter(has_text="Física").check(timeout=5000)
    elif len(documento) == 14:
        doc_formatado = _formatar_cnpj(documento)
        try:
            await page.get_by_label("Jurídica").check(timeout=5000)
        except Exception:
            await page.locator("input[type=radio]").filter(has_text="Jurídica").check(timeout=5000)
    else:
        raise ValueError(f"Documento inválido: {len(documento)} dígitos")

    try:
        await page.get_by_label("CPF").fill(doc_formatado, timeout=5000)
    except Exception:
        campo = page.locator("input[name*='cpf'], input[id*='cpf'], input[name*='Cpf']").first
        await campo.fill(doc_formatado, timeout=5000)
    try:
        await page.get_by_label("Nome").first.fill(nome, timeout=5000)
    except Exception:
        campo = page.locator("input[name*='nome'], input[id*='nome'], input[name*='Nome']").first
        await campo.fill(nome, timeout=5000)
    logger.info("Seção Dados do Consultado preenchida.")


async def _preencher_secao_solicitante(page, nome: str, cpf: str, email: str) -> None:
    logger.info("Preenchendo seção Solicitante...")

    async def _fill(labels: list[str], selectors: list[str], valor: str):
        for lbl in labels:
            try:
                await page.get_by_label(lbl).fill(valor, timeout=4000)
                return
            except Exception:
                continue
        for sel in selectors:
            try:
                await page.locator(sel).fill(valor, timeout=4000)
                return
            except Exception:
                continue
        raise RuntimeError(f"Não encontrei campo: {labels}")

    await _fill(
        ["Nome do Solicitante", "Nome"],
        ["input[name*='nomeSolicitante']", "input[id*='nomeSolicitante']"],
        nome,
    )
    await _fill(
        ["CPF do Solicitante", "CPF Solicitante"],
        ["input[name*='cpfSolicitante']", "input[id*='cpfSolicitante']"],
        cpf,
    )
    await _fill(
        ["E-mail", "Email"],
        ["input[name*='email']:not([name*='onfirmacao'])"],
        email,
    )
    await _fill(
        ["Confirmação de E-mail", "Confirmação E-mail", "Confirmar E-mail"],
        ["input[name*='onfirmacao']"],
        email,
    )
    logger.info("Seção Solicitante preenchida.")


async def _disparar_envio_otp(page) -> None:
    logger.info("Clicando em 'Gerar Código' (abre popup de confirmação)...")
    try:
        await page.click("text=Gerar Código", timeout=10_000)
    except Exception as exc:
        raise RuntimeError(f"Não encontrei o botão 'Gerar Código': {exc}")

    await asyncio.sleep(1.5)

    logger.info("Clicando em 'Enviar Código de Verificação' no popup...")
    seletores = [
        'text="Enviar Código de Verificação"',
        'button:has-text("Enviar Código de Verificação")',
        'input[type="button"][value*="Enviar Código"]',
        'input[type="submit"][value*="Enviar Código"]',
        'input[value*="Enviar Código de Verificação"]',
    ]
    clicado = False
    ultima_exc = None
    for s in seletores:
        try:
            await page.locator(s).first.click(timeout=5000)
            clicado = True
            logger.info("Popup confirmado via seletor: %s", s)
            break
        except Exception as exc:
            ultima_exc = exc
            continue
    if not clicado:
        raise RuntimeError(f"Popup não encontrado. Última exceção: {ultima_exc}")

    await asyncio.sleep(1)


# ─── DIAGNÓSTICO: dump completo de estado ──────────────────────────────────────

async def _dump_estado(label: str, page, context, captura: dict) -> None:
    """
    Imprime e armazena estado completo do browser para diagnóstico.

    Captura:
      - URL atual da página principal
      - Lista de TODAS as abas e suas URLs/títulos
      - Trecho do conteúdo da página principal (primeiros 800 chars)
    """
    logger.info("=" * 60)
    logger.info("DIAGNÓSTICO [%s]", label)
    logger.info("=" * 60)

    estado = {"label": label, "timestamp": datetime.now(timezone.utc).isoformat()}

    # URL atual da página principal
    try:
        url_atual = page.url
        logger.info("URL página principal: %s", url_atual)
        estado["url_principal"] = url_atual
    except Exception as exc:
        logger.warning("Erro ao obter URL principal: %s", exc)
        estado["url_principal_erro"] = str(exc)

    # Todas as abas
    try:
        todas_pages = context.pages
        logger.info("Total de abas abertas: %d", len(todas_pages))
        estado["abas"] = []
        for i, p in enumerate(todas_pages):
            try:
                titulo = await p.title()
            except Exception:
                titulo = "<erro ao obter título>"
            url_p = p.url
            logger.info("  Aba %d: url=%s | titulo=%s", i, url_p, titulo)
            estado["abas"].append({"indice": i, "url": url_p, "titulo": titulo})
    except Exception as exc:
        logger.warning("Erro ao listar abas: %s", exc)
        estado["abas_erro"] = str(exc)

    # Trecho da página principal
    try:
        texto = await page.inner_text("body", timeout=5000)
        trecho = texto[:800].strip()
        logger.info("Trecho do conteúdo (primeiros 800 chars):\n%s", trecho)
        estado["trecho_pagina"] = trecho
    except Exception as exc:
        logger.warning("Erro ao obter texto da página: %s", exc)
        estado["trecho_pagina_erro"] = str(exc)

    logger.info("=" * 60)
    captura[label] = estado


# ─── Captura de PDF (DIAGNÓSTICA) ──────────────────────────────────────────────

async def _capturar_pdf_download_diagnostico(page, context, destino: Path, captura: dict) -> str | None:
    """
    Versão diagnóstica: tenta capturar download E loga tudo que acontece.
    """
    # ANTES do clique
    await _dump_estado("ANTES_DO_SALVAR", page, context, captura)

    # Configurar handler pra novas páginas (NOVO: detecta abertura de aba)
    novas_paginas = []

    def on_new_page(p):
        novas_paginas.append(p)
        logger.info("EVENTO: Nova página aberta — URL inicial: %s", p.url)

    context.on("page", on_new_page)

    # Configurar handler pra responses (detecta PDFs por content-type)
    pdfs_responses = []

    def on_response(response):
        ct = response.headers.get("content-type", "").lower()
        if "pdf" in ct:
            pdfs_responses.append({
                "url": response.url,
                "content_type": ct,
                "status": response.status,
            })
            logger.info("EVENTO: Response com PDF detectado — URL: %s | Content-Type: %s",
                       response.url, ct)

    context.on("response", on_response)

    # Tentar capturar download (mesmo método antes)
    try:
        async with page.expect_download(timeout=30_000) as dl_info:
            logger.info("Clicando em 'Salvar' (com expect_download)...")
            await page.click("text=Salvar", timeout=10_000)
        download = await dl_info.value
        caminho_temp = await download.path()
        if caminho_temp:
            destino.write_bytes(Path(caminho_temp).read_bytes())
            logger.info("PDF salvo via download: %s", destino.name)
            captura["modo_captura"] = "download_direto"
            return str(destino.resolve())
    except PlaywrightTimeout:
        logger.info("Nenhum download automático em 30s.")
    except Exception as exc:
        logger.warning("Erro ao capturar download: %s", exc)

    # DEPOIS de aguardar download (ou timeout)
    await asyncio.sleep(3)
    await _dump_estado("DEPOIS_DO_SALVAR", page, context, captura)

    # Salvar info dos eventos capturados
    captura["novas_paginas_eventos"] = [
        {"url": p.url, "titulo": await p.title()} for p in novas_paginas
    ]
    captura["pdfs_responses_eventos"] = pdfs_responses

    logger.info("Total de novas páginas via evento: %d", len(novas_paginas))
    logger.info("Total de responses PDF detectados: %d", len(pdfs_responses))

    return None


# ─── Função principal (DIAGNÓSTICA) ────────────────────────────────────────────

async def consultar_tjmg(
    cpf: str,
    nome_solicitante: str,
    cpf_solicitante: str,
    email_solicitante: str,
    nome_consultado: str | None = None,
    documento_consultado: str | None = None,
) -> dict:
    inicio = time.monotonic()
    resultado = _resultado_base()
    captura = resultado["diagnostico"]

    doc = cpf or documento_consultado or ""
    doc = "".join(c for c in doc if c.isdigit())

    if not doc or len(doc) not in (11, 14):
        resultado["status"] = "erro"
        resultado["erro"] = f"CPF/CNPJ inválido: '{cpf}'"
        return _finalizar(resultado, inicio)

    if not nome_consultado:
        resultado["status"] = "erro"
        resultado["erro"] = "nome_consultado é obrigatório"
        return _finalizar(resultado, inicio)

    logger.info("=" * 60)
    logger.info("TJMG/RUPE — Iniciando consulta DIAGNÓSTICA")
    logger.info("Consultado: doc=%s*** | nome=%s", doc[:4], nome_consultado)
    logger.info("=" * 60)

    # Gmail
    logger.info("Testando autenticação Gmail...")
    try:
        gmail = GmailReader()
        gmail.testar_acesso()
    except Exception as exc:
        resultado["status"] = "erro"
        resultado["erro"] = f"Falha Gmail: {exc}"
        return _finalizar(resultado, inicio)

    logger.info("Iniciando Playwright (headless=%s)...", HEADLESS)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            accept_downloads=True,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        page = await context.new_page()

        try:
            logger.info("Abrindo portal RUPE...")
            try:
                await page.goto(URL_CRIAR, timeout=60_000)
                await page.wait_for_load_state("networkidle", timeout=30_000)
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Erro ao abrir RUPE: {exc}"
                return _finalizar(resultado, inicio)

            try:
                await _preencher_secao_certidao(page)
                await _preencher_secao_dados(page, doc, nome_consultado)
                await _preencher_secao_solicitante(
                    page, nome_solicitante, cpf_solicitante, email_solicitante,
                )
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Erro ao preencher: {exc}"
                return _finalizar(resultado, inicio)

            timestamp_envio = datetime.now(timezone.utc)
            try:
                await _disparar_envio_otp(page)
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Erro ao disparar OTP: {exc}"
                return _finalizar(resultado, inicio)

            logger.info("Aguardando OTP por email (timeout=%ds)...", TIMEOUT_OTP_SEGUNDOS)
            try:
                otp = await gmail.aguardar_otp(timestamp_envio, timeout=TIMEOUT_OTP_SEGUNDOS)
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"OTP não chegou: {exc}"
                return _finalizar(resultado, inicio)

            logger.info("OTP recebido. Preenchendo código de verificação...")
            try:
                campo_otp = page.locator(
                    "input[name*='codigo'], input[id*='codigo'], "
                    "input[name*='Codigo'], input[placeholder*='digo']"
                ).first
                await campo_otp.fill(otp, timeout=5000)
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Campo OTP não encontrado: {exc}"
                return _finalizar(resultado, inicio)

            # CAPTURA DIAGNÓSTICA com logs verbosos
            destino = _destino_pdf(doc)
            pdf_path = await _capturar_pdf_download_diagnostico(page, context, destino, captura)

            if pdf_path:
                resultado["status"] = "concluido"
                resultado["pdf_path"] = pdf_path

            # Tentar extrair protocolo (com 2 regex agora)
            try:
                texto = await page.inner_text("body", timeout=5000)
                match = REGEX_PROTOCOLO_SOLICITACAO.search(texto)
                if match:
                    resultado["protocolo"] = match.group(1).strip()
                    logger.info("Protocolo extraído (formato 'Solicitação de número'): %s", resultado["protocolo"])
                else:
                    match = REGEX_PROTOCOLO.search(texto)
                    if match:
                        resultado["protocolo"] = match.group(1).strip()
                        logger.info("Protocolo extraído (formato 'Protocolo:'): %s", resultado["protocolo"])
            except Exception as exc:
                logger.warning("Erro ao extrair protocolo: %s", exc)

            # PAUSA DIAGNÓSTICA — você tem 30s pra ver as abas, copiar URL etc
            logger.info("=" * 60)
            logger.info("⏸️  PAUSA DIAGNÓSTICA: %ds antes de fechar o browser", PAUSA_DIAGNOSTICA_SEGUNDOS)
            logger.info("    OLHA AS JANELAS ABERTAS DO CHROMIUM")
            logger.info("    Se houver aba com PDF, copia a URL agora")
            logger.info("=" * 60)
            await asyncio.sleep(PAUSA_DIAGNOSTICA_SEGUNDOS)

            # Estado FINAL antes de fechar
            await _dump_estado("FINAL_ANTES_DE_FECHAR", page, context, captura)

            if not resultado["status"]:
                resultado["status"] = "diagnostico"
                resultado["erro"] = "Modo diagnóstico — capture as informações dos logs"

            return _finalizar(resultado, inicio)

        except Exception as exc:
            logger.exception("Exceção inesperada")
            resultado["status"] = "erro"
            resultado["erro"] = f"Erro inesperado: {exc}"
            return _finalizar(resultado, inicio)
        finally:
            await browser.close()
            logger.info("Browser fechado.")


# ─── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) < 3:
        print("Uso: python tjmg_scraper.py <CPF_ou_CNPJ> \"<Nome>\"")
        sys.exit(1)

    _doc = "".join(c for c in sys.argv[1] if c.isdigit())
    _nome = sys.argv[2]

    _r = asyncio.run(
        consultar_tjmg(
            cpf=_doc,
            nome_solicitante=_SOLICITANTE_NOME,
            cpf_solicitante=_SOLICITANTE_CPF,
            email_solicitante=_SOLICITANTE_EMAIL,
            nome_consultado=_nome,
        )
    )
    print("\n=== RESULTADO ===")
    print(json.dumps(_r, ensure_ascii=False, indent=2, default=str))