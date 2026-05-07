"""
test_gmail.py
Teste isolado do GmailReader — valida autenticação e polling de OTP sem Playwright.

Uso:
  1. Abra o portal RUPE manualmente no browser:
     https://rupe.tjmg.jus.br/rupe/justica/publico/certidoes/criarSolicitacaoCertidao.rupe?solicitacaoPublica=true
  2. Preencha qualquer dado e clique em "Gerar Código"
  3. No popup que abrir, clique em "Enviar Código de Verificação"
  4. Pressione Enter no terminal para iniciar o polling (timeout: 180s)
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

from gmail_reader import GmailReader


async def main():
    print("\n=== Teste isolado do GmailReader ===\n")

    # 1. Testar autenticação
    print("→ Inicializando GmailReader...")
    try:
        gmail = GmailReader()
        email = gmail.testar_acesso()
        print(f"✓ Autenticação OK — conta: {email}\n")
    except Exception as exc:
        print(f"✗ Falha na autenticação: {exc}")
        print("  Execute oauth_setup.py para gerar/renovar o token.")
        sys.exit(1)

    # 2. Aguardar OTP
    print("→ Agora abra o portal RUPE no browser, preencha os dados, clique em")
    print("  'Gerar Código' e depois 'Enviar Código de Verificação' no popup.")
    print("  Você tem 180 segundos para isso depois de pressionar Enter.\n")
    input("  Pressione Enter quando estiver pronto para iniciar o polling...")

    timestamp = datetime.now(timezone.utc)
    print(f"\n→ Polling iniciado em {timestamp.isoformat()}. Aguardando OTP...")

    try:
        otp = await gmail.aguardar_otp(timestamp, timeout=180)
        print(f"\n✓ OTP capturado com sucesso!")
        # NÃO logar o OTP completo — apenas confirmar que veio
        print(f"  Formato: {otp[:4]}-****-****-****-****")
        print(f"  Comprimento total: {len(otp)} caracteres")
    except TimeoutError as exc:
        print(f"\n✗ Timeout: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n✗ Erro inesperado: {exc}")
        sys.exit(1)

    print("\n=== Teste concluído com sucesso ===\n")


if __name__ == "__main__":
    asyncio.run(main())
