"""
trf6_eproc_scraper.py — TRF6 EPROC (certidão.trf6.jus.br)
Automatiza a emissão da Certidão Judicial Cível via portal EPROC do TRF6.

Diferente do PJE (coberto pela Infosimples), este portal não tem cobertura
pela API — por isso usamos Playwright diretamente.

Variáveis de ambiente:
  TRF6_EPROC_HEADLESS=false   → abre browser visível (útil pra debug)

CLI de teste:
  python trf6_eproc_scraper.py 11773105620
  TRF6_EPROC_HEADLESS=false python trf6_eproc_scraper.py 11773105620
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import (
    TimeoutError as PlaywrightTimeout,
    async_playwright,
)

# ─── Configuração ──────────────────────────────────────────────────────────────

logger = logging.getLogger("deed-sync.trf6_eproc_scraper")

HEADLESS = os.getenv("TRF6_EPROC_HEADLESS", "true").lower() not in ("false", "0", "no")

OUTPUT_BASE = Path(__file__).parent / "output" / "pdfs"

URL_EPROC = "https://certidao.trf6.jus.br/consulta"
URL_PDF_EPROC_HOST = "certidao.trf6.jus.br"

# Timeout máximo aguardando o botão "Baixar certidão" aparecer
TIMEOUT_PROCESSAMENTO_SEGUNDOS = 120


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mask_doc(doc: str) -> str:
    """Mascara o documento pra logging seguro (mostra apenas os 4 primeiros dígitos)."""
    return f"{doc[:4]}{'*' * (len(doc) - 4)}"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _destino_pdf(documento: str) -> Path:
    pasta = OUTPUT_BASE / documento
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / f"trf6_eproc_{_timestamp()}.pdf"


def _resultado_base() -> dict:
    return {
        "status": None,
        "pdf_path": None,
        "duracao_segundos": None,
        "erro": None,
        "detalhes_tecnicos": None,
    }


def _finalizar(resultado: dict, inicio: float) -> dict:
    resultado["duracao_segundos"] = round(time.monotonic() - inicio, 1)
    return resultado


# ─── Captura de PDF via response event ────────────────────────────────────────

async def _capturar_pdf_via_response(context, page, destino: Path) -> str | None:
    """
    Aguarda resposta HTTP com Content-Type application/pdf do host do EPROC,
    baixa via APIRequestContext e salva em destino.

    Estratégia:
      1. Registra handler em context.on("response", ...) ANTES do clique.
      2. Clica em "Baixar certidão".
      3. Aguarda até 30s pela URL de PDF detectada.
      4. Baixa com context.request.get() e salva.

    Retorna caminho absoluto do PDF salvo, ou None em caso de falha.
    """
    pdf_url_capturada: list[str] = []

    def on_response(response):
        ct = response.headers.get("content-type", "").lower()
        host = URL_PDF_EPROC_HOST
        if "pdf" in ct and host in response.url:
            if not pdf_url_capturada:  # captura só a primeira
                pdf_url_capturada.append(response.url)
                logger.info("PDF detectado via response event — URL: %s", response.url)

    context.on("response", on_response)

    try:
        logger.info("Clicando em 'Baixar certidão'...")
        await page.locator("text=/Baixar Certidão/i").first.click(timeout=10_000)
    except Exception as exc:
        logger.warning("Botão 'Baixar certidão' não respondeu ao clique: %s", exc)
        # Tenta seletor alternativo
        try:
            await page.locator("button:has-text('Baixar'), a:has-text('Baixar'), :text('Baixar')").first.click(timeout=8_000)
        except Exception as exc2:
            logger.error("Clique alternativo também falhou: %s", exc2)
            return None

    # Aguarda até 30s pela URL de PDF
    logger.info("Aguardando captura do PDF (até 30s)...")
    for _ in range(60):  # 60 × 0.5s = 30s
        if pdf_url_capturada:
            break
        await asyncio.sleep(0.5)

    if not pdf_url_capturada:
        logger.warning("Nenhuma URL de PDF capturada via response event.")
        # Tenta buscar em novas abas abertas
        for p in context.pages:
            if URL_PDF_EPROC_HOST in p.url and p.url != URL_EPROC:
                logger.info("Aba extra detectada com URL: %s", p.url)
                pdf_url_capturada.append(p.url)
                break

    if not pdf_url_capturada:
        logger.error("PDF não capturado — nenhuma URL encontrada.")
        return None

    pdf_url = pdf_url_capturada[0]
    logger.info("Baixando PDF via APIRequestContext: %s", pdf_url)

    try:
        response = await context.request.get(pdf_url)
        if response.status != 200:
            logger.error("HTTP %d ao baixar PDF de %s", response.status, pdf_url)
            return None

        conteudo = await response.body()

        # Valida assinatura PDF
        if len(conteudo) < 4 or conteudo[:4] != b"%PDF":
            logger.error(
                "Conteúdo baixado não é PDF válido (primeiros bytes: %s)",
                conteudo[:4],
            )
            return None

        destino.write_bytes(conteudo)
        logger.info("PDF salvo: %s (%d bytes)", destino.name, len(conteudo))
        return str(destino.resolve())

    except Exception as exc:
        logger.error("Erro ao baixar PDF: %s", exc)
        return None


# ─── Função principal ──────────────────────────────────────────────────────────

async def consultar_trf6_eproc(
    documento: str,
    nome_consultado: str | None = None,  # não usado pelo portal, mantido por simetria
) -> dict:
    """
    Emite a Certidão Judicial Cível via portal EPROC do TRF6.

    Args:
        documento:       CPF (11 dígitos) ou CNPJ (14 dígitos), apenas números.
        nome_consultado: Não usado pelo portal EPROC, mas mantido por simetria
                         com as demais funções do scraper.py.

    Returns:
        Dict com campos: status, pdf_path, duracao_segundos, erro, detalhes_tecnicos.
    """
    inicio = time.monotonic()
    resultado = _resultado_base()

    # ── Validação de entrada ───────────────────────────────────────────────────
    doc = "".join(c for c in documento if c.isdigit())
    if not doc or len(doc) not in (11, 14):
        resultado["status"] = "erro"
        resultado["erro"] = f"CPF/CNPJ inválido: '{documento}' (esperado 11 ou 14 dígitos)"
        return _finalizar(resultado, inicio)

    logger.info("=" * 60)
    logger.info("TRF6 EPROC — Iniciando consulta")
    logger.info("Documento: %s | Tipo: %s", _mask_doc(doc), "CPF" if len(doc) == 11 else "CNPJ")
    logger.info("=" * 60)

    # ── Playwright ────────────────────────────────────────────────────────────
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            accept_downloads=True,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        page = await context.new_page()

        try:
            # STEP 1 — Abrir portal
            logger.info("Abrindo portal EPROC: %s", URL_EPROC)
            try:
                await page.goto(URL_EPROC, timeout=60_000)
                await page.wait_for_load_state("networkidle", timeout=30_000)
                logger.info("Portal carregado com sucesso.")
            except PlaywrightTimeout as exc:
                resultado["status"] = "erro"
                resultado["erro"] = "Portal TRF6 EPROC indisponível"
                resultado["detalhes_tecnicos"] = str(exc)
                return _finalizar(resultado, inicio)
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Erro ao abrir portal EPROC: {exc}"
                resultado["detalhes_tecnicos"] = str(exc)
                return _finalizar(resultado, inicio)

            # Verificação rápida de disponibilidade
            try:
                texto_pagina = await page.inner_text("body", timeout=5_000)
                if len(texto_pagina.strip()) < 10:
                    resultado["status"] = "erro"
                    resultado["erro"] = "Portal TRF6 EPROC indisponível (página vazia)"
                    return _finalizar(resultado, inicio)
            except Exception:
                pass  # não crítico

            # STEP 2 — Preencher CPF/CNPJ
            logger.info("Preenchendo CPF/CNPJ no formulário...")
            try:
                # Tenta pelo label primeiro, depois por seletores alternativos
                campo_doc = None
                seletores_doc = [
                    "label:has-text('CPF/CNPJ') >> .. >> input",
                    "input[placeholder*='CPF'], input[placeholder*='CNPJ']",
                    "input[name*='cpf'], input[id*='cpf'], input[name*='documento']",
                    "input[type='text']",
                ]
                for sel in seletores_doc:
                    try:
                        loc = page.locator(sel).first
                        if await loc.count() > 0 or True:
                            await loc.fill(doc, timeout=5_000)
                            campo_doc = sel
                            break
                    except Exception:
                        continue

                if campo_doc is None:
                    # Fallback: usa get_by_label
                    await page.get_by_label("CPF/CNPJ").fill(doc, timeout=5_000)

                logger.info("Campo CPF/CNPJ preenchido.")
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Campo CPF/CNPJ não encontrado: {exc}"
                resultado["detalhes_tecnicos"] = str(exc)
                return _finalizar(resultado, inicio)

            # STEP 3 — Selecionar "Certidão judicial cível"
            logger.info("Selecionando tipo de certidão: 'Certidão judicial cível'...")
            try:
                seletores_select = [
                    "select",
                    "select[name*='tipo'], select[id*='tipo']",
                ]
                selecionado = False
                for sel in seletores_select:
                    try:
                        await page.locator(sel).first.select_option(
                            label="Certidão judicial cível", timeout=5_000
                        )
                        selecionado = True
                        break
                    except Exception:
                        continue

                if not selecionado:
                    # Tenta get_by_label
                    await page.get_by_label("Tipo de certidão").select_option(
                        label="Certidão judicial cível", timeout=5_000
                    )

                logger.info("Tipo de certidão selecionado.")
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Não foi possível selecionar o tipo de certidão: {exc}"
                resultado["detalhes_tecnicos"] = str(exc)
                return _finalizar(resultado, inicio)

            # STEP 4 — Clicar em "Requisitar Certidão"
            logger.info("Clicando em 'Requisitar Certidão'...")
            try:
                seletores_btn = [
                    "text=Requisitar Certidão",
                    "button:has-text('Requisitar Certidão')",
                    "input[type='submit'][value*='Requisitar']",
                    "input[value*='Requisitar Certidão']",
                ]
                clicado = False
                for sel in seletores_btn:
                    try:
                        await page.locator(sel).first.click(timeout=8_000)
                        clicado = True
                        logger.info("Botão 'Requisitar Certidão' clicado via: %s", sel)
                        break
                    except Exception:
                        continue

                if not clicado:
                    resultado["status"] = "erro"
                    resultado["erro"] = "Botão 'Requisitar Certidão' não encontrado"
                    return _finalizar(resultado, inicio)

            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Erro ao clicar 'Requisitar Certidão': {exc}"
                resultado["detalhes_tecnicos"] = str(exc)
                return _finalizar(resultado, inicio)

            # STEP 5 — Verificar se há erro de CPF/CNPJ inválido imediatamente
            await asyncio.sleep(2)
            try:
                texto_pos_envio = await page.inner_text("body", timeout=5_000)
                termos_erro = [
                    "cpf inválido", "cnpj inválido", "documento inválido",
                    "não encontrado", "invalid", "erro", "error",
                ]
                termos_sucesso = [
                    "baixar certidão", "certidão emitida", "download", "processan",
                ]
                texto_lower = texto_pos_envio.lower()

                # Se apareceu mensagem de erro clara E não tem indicação de sucesso
                if any(t in texto_lower for t in termos_erro) and not any(t in texto_lower for t in termos_sucesso):
                    # Extrai a mensagem de erro da página
                    try:
                        erro_pagina = await page.locator(
                            ".alert, .error, .erro, [class*='error'], [class*='erro'], "
                            "[class*='alert'], p.text-danger, span.text-danger"
                        ).first.inner_text(timeout=3_000)
                    except Exception:
                        erro_pagina = texto_pos_envio[:300].strip()
                    resultado["status"] = "erro"
                    resultado["erro"] = f"CPF/CNPJ rejeitado pelo portal: {erro_pagina[:200]}"
                    resultado["detalhes_tecnicos"] = texto_pos_envio[:500]
                    return _finalizar(resultado, inicio)
            except Exception:
                pass  # verificação não crítica

            # STEP 6 — Aguardar processamento e botão "Baixar certidão"
            logger.info(
                "Aguardando processamento (até %ds)...", TIMEOUT_PROCESSAMENTO_SEGUNDOS
            )
            try:
                await page.locator("text=/Baixar Certidão/i").first.wait_for(
                    timeout=TIMEOUT_PROCESSAMENTO_SEGUNDOS * 1_000,
                    state="visible",
                )
                logger.info("Botão 'Baixar certidão' detectado — certidão pronta!")
            except PlaywrightTimeout:
                # Tenta capturar conteúdo da página pra diagnóstico
                try:
                    conteudo_timeout = await page.inner_text("body", timeout=5_000)
                except Exception:
                    conteudo_timeout = "<não foi possível obter conteúdo da página>"

                resultado["status"] = "erro"
                resultado["erro"] = f"Processamento excedeu {TIMEOUT_PROCESSAMENTO_SEGUNDOS}s sem exibir o botão 'Baixar certidão'"
                resultado["detalhes_tecnicos"] = conteudo_timeout[:800]
                return _finalizar(resultado, inicio)
            except Exception as exc:
                resultado["status"] = "erro"
                resultado["erro"] = f"Erro ao aguardar botão de download: {exc}"
                resultado["detalhes_tecnicos"] = str(exc)
                return _finalizar(resultado, inicio)

            # STEP 7 — Capturar e baixar PDF
            logger.info("Iniciando captura do PDF...")
            destino = _destino_pdf(doc)
            pdf_path = await _capturar_pdf_via_response(context, page, destino)

            if pdf_path:
                resultado["status"] = "concluido"
                resultado["pdf_path"] = pdf_path
                logger.info("=" * 60)
                logger.info("TRF6 EPROC — Certidão emitida com sucesso!")
                logger.info("PDF salvo em: %s", pdf_path)
                logger.info("=" * 60)
            else:
                resultado["status"] = "erro"
                resultado["erro"] = "Botão 'Baixar certidão' foi clicado, mas o PDF não foi capturado"
                try:
                    resultado["detalhes_tecnicos"] = await page.inner_text("body", timeout=5_000)
                except Exception:
                    pass

            return _finalizar(resultado, inicio)

        except Exception as exc:
            logger.exception("Exceção inesperada no scraper EPROC")
            resultado["status"] = "erro"
            resultado["erro"] = f"Erro inesperado: {exc}"
            resultado["detalhes_tecnicos"] = str(exc)
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

    if len(sys.argv) < 2:
        print("Uso: python trf6_eproc_scraper.py <CPF_ou_CNPJ>")
        print("Exemplo: python trf6_eproc_scraper.py 11773105620")
        print("         TRF6_EPROC_HEADLESS=false python trf6_eproc_scraper.py 11773105620")
        sys.exit(1)

    _doc = "".join(c for c in sys.argv[1] if c.isdigit())

    _r = asyncio.run(consultar_trf6_eproc(_doc))
    print("\n=== RESULTADO ===")
    print(json.dumps(_r, ensure_ascii=False, indent=2, default=str))
