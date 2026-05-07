"""
infosimples_client.py
Funções assíncronas para consulta de certidões via Infosimples API v2.

Endpoints cobertos:
  - TST/CNDT   → tribunal/tst/cndt
  - TRF6 Cível → tribunal/trf6/certidao
  - TRT3/CEAT  → tribunal/trt3/ceat
  - PGFN       → receita-federal/pgfn/2via  (fallback: /nova)

Cada função retorna um dict no formato padrão:
  {
      "sucesso": bool,
      "code": int,
      "code_message": str,
      "pdf_path": str | None,       # preenchido pelo scraper.py após download
      "pdf_url_temporaria": str | None,
      "dados": dict | None,
      "erro": str | None,
      # PGFN também inclui: "modo", "tentativas"
  }
"""

import asyncio
import logging
import os

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://api.infosimples.com/api/v2/consultas/"
TIMEOUT_INFOSIMPLES = 660  # segundos (servidor side-timeout é 600s + folga)

# Códigos da Infosimples que disparam fallback PGFN (2via → nova).
# - 612: "A consulta não retornou dados no site ou aplicativo de origem"
#         → certidão de 2via não existe, faz sentido tentar emitir nova.
# - 600: "Um erro inesperado ocorreu e será analisado"
#         → falha intermitente do portal da Receita; tentar /nova
#         pode dar certo numa segunda passada.
#
# Para adicionar mais códigos no futuro, basta incluir aqui — a lógica
# de fallback fica inalterada.
CODES_FALLBACK_PGFN = {600, 612}


def _get_token() -> str:
    token = os.getenv("INFOSIMPLES_TOKEN")
    if not token:
        raise RuntimeError(
            "INFOSIMPLES_TOKEN não encontrado nas variáveis de ambiente. "
            "Verifique se o arquivo credenciais.env foi carregado corretamente."
        )
    return token


def _mask_token(token: str) -> str:
    """Mascara o token para evitar exposição em logs."""
    if not token or len(token) < 8:
        return "***"
    return token[:4] + "***" + token[-4:]


def _mask_doc(cpf_ou_cnpj: str) -> str:
    """Mascara documento para logs (mostra só primeiros 4 dígitos)."""
    if not cpf_ou_cnpj or len(cpf_ou_cnpj) < 4:
        return "***"
    return cpf_ou_cnpj[:4] + "***"


def _build_doc_params(cpf_ou_cnpj: str) -> dict:
    """Retorna o parâmetro correto (cpf ou cnpj) baseado no tamanho."""
    if len(cpf_ou_cnpj) == 11:
        return {"cpf": cpf_ou_cnpj}
    elif len(cpf_ou_cnpj) == 14:
        return {"cnpj": cpf_ou_cnpj}
    else:
        raise ValueError(
            f"Documento inválido: esperado 11 (CPF) ou 14 (CNPJ) dígitos, "
            f"recebido {len(cpf_ou_cnpj)}."
        )


def _normalizar_dados(data_list: list) -> dict:
    """Extrai e normaliza o primeiro elemento da lista de dados do JSON."""
    if data_list and isinstance(data_list, list) and len(data_list) > 0:
        return data_list[0] if isinstance(data_list[0], dict) else {}
    return {}


def _extrair_pdf_url(response_json: dict) -> str | None:
    """Extrai a URL temporária do PDF de site_receipts[0]."""
    try:
        receipts = response_json.get("site_receipts", [])
        if receipts and isinstance(receipts, list):
            return receipts[0]
    except Exception:
        pass
    return None


def _resultado_erro(
    code: int | None,
    code_message: str | None,
    mensagem_amigavel: str,
) -> dict:
    return {
        "sucesso": False,
        "code": code,
        "code_message": code_message,
        "pdf_path": None,
        "pdf_url_temporaria": None,
        "dados": None,
        "erro": mensagem_amigavel,
    }


def _resultado_sucesso(response_json: dict) -> dict:
    """Constrói resultado de sucesso a partir do JSON da Infosimples.

    Extrai automaticamente a URL do PDF de site_receipts[0].
    """
    code = response_json.get("code")
    code_message = response_json.get("code_message", "")
    dados = _normalizar_dados(response_json.get("data", []))
    pdf_url = _extrair_pdf_url(response_json)
    return {
        "sucesso": True,
        "code": code,
        "code_message": code_message,
        "pdf_path": None,  # preenchido pelo scraper.py após download
        "pdf_url_temporaria": pdf_url,
        "dados": dados,
        "erro": None,
    }


