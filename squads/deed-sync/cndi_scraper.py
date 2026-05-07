"""
cndi_scraper.py
Scraper Playwright para emissão de CNDI (Certidão Negativa de Débito de Imóvel)
na Prefeitura de Juiz de Fora via portal 1doc.

Fluxo:
1. Login no portal 1doc com email + senha + reCaptcha v2 (2captcha)
2. Navegação até formulário de CNDI
3. Preenchimento dos dados do proprietário e do imóvel
4. Protocolar e capturar número de protocolo + URL
5. Download do PDF quando disponível (via polling de e-mail externo)

Uso standalone:
    python cndi_scraper.py <cpf_cnpj_vendedor> "<nome_vendedor>" <inscricao_iptu> "<endereco_imovel>" <numero> "<complemento>" "<bairro>"

Exemplo:
    python cndi_scraper.py 10271511672 "Maria Regina Bellei Picinini" 006987008 "RUA SILVA JARDIM" 361 "APTO 404" "Centro"
"""

import asyncio
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

# ─── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] deed-sync.cndi_scraper — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("deed-sync.cndi_scraper")

# ─── Constantes ─────────────────────────────────────────────────────────────

PORTAL_URL = "https://juizdefora.1doc.com.br/b.php?pg=o/wp&s=juizdefora"
RECAPTCHA_SITEKEY = "6Lc6f_4SAAAAAK4yKz-XY5dA7Ie5oPxKOJ3PjqsL"

# Dados hardcoded do despachante (Pedro Ivo)
DESPACHANTE_CPF = "11773105620"
REQUERENTE_NOME = "PEDRO IVO BATISTA CLEMENTE"
REQUERENTE_CPF = "117.731.056-20"
REQUERENTE_ENDERECO = "RUA SANTA RITA"
REQUERENTE_NUMERO = "454"
REQUERENTE_COMPLEMENTO = "SALA 203"
REQUERENTE_BAIRRO = "CENTRO"
REQUERENTE_CEP = "36010-071"
REQUERENTE_CIDADE = "Juiz de Fora/MG"
REQUERENTE_TELEFONE = "32999992797"
FINALIDADE = "TRANSMISSÃO"

OUTPUT_DIR = Path(__file__).parent / "output" / "pdfs"

# ─── Helpers ────────────────────────────────────────────────────────────────

def _mascarar(doc: str) -> str:
    d = re.sub(r"\D", "", doc)
    if len(d) >= 6:
        return d[:3] + "*" * (len(d) - 6) + d[-3:]
    return "***"

def _resultado_base(documento: str) -> dict:
    return {
        "endpoint": "cndi_pjf",
        "documento": _mascarar(documento),
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "status": "erro",
        "protocolo": None,
        "url_protocolo": None,
        "pdf_path": None,
        "detalhes_tecnicos": None,
    }

def _normalizar_inscricao_iptu(inscricao: str) -> str:
    """Remove caracteres especiais da inscrição IPTU (aceita 000.000/000 → 000000000)."""
    return re.sub(r"\D", "", inscricao)

# ─── 2captcha ───────────────────────────────────────────────────────────────

async def _resolver_recaptcha(api_key: str, sitekey: str, page_url: str, timeout: int = 120) -> str:
    """Envia reCaptcha v2 para o 2captcha e aguarda a solução."""
    logger.info("2captcha — Enviando reCaptcha v2 para resolução...")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://2captcha.com/in.php",
            data={
                "key": api_key,
                "method": "userrecaptcha",
                "googlekey": sitekey,
                "pageurl": page_url,
                "json": 1,
            },
        )
        data = resp.json()
        if data.get("status") != 1:
            raise RuntimeError(f"2captcha erro ao enviar: {data}")

        captcha_id = data["request"]
        logger.info(f"2captcha — ID do captcha: {captcha_id}. Aguardando resolução...")

        inicio = time.time()
        await asyncio.sleep(15)

        while time.time() - inicio < timeout:
            await asyncio.sleep(5)
            resp = await client.get(
                "https://2captcha.com/res.php",
                params={"key": api_key, "action": "get", "id": captcha_id, "json": 1},
            )
            data = resp.json()
            if data.get("status") == 1:
                token = data["request"]
                logger.info("2captcha — Captcha resolvido com sucesso.")
                return token
            if data.get("request") != "CAPCHA_NOT_READY":
                raise RuntimeError(f"2captcha erro na resolução: {data}")

        raise TimeoutError("2captcha — Timeout aguardando resolução do captcha.")

