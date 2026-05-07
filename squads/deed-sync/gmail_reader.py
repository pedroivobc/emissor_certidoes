"""
gmail_reader.py
Leitor de emails OTP do RUPE TJMG via Gmail API (OAuth 2.0).

Pré-requisitos:
  - google_oauth_token.json gerado pelo oauth_setup.py (mesma pasta)
  - Escopo gmail.readonly habilitado
"""

import asyncio
import base64
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger("deed-sync.gmail_reader")

# ─── Constantes ────────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
PASTA = Path(__file__).parent
ARQ_TOKEN = PASTA / "google_oauth_token.json"

REMETENTE_RUPE = "rupecertidoes1@tjmg.jus.br"
ASSUNTO_RUPE = "Solicitação de certidão - Validação de e-mail"
# Padrão: XXXX-XXXX-XXXX-XXXX-XXXX  (5 grupos de 4 dígitos)
REGEX_OTP = re.compile(r"\d{4}-\d{4}-\d{4}-\d{4}-\d{4}")


# ─── Classe principal ──────────────────────────────────────────────────────────

class GmailReader:
    """Leitor de OTP do RUPE TJMG via Gmail API."""

    def __init__(self):
        self.creds = self._carregar_credenciais()
        self.service = build("gmail", "v1", credentials=self.creds, cache_discovery=False)

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _carregar_credenciais(self) -> Credentials:
        if not ARQ_TOKEN.exists():
            raise RuntimeError(
                f"Token OAuth não encontrado em {ARQ_TOKEN}. "
                "Execute oauth_setup.py primeiro para gerar o token."
            )
        creds = Credentials.from_authorized_user_file(str(ARQ_TOKEN), SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                logger.info("Token expirado — renovando automaticamente...")
                creds.refresh(Request())
                ARQ_TOKEN.write_text(creds.to_json())
                logger.info("Token renovado e salvo.")
            else:
                raise RuntimeError(
                    "Token OAuth inválido e não pode ser renovado automaticamente. "
                    "Execute oauth_setup.py de novo."
                )
        return creds

    def testar_acesso(self) -> str:
        """
        Sanity check — confirma que a API está acessível.
        Retorna o endereço de email autenticado.
        Levanta exceção se falhar.
        """
        profile = self.service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "desconhecido")
        logger.info("Gmail API OK — conta autenticada: %s", email)
        return email

    # ── Polling de OTP ────────────────────────────────────────────────────────

    async def aguardar_otp(self, desde: datetime, timeout: int = 60) -> str:
        """
        Faz polling no Gmail buscando email do RUPE recebido APÓS `desde`.

        Args:
            desde:   datetime UTC de quando o botão "Gerar Código" foi clicado.
            timeout: Máximo de segundos de espera (padrão: 60).

        Returns:
            Código OTP no formato XXXX-XXXX-XXXX-XXXX-XXXX.

        Raises:
            TimeoutError: Se nenhum OTP chegar dentro do timeout.
        """
        # Gmail API 'after' usa Unix timestamp
        ts_unix = int(desde.timestamp())
        query = f"from:{REMETENTE_RUPE} after:{ts_unix}"
        logger.info("Aguardando OTP do RUPE (timeout=%ds)...", timeout)

        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        intervalo = 3  # segundos entre polls

        # Controla IDs já vistos para não processar o mesmo email duas vezes
        vistos: set[str] = set()

        while loop.time() < deadline:
            try:
                results = await asyncio.to_thread(
                    lambda: self.service.users().messages().list(
                        userId="me", q=query, maxResults=5
                    ).execute()
                )
            except Exception as exc:
                logger.warning("Erro ao listar emails (tentando novamente): %s", exc)
                await asyncio.sleep(intervalo)
                continue

            messages = results.get("messages", [])

            for msg_info in messages:
                msg_id = msg_info["id"]
                if msg_id in vistos:
                    continue
                vistos.add(msg_id)

                try:
                    msg = await asyncio.to_thread(
                        lambda mid=msg_id: self.service.users().messages().get(
                            userId="me", id=mid, format="full"
                        ).execute()
                    )
                except Exception as exc:
                    logger.warning("Erro ao ler email %s: %s", msg_id, exc)
                    continue

                # Validar assunto
                headers = msg.get("payload", {}).get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"].lower() == "subject"),
                    "",
                )
                if ASSUNTO_RUPE not in subject:
                    logger.debug("Email ignorado (assunto não coincide): %s", subject)
                    continue

                # Extrair corpo e buscar OTP
                body = self._extrair_corpo(msg["payload"])
                match = REGEX_OTP.search(body)
                if match:
                    logger.info("OTP recebido do RUPE.")
                    return match.group(0)
                else:
                    logger.warning(
                        "Email do RUPE encontrado mas OTP não detectado no corpo. "
                        "Verifique o padrão regex."
                    )

            tempo_restante = deadline - loop.time()
            if tempo_restante <= 0:
                break
            esperar = min(intervalo, tempo_restante)
            await asyncio.sleep(esperar)

        raise TimeoutError(
            f"OTP do RUPE não chegou em {timeout}s. "
            "Verifique a caixa de entrada de contato@clementeassessoria.com "
            "e a pasta de spam."
        )

    # ── Extração de corpo ─────────────────────────────────────────────────────

    def _extrair_corpo(self, payload: dict) -> str:
        """
        Extrai texto do corpo do email (suporta multipart recursivo).
        Prioriza text/plain; fallback pra text/html.
        """
        texto_plain = ""
        texto_html = ""

        if "parts" in payload:
            for part in payload["parts"]:
                mime = part.get("mimeType", "")
                if mime == "text/plain":
                    texto_plain += self._decodificar_part(part)
                elif mime == "text/html":
                    texto_html += self._decodificar_part(part)
                elif mime.startswith("multipart/"):
                    # Recursivo para parts aninhadas (multipart/alternative, etc.)
                    sub = self._extrair_corpo(part)
                    if sub:
                        return sub
        else:
            # Mensagem simples (não-multipart)
            mime = payload.get("mimeType", "")
            if mime in ("text/plain", "text/html"):
                return self._decodificar_part(payload)

        return texto_plain or texto_html

    def _decodificar_part(self, part: dict) -> str:
        """Decodifica base64url do corpo de uma part de email."""
        data = part.get("body", {}).get("data", "")
        if not data:
            return ""
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        except Exception:
            return ""