async def _post_infosimples(
    endpoint_path: str,
    params: dict,
    session: aiohttp.ClientSession,
    retries: int = 1,
) -> dict:
    """
    Faz POST para a Infosimples API com retry automático em caso de falha de rede.
    Nunca loga o token.

    Retorna o JSON completo da resposta ou levanta exceção.
    """
    token = _get_token()
    url = BASE_URL + endpoint_path
    payload = {**params, "token": token, "timeout": 600}
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_INFOSIMPLES)

    last_exc: Exception | None = None
    for attempt in range(1, retries + 2):  # retries+1 tentativas no total
        try:
            logger.debug("POST %s (tentativa %d)", url, attempt)
            async with session.post(url, data=payload, timeout=timeout) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_exc = exc
            masked = _mask_token(token)
            logger.warning(
                "Tentativa %d/%d falhou para %s (token: %s): %s",
                attempt, retries + 1, endpoint_path, masked, type(exc).__name__,
            )
            if attempt <= retries:
                await asyncio.sleep(5)

    raise RuntimeError(
        f"Falha após {retries + 1} tentativa(s) em '{endpoint_path}': {last_exc}"
    )


# ─── Consultas públicas ────────────────────────────────────────────────────────

async def consultar_tst(cpf_ou_cnpj: str, session: aiohttp.ClientSession) -> dict:
    """
    Consulta TST/CNDT — Certidão Negativa de Débitos Trabalhistas.

    Endpoint: tribunal/tst/cndt
    Custo: ~R$ 0,24
    """
    logger.info("Consultando TST/CNDT para documento %s...", _mask_doc(cpf_ou_cnpj))
    try:
        params = _build_doc_params(cpf_ou_cnpj)
        resp = await _post_infosimples("tribunal/tst/cndt", params, session)

        code = resp.get("code")
        code_message = resp.get("code_message", "")

        if code == 200:
            result = _resultado_sucesso(resp)
            logger.info("TST/CNDT ✓ (code %d)", code)
            return result
        else:
            logger.warning("TST/CNDT retornou code %s: %s", code, code_message)
            return _resultado_erro(
                code, code_message,
                f"Não foi possível emitir a certidão TST. Code: {code} — {code_message}",
            )

    except Exception as exc:
        logger.error("TST/CNDT — exceção: %s", exc)
        return _resultado_erro(None, None, f"Erro ao consultar TST: {exc}")


async def consultar_trf6(cpf_ou_cnpj: str, session: aiohttp.ClientSession) -> dict:
    """
    Consulta TRF6 Cível — Certidão da 6ª Região.

    Endpoint: tribunal/trf6/certidao
    Parâmetros fixos: tipo_certidao=CIVEL, orgao=MG, considera_filiais=1
    Custo: ~R$ 0,24
    """
    logger.info("Consultando TRF6 para documento %s...", _mask_doc(cpf_ou_cnpj))
    try:
        params = {
            **_build_doc_params(cpf_ou_cnpj),
            "tipo_certidao": "CIVEL",
            "orgao": "MG",
            "considera_filiais": "1",
        }
        resp = await _post_infosimples("tribunal/trf6/certidao", params, session)

        code = resp.get("code")
        code_message = resp.get("code_message", "")

        if code == 200:
            result = _resultado_sucesso(resp)
            logger.info("TRF6 ✓ (code %d)", code)
            return result
        else:
            logger.warning("TRF6 retornou code %s: %s", code, code_message)
            return _resultado_erro(
                code, code_message,
                f"Não foi possível emitir a certidão TRF6. Code: {code} — {code_message}",
            )

    except Exception as exc:
        logger.error("TRF6 — exceção: %s", exc)
        return _resultado_erro(None, None, f"Erro ao consultar TRF6: {exc}")


async def consultar_trt3(cpf_ou_cnpj: str, session: aiohttp.ClientSession) -> dict:
    """
    Consulta TRT3/CEAT — Certidão de Ações Trabalhistas (3ª Região / MG).

    Endpoint: tribunal/trt3/ceat
    Custo: ~R$ 0,24
    """
    logger.info("Consultando TRT3/CEAT para documento %s...", _mask_doc(cpf_ou_cnpj))
    try:
        params = _build_doc_params(cpf_ou_cnpj)
        resp = await _post_infosimples("tribunal/trt3/ceat", params, session)

        code = resp.get("code")
        code_message = resp.get("code_message", "")

        if code == 200:
            result = _resultado_sucesso(resp)
            logger.info("TRT3/CEAT ✓ (code %d)", code)
            return result
        else:
            logger.warning("TRT3/CEAT retornou code %s: %s", code, code_message)
            return _resultado_erro(
                code, code_message,
                f"Não foi possível emitir a certidão TRT3. Code: {code} — {code_message}",
            )

    except Exception as exc:
        logger.error("TRT3/CEAT — exceção: %s", exc)
        return _resultado_erro(None, None, f"Erro ao consultar TRT3: {exc}")