# ─── Login ───────────────────────────────────────────────────────────────────

async def _fazer_login(page, email: str, senha: str, twocaptcha_key: str) -> None:
    """Abre o portal, abre o modal de login, preenche campos, resolve captcha e autentica."""
    logger.info("Abrindo portal 1doc...")
    await page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)

    logger.info("Abrindo modal de login via JavaScript...")
    await page.evaluate("$('#modal_login').modal('show');")
    await page.wait_for_timeout(1500)

    logger.info("Preenchendo email...")
    await page.locator("#email").fill(email, force=True)

    logger.info("Preenchendo senha...")
    await page.locator("input[name='senha']").fill(senha, force=True)

    token = await _resolver_recaptcha(twocaptcha_key, RECAPTCHA_SITEKEY, PORTAL_URL)

    logger.info("Injetando token do captcha...")
    await page.evaluate(f"""
        const token = '{token}';
        const textareas = document.querySelectorAll('textarea');
        for (const t of textareas) {{ t.value = token; }}
        if (typeof ___grecaptcha_cfg !== 'undefined') {{
            const clients = ___grecaptcha_cfg.clients;
            for (const key in clients) {{
                const client = clients[key];
                for (const k in client) {{
                    if (client[k] && typeof client[k].callback === 'function') {{
                        client[k].callback(token);
                        break;
                    }}
                }}
            }}
        }}
    """)
    await page.wait_for_timeout(1000)

    logger.info("Submetendo formulário de login...")
    await page.evaluate("document.querySelector('#authForm').submit();")
    await page.wait_for_load_state("networkidle", timeout=15000)

    current_url = page.url
    if "formLoginPessoa" in current_url:
        raise RuntimeError("Login falhou — verifique email/senha ou captcha.")
    logger.info("Login concluído.")

# ─── Navegação até formulário CNDI ──────────────────────────────────────────

async def _navegar_para_cndi(page) -> None:
    """Navega até o formulário de CNDI após o login."""
    logger.info("Clicando em 'Protocolos'...")
    await page.get_by_role("link", name="Protocolos", exact=True).click()
    await page.wait_for_load_state("networkidle", timeout=10000)

    logger.info("Clicando em 'Prosseguir >>'...")
    await page.get_by_role("button", name="Prosseguir").click()
    await page.wait_for_load_state("networkidle", timeout=10000)

    logger.info("Buscando assunto 'CNDI'...")
    campo_assunto = await page.wait_for_selector("#codigo, input[placeholder*='Busca']", timeout=10000)
    await campo_assunto.fill("CNDI")
    await page.wait_for_timeout(1500)
    logger.info("Selecionando 'Certidão Negativa de Débito de Imóvel (CNDI)'...")
    await page.evaluate("""
        var selects = document.querySelectorAll('select');
        for (var s of selects) {
            var opt = s.querySelector('option[value="3666"]');
            if (opt) {
                s.value = '3666';
                s.dispatchEvent(new Event('change', {bubbles: true}));
                break;
            }
        }
    """)
    await page.wait_for_timeout(1500)
    await page.wait_for_load_state("networkidle", timeout=15000)
    logger.info("Formulário CNDI carregado.")

# ─── Preenchimento do formulário ─────────────────────────────────────────────

async def _preencher_contribuinte(page, cpf_cnpj: str, nome: str) -> None:
    """Preenche o campo Identifique Contribuinte (select2)."""
    logger.info("Preenchendo Contribuinte...")
    doc_limpo = re.sub(r"\D", "", cpf_cnpj)

    # Abre o select2 do contribuinte clicando no campo
    contribuinte_container = page.locator(".s2id_id_contribuinte, [id*=contribuinte]").first
    await contribuinte_container.click(force=True)
    await page.wait_for_timeout(500)

    # Digita o CPF/CNPJ no campo de busca do select2
    search_input = page.locator(".select2-drop:not(.select2-display-none) input.select2-input").first
    await search_input.fill(doc_limpo, force=True)
    await page.wait_for_timeout(2000)

    # Clica no resultado
    resultado = page.locator(".select2-results li:not(.select2-no-results)").first
    await resultado.click(force=True)
    await page.wait_for_timeout(500)
    logger.info(f"Contribuinte selecionado: {nome}")


