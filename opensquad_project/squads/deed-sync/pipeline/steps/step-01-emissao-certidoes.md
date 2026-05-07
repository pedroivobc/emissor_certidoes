---
execution: inline
agent: squads/deed-sync/agents/emissor-certidoes
inputFile: squads/deed-sync/output/input.json
outputFile: squads/deed-sync/output/resultado.json
---

# Step 01: Emissão Automática de Certidões

## Context Loading

Carregar antes de executar:
- `squads/deed-sync/output/input.json` — CPF e Nome do consultado recebidos via API
- `squads/deed-sync/agents/emissor-certidoes.agent.md` — persona e framework operacional do agente
- `credenciais.env` — TWOCAPTCHA_API_KEY necessária para resolução de captchas
- `squads/deed-sync/squad.yaml` — configurações do squad (output_dir, dados do solicitante fixo)

## Instructions

### Process

1. **Validar input**: Verificar que `cpf` e `nome` estão presentes e que o CPF tem 11 dígitos válidos (após remover pontuação). Rejeitar imediatamente com erro descritivo se inválido.
2. **Criar diretório de saída**: Garantir que `output/pdfs/{CPF_limpo}/` existe antes de qualquer navegação.
3. **Executar `scraper.py`**: Acionar o script Playwright passando `cpf` e `nome` como argumentos. O script processa os 6 órgãos sequencialmente (TST → TRF6 eproc → TRF6 PJE → TRT3 → TJMG/RUPE → PGFN).
4. **Coletar resultados**: Ler o JSON de resultado retornado pelo scraper, contendo status (sucesso/falha), caminho do arquivo e número de tentativas para cada certidão.
5. **Salvar resultado**: Escrever o JSON consolidado em `output/resultado.json`.
6. **Retornar resposta**: Formatar e retornar o JSON final para a API FastAPI.

## Output Format

```json
{
  "status": "concluido | parcial | falha",
  "consultado": {
    "cpf": "000.000.000-00",
    "nome": "Nome Completo do Consultado"
  },
  "certidoes": [
    {
      "orgao": "TST | TRF6_EPROC | TRF6_PJE | TRT3 | TJMG_RUPE | PGFN",
      "status": "sucesso | falha",
      "arquivo": "output/pdfs/{CPF}/{ORGAO}_{CPF_limpo}_{Nome}.pdf",
      "tentativas": 1,
      "erro": "descrição do erro (apenas se status=falha)"
    }
  ],
  "total": 6,
  "sucessos": 0,
  "falhas": 0,
  "duracao_segundos": 0
}
```

## Output Example

> Exemplo de execução completa bem-sucedida para CPF 123.456.789-00, João da Silva Santos.

```json
{
  "status": "concluido",
  "consultado": {
    "cpf": "123.456.789-00",
    "nome": "João da Silva Santos"
  },
  "certidoes": [
    {
      "orgao": "TST",
      "status": "sucesso",
      "arquivo": "output/pdfs/12345678900/TST_12345678900_JoaoSilva.pdf",
      "tentativas": 1
    },
    {
      "orgao": "TRF6_EPROC",
      "status": "sucesso",
      "arquivo": "output/pdfs/12345678900/TRF6EPROC_12345678900_JoaoSilva.pdf",
      "tentativas": 1
    },
    {
      "orgao": "TRF6_PJE",
      "status": "sucesso",
      "arquivo": "output/pdfs/12345678900/TRF6PJE_12345678900_JoaoSilva.pdf",
      "tentativas": 1
    },
    {
      "orgao": "TRT3",
      "status": "sucesso",
      "arquivo": "output/pdfs/12345678900/TRT3_12345678900_JoaoSilva.pdf",
      "tentativas": 1
    },
    {
      "orgao": "TJMG_RUPE",
      "status": "sucesso",
      "arquivo": "output/pdfs/12345678900/TJMGRUPE_12345678900_JoaoSilva.pdf",
      "tentativas": 1,
      "nota": "Solicitante: Pedro Ivo Batista Clemente"
    },
    {
      "orgao": "PGFN",
      "status": "sucesso",
      "arquivo": "output/pdfs/12345678900/PGFN_12345678900_JoaoSilva.pdf",
      "tentativas": 1
    }
  ],
  "total": 6,
  "sucessos": 6,
  "falhas": 0,
  "duracao_segundos": 142
}
```

## Veto Conditions

Rejeitar e declarar falha crítica se:
1. O CPF fornecido tiver menos de 11 dígitos numéricos após sanitização (CPF inválido).
2. O script `scraper.py` não existir ou retornar erro de importação/sintaxe (configuração quebrada).

## Quality Criteria

- [ ] JSON de resultado contém exatamente 6 entradas em `certidoes`, uma por órgão
- [ ] Cada certidão com `status: sucesso` tem um `arquivo` cujo tamanho é > 10KB
- [ ] O campo `duracao_segundos` está preenchido com o tempo real de execução
- [ ] Nenhuma exceção não tratada vazou para a resposta da API