async def consultar_pgfn(
    cpf_ou_cnpj: str,
    birthdate: str | None,
    session: aiohttp.ClientSession,
) -> dict:
    """
    Consulta PGFN — Certidão de Regularidade Fiscal.

    Lógica composta:
      1. Tenta receita-federal/pgfn/2via
      2. Se code estiver em CODES_FALLBACK_PGFN (612, 600) → tenta /nova
      3. Se /nova também falhar com code em CODES_FALLBACK_PGFN → cliente
         provavelmente irregular ou portal com problema persistente; retorna
         erro amigável.

    PF: requer birthdate (AAAA-MM-DD)
    PJ: birthdate ignorado
    Custo: R$ 0,26 por chamada (até R$ 0,52 com fallback)
    """
    logger.info("Consultando PGFN para documento %s...", _mask_doc(cpf_ou_cnpj))

    doc_params = _build_doc_params(cpf_ou_cnpj)

    # PF requer birthdate
    if len(cpf_ou_cnpj) == 11:
        if not birthdate:
            return _resultado_erro(
                None, None,
                "birthdate é obrigatório para consulta PGFN de pessoa física.",
            )
        doc_params["birthdate"] = birthdate

    # ── Tentativa 1: /2via ────────────────────────────────────────────────────
    try:
        resp_2via = await _post_infosimples("receita-federal/pgfn/2via", doc_params, session)
        code_2via = resp_2via.get("code")
        code_msg_2via = resp_2via.get("code_message", "")

        if code_2via == 200:
            result = _resultado_sucesso(resp_2via)
            result["modo"] = "2via"
            result["tentativas"] = 1
            logger.info("PGFN/2via ✓ (code 200)")
            return result

        elif code_2via in CODES_FALLBACK_PGFN:
            logger.info(
                "PGFN/2via retornou %s (%s) — tentando /nova (fallback)...",
                code_2via, code_msg_2via,
            )

            # ── Tentativa 2: /nova (fallback) ─────────────────────────────────
            try:
                resp_nova = await _post_infosimples(
                    "receita-federal/pgfn/nova", doc_params, session,
                )
                code_nova = resp_nova.get("code")
                code_msg_nova = resp_nova.get("code_message", "")

                if code_nova == 200:
                    result = _resultado_sucesso(resp_nova)
                    result["modo"] = "nova"
                    result["tentativas"] = 2
                    logger.info("PGFN/nova ✓ (code 200) — após fallback de 2via (%s)", code_2via)
                    return result

                elif code_nova in CODES_FALLBACK_PGFN:
                    logger.warning(
                        "PGFN/nova também retornou %s (%s) — "
                        "provável irregularidade fiscal ou problema persistente do portal.",
                        code_nova, code_msg_nova,
                    )
                    err = _resultado_erro(
                        code_nova, code_msg_nova,
                        "Não foi possível emitir a certidão para esse CPF/CNPJ — "
                        "consulte a Receita Federal ou tente novamente mais tarde.",
                    )
                    err["modo"] = "nova"
                    err["tentativas"] = 2
                    return err

                else:
                    logger.warning("PGFN/nova retornou code %s: %s", code_nova, code_msg_nova)
                    err = _resultado_erro(
                        code_nova, code_msg_nova,
                        f"Não foi possível emitir a certidão PGFN (após fallback). "
                        f"Code: {code_nova} — {code_msg_nova}",
                    )
                    err["modo"] = "nova"
                    err["tentativas"] = 2
                    return err

            except Exception as exc_nova:
                logger.error("PGFN/nova — exceção (após 2via %s): %s", code_2via, exc_nova)
                err = _resultado_erro(
                    None, None,
                    f"Erro ao consultar PGFN/nova após fallback de 2via: {exc_nova}",
                )
                err["modo"] = "nova"
                err["tentativas"] = 2
                return err

        else:
            logger.warning("PGFN/2via retornou code %s: %s", code_2via, code_msg_2via)
            err = _resultado_erro(
                code_2via, code_msg_2via,
                f"Não foi possível emitir a certidão PGFN. "
                f"Code: {code_2via} — {code_msg_2via}",
            )
            err["modo"] = "2via"
            err["tentativas"] = 1
            return err

    except Exception as exc_2via:
        logger.error("PGFN/2via — exceção: %s", exc_2via)
        err = _resultado_erro(None, None, f"Erro ao consultar PGFN/2via: {exc_2via}")
        err["modo"] = "2via"
        err["tentativas"] = 1
        return err