async def _preencher_despachante(page) -> None:
    """Preenche o campo 'Identifique Despachante' com os dados fixos do Pedro."""
    logger.info("Preenchendo Despachante (Pedro Ivo)...")

    campo = await page.wait_for_selector(
        "text=Identifique Despachante >> .. >> input[placeholder*='CPF']",
        timeout=10000,
    )
    await campo.fill(DESPACHANTE_CPF)
    await page.wait_for_timeout(1500)
    await page.click(f"text={REQUERENTE_NOME}")
    logger.info("Despachante preenchido.")

async def _preencher_dados_identificacao(page, cpf_cnpj: str, nome_proprietario: str) -> None:
    """Preenche a seção 1 — Dados de Identificação."""
    logger.info("Preenchendo seção 1 — Dados de Identificação...")
    doc_limpo = re.sub(r"\D", "", cpf_cnpj)
    tipo_doc = "CNPJ" if len(doc_limpo) == 14 else "CPF"

    await page.fill(
        "input[name*='proprietario'], input[placeholder*='Proprietário'], input[placeholder*='PROPRIETÁRIO']",
        nome_proprietario,
    )

    select = page.locator("select").filter(has_text=tipo_doc).first
    await select.select_option(label=tipo_doc)
    await page.wait_for_timeout(500)

    await page.fill(
        f"input[name*='{tipo_doc.lower()}'], input[placeholder*='{tipo_doc}']",
        doc_limpo,
    )

    await page.fill(
        "input[name*='requerente'][name*='nome'], input[placeholder*='Requerente']",
        REQUERENTE_NOME,
    )
    await page.fill(
        "input[name*='requerente'][name*='cpf'], input[placeholder*='CPF do Requerente']",
        REQUERENTE_CPF,
    )
    await page.fill(
        "input[name*='endereco'][name*='req'], input[placeholder*='Endereço']",
        REQUERENTE_ENDERECO,
    )
    await page.fill(
        "input[name*='numero'][name*='req'], input[placeholder*='Número']",
        REQUERENTE_NUMERO,
    )
    await page.fill(
        "input[name*='complemento'][name*='req'], input[placeholder*='Complemento']",
        REQUERENTE_COMPLEMENTO,
    )
    await page.fill(
        "input[name*='bairro'][name*='req'], input[placeholder*='Bairro']",
        REQUERENTE_BAIRRO,
    )
    await page.fill("input[name*='cep'], input[placeholder*='CEP']", REQUERENTE_CEP)
    await page.fill("input[name*='cidade'], input[placeholder*='Cidade']", REQUERENTE_CIDADE)
    await page.fill("input[name*='telefone'], input[placeholder*='Telefone']", REQUERENTE_TELEFONE)

    logger.info("Seção 1 preenchida.")

async def _preencher_dados_imovel(
    page,
    inscricao_iptu: str,
    endereco: str,
    numero: str,
    complemento: str,
    bairro: str,
) -> None:
    """Preenche a seção 2 — Dados do Imóvel."""
    logger.info("Preenchendo seção 2 — Dados do Imóvel...")
    inscricao_limpa = _normalizar_inscricao_iptu(inscricao_iptu)

    await page.fill(
        "input[name*='inscricao'][name*='iptu'], input[placeholder*='Inscrição'][placeholder*='IPTU']",
        inscricao_limpa,
    )
    await page.fill(
        "input[name*='endereco'][name*='imovel'], input[placeholder*='Endereço do Imóvel']",
        endereco,
    )
    await page.fill(
        "input[name*='numero'][name*='imovel'], input[placeholder*='Número do Imóvel']",
        numero,
    )

    if complemento:
        await page.fill(
            "input[name*='complemento'][name*='imovel'], input[placeholder*='Complemento do Imóvel']",
            complemento,
        )

    await page.fill(
        "input[name*='bairro'][name*='imovel'], input[placeholder*='Bairro do Imóvel']",
        bairro,
    )

    logger.info("Seção 2 preenchida.")

async def _preencher_finalidade(page) -> None:
    """Preenche a seção 3 — Finalidade."""
    logger.info("Preenchendo seção 3 — Finalidade...")
    await page.fill(
        "input[name*='finalidade'], textarea[name*='finalidade'], input[placeholder*='Finalidade']",
        FINALIDADE,
    )
    logger.info("Seção 3 preenchida.")

# ─── Protocolar ──────────────────────────────────────────────────────────────

