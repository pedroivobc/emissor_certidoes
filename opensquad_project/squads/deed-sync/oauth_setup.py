"""
oauth_setup.py
Setup inicial do OAuth com Gmail API.

Roda UMA VEZ pra autorizar o app. Depois disso, o scraper TJMG
usa o google_oauth_token.json salvo automaticamente.

Uso: python oauth_setup.py
"""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Escopo: SOMENTE LEITURA do Gmail (mais seguro)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

PASTA = Path(__file__).parent
ARQ_CLIENT = PASTA / "google_oauth_client.json"
ARQ_TOKEN = PASTA / "google_oauth_token.json"


def autorizar() -> Credentials:
    """Faz o fluxo OAuth se necessário e retorna credenciais válidas."""
    creds = None

    # Se já tem token salvo, tenta usar
    if ARQ_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(ARQ_TOKEN), SCOPES)

    # Se não tem ou expirou, faz o fluxo
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expirado. Renovando automaticamente...")
            creds.refresh(Request())
        else:
            print("Iniciando fluxo OAuth — uma janela do navegador vai abrir.")
            print("Autoriza o app contato@clementeassessoria.com a ler emails.")
            flow = InstalledAppFlow.from_client_secrets_file(str(ARQ_CLIENT), SCOPES)
            creds = flow.run_local_server(port=0)

        # Salva pra próximas execuções
        ARQ_TOKEN.write_text(creds.to_json())
        os.chmod(ARQ_TOKEN, 0o600)  # só o dono pode ler/escrever
        print(f"Token salvo em: {ARQ_TOKEN}")

    return creds


def testar_acesso(creds: Credentials):
    """Testa que conseguimos ler o perfil do Gmail."""
    service = build("gmail", "v1", credentials=creds)
    profile = service.users().getProfile(userId="me").execute()
    email = profile.get("emailAddress")
    total = profile.get("messagesTotal")
    print(f"\nAutorizacao OK!")
    print(f"Email autorizado: {email}")
    print(f"Total de mensagens na caixa: {total}")


if __name__ == "__main__":
    if not ARQ_CLIENT.exists():
        print(f"ERRO: arquivo {ARQ_CLIENT} nao encontrado.")
        print("Verifique se google_oauth_client.json esta na pasta deed-sync.")
        exit(1)

    creds = autorizar()
    testar_acesso(creds)