async def _protocolar(page) -> tuple[str, str]:
    """Clica em Protocolar e captura o número do protocolo e a URL."""
    logger.info("Clicando em 'Protocolar'...")
    await page.click("button:has-text('Protocolar'), input[value*='Protocolar']")
    await page.wait_for_load_state("networkidle", timeout=20000)

    logger.info("Aguardando número do protocolo...")
    await page.wait_for_selector("a[href*='protocolo'], a:has-text('Protocolo')", timeout=15000)

    link = page.locator("a[href*='protocolo'], a:has-text('Protocolo nº')").first
    url_protocolo = await link.get_attribute("href")
    texto_protocolo = await link.text_content()

    match = re.search(r"[\d\-\.\/]+\/\d{4}", texto_protocolo or "")
    numero_protocolo = match.group(0).strip() if match else texto_protocolo.strip()

    if url_protocolo and not url_protocolo.startswith("http"):
        base = "https://juizdefora.1doc.com.br"
        url_protocolo = base + url_protocolo

    logger.info(f"Protocolo capturado: {numero_protocolo}")
    logger.info(f"URL do protocolo: {url_protocolo}")

    return numero_protocolo, url_protocolo

# ─── Download do PDF ─────────────────────────────────────────────────────────

async def _baixar_pdf_protocolo(
    context,
    url_protocolo: str,
    numero_protocolo: str,
    documento: str,
) -> str | None:
    """
    Acessa a URL do protocolo, aguarda o Despacho 2, clica em Verificar
    e captura o PDF via response event.
    """
    logger.info(f"Acessando URL do protocolo: {url_protocolo}")
    page = await context.new_page()

    pdf_bytes = None
    pdf_url = None

    async def capturar_pdf(response):
        nonlocal pdf_bytes, pdf_url
        ct = response.headers.get("content-type", "")
        if "pdf" in ct and pdf_bytes is None:
            pdf_url = response.url
            logger.info(f"PDF detectado via response event — URL: {pdf_url}")
            try:
                pdf_bytes = await response.body()
            except Exception as e:
                logger.warning(f"Falha ao capturar body do response: {e}")

    context.on("response", capturar_pdf)

    try:
        await page.goto(url_protocolo, wait_until="networkidle", timeout=30000)

        logger.info("Aguardando Despacho 2 no protocolo (até 10s)...")
        await page.wait_for_selector(
            "text=Despacho 2, text=AO SOLICITANTE - ENVIO DE CERTIDÃO",
            timeout=10000,
        )

        logger.info("Despacho 2 encontrado. Clicando em 'Verificar'...")
        await page.click("button:has-text('Verificar'), a:has-text('Verificar')")
        await page.wait_for_timeout(8000)

        if pdf_bytes and len(pdf_bytes) > 1000 and pdf_bytes[:4] == b"%PDF":
            doc_limpo = re.sub(r"\D", "", documento)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            pasta = OUTPUT_DIR / doc_limpo
            pasta.mkdir(parents=True, exist_ok=True)
            nome_arquivo = f"cndi_pjf_{ts}.pdf"
            caminho = pasta / nome_arquivo
            caminho.write_bytes(pdf_bytes)
            logger.info(f"PDF salvo: {nome_arquivo} ({len(pdf_bytes)} bytes)")
            return str(caminho)

        if pdf_url:
            logger.info(f"Tentando download direto: {pdf_url}")
            resp = await context.request.get(pdf_url)
            body = await resp.body()
            if body[:4] == b"%PDF":
                doc_limpo = re.sub(r"\D", "", documento)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                pasta = OUTPUT_DIR / doc_limpo
                pasta.mkdir(parents=True, exist_ok=True)
                nome_arquivo = f"cndi_pjf_{ts}.pdf"
                caminho = pasta / nome_arquivo
                caminho.write_bytes(body)
                logger.info(f"PDF salvo via fallback: {nome_arquivo} ({len(body)} bytes)")
                return str(caminho)

        logger.warning("PDF não capturado nesta tentativa.")
        return None

    except Exception as e:
        logger.warning(f"Erro ao tentar baixar PDF: {e}")
        return None
    finally:
        context.remove_listener("response", capturar_pdf)
        await page.close()

# ─── Função principal ────────────────────────────────────────────────────────

async def solicitar_cndi(
    cpf_cnpj_vendedor: str,
    nome_vendedor: str,
    inscricao_iptu: str,
    endereco_imovel: str,
    numero_imovel: str,
    complemento_imovel: str,
    bairro_imovel: str,
) -> dict:
    """
    Solicita a CNDI no portal 1doc da PJF.
    Retorna dict com status, protocolo, url_protocolo e pdf_path (se já disponível).
    """
    resultado = _resultado_base(cpf_cnpj_vendedor)
    inicio = time.time()

    email = os.environ.get("ONEDOC_EMAIL", "")
    senha = os.environ.get("ONEDOC_SENHA", "")
    twocaptcha_key = os.environ.get("TWOCAPTCHA_API_KEY", "")

    if not email or not senha:
        resultado["detalhes_tecnicos"] = "ONEDOC_EMAIL ou ONEDOC_SENHA não definidos no ambiente."
        return resultado

    if not twocaptcha_key:
        resultado["detalhes_tecnicos"] = "TWOCAPTCHA_API_KEY não definida no ambiente."
        return resultado

    logger.info("=" * 60)
    logger.info("CNDI PJF — Iniciando solicitação")
    logger.info(f"Vendedor: {_mascarar(cpf_cnpj_vendedor)} | IPTU: {inscricao_iptu}")
    logger.info("=" * 60)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await _fazer_login(page, email, senha, twocaptcha_key)
            await _navegar_para_cndi(page)
            await _preencher_contribuinte(page, cpf_cnpj_vendedor, nome_vendedor)
            await _preencher_despachante(page)
            await _preencher_dados_identificacao(page, cpf_cnpj_vendedor, nome_vendedor)
            await _preencher_dados_imovel(
                page,
                inscricao_iptu,
                endereco_imovel,
                numero_imovel,
                complemento_imovel,
                bairro_imovel,
            )
            await _preencher_finalidade(page)
            numero_protocolo, url_protocolo = await _protocolar(page)

            resultado["status"] = "protocolado"
            resultado["protocolo"] = numero_protocolo
            resultado["url_protocolo"] = url_protocolo

            logger.info("=" * 60)
            logger.info("CNDI PJF — Protocolado com sucesso!")
            logger.info(f"Protocolo: {numero_protocolo}")
            logger.info(f"URL: {url_protocolo}")
            logger.info("Aguardando e-mail de retorno (1h–1 dia).")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Erro durante solicitação CNDI: {e}", exc_info=True)
            resultado["detalhes_tecnicos"] = str(e)
        finally:
            resultado["duracao_segundos"] = round(time.time() - inicio, 1)
            await browser.close()
            logger.info("Browser fechado.")

    return resultado


async def baixar_cndi(
    url_protocolo: str,
    numero_protocolo: str,
    documento: str,
) -> dict:
    """
    Tenta baixar o PDF da CNDI a partir da URL do protocolo.
    Deve ser chamado quando o e-mail de retorno indicar emissão (Despacho 2).
    Retorna dict com status e pdf_path.
    """
    resultado = {
        "endpoint": "cndi_pjf",
        "protocolo": numero_protocolo,
        "status": "erro",
        "pdf_path": None,
        "detalhes_tecnicos": None,
    }

    email = os.environ.get("ONEDOC_EMAIL", "")
    senha = os.environ.get("ONEDOC_SENHA", "")
    twocaptcha_key = os.environ.get("TWOCAPTCHA_API_KEY", "")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await _fazer_login(page, email, senha, twocaptcha_key)
            pdf_path = await _baixar_pdf_protocolo(context, url_protocolo, numero_protocolo, documento)

            if pdf_path:
                resultado["status"] = "concluido"
                resultado["pdf_path"] = pdf_path
            else:
                resultado["status"] = "aguardando"
                resultado["detalhes_tecnicos"] = "PDF não disponível ainda."

        except Exception as e:
            logger.error(f"Erro ao baixar CNDI: {e}", exc_info=True)
            resultado["detalhes_tecnicos"] = str(e)
        finally:
            await browser.close()

    return resultado


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 8:
        print(
            "Uso: python cndi_scraper.py <cpf_cnpj> \"<nome>\" <inscricao_iptu> "
            "\"<endereco>\" <numero> \"<complemento>\" \"<bairro>\""
        )
        sys.exit(1)

    resultado = asyncio.run(
        solicitar_cndi(
            cpf_cnpj_vendedor=sys.argv[1],
            nome_vendedor=sys.argv[2],
            inscricao_iptu=sys.argv[3],
            endereco_imovel=sys.argv[4],
            numero_imovel=sys.argv[5],
            complemento_imovel=sys.argv[6],
            bairro_imovel=sys.argv[7],
        )
    )

    import json
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
