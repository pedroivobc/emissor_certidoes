---
execution: inline
agent: certidoes-automaticas/agents/renata-resultados
inputFile: squads/certidoes-automaticas/output/certidoes-parciais.json
outputFile: squads/certidoes-automaticas/output/consolidado.json
---

# Step 05: Consolidação — Upload Drive, Atualização ClickUp e Exceções

## Context Loading

Carregue estes arquivos antes de executar:
- `squads/certidoes-automaticas/output/certidoes-parciais.json` — resultados dos 5 portais paralelos
- `squads/certidoes-automaticas/output/tjmg-result.json` — resultado do TJMG
- `squads/certidoes-automaticas/output/card-data.json` — manifesto original com drive_folder_id e card_id

## Instructions

### Process

1. **Carregar os três arquivos de input** e cruzar os dados: certidoes-parciais + tjmg-result + card-data.
2. **Executar `upload-to-drive.md`:** para cada PDF coletado com sucesso, fazer upload para `drive_folder_id` com o nome no padrão `[ORGAO]_[NOME-MAIUSCULO]_[AAAA-MM-DD].pdf`.
3. **Executar `handle-exceptions.md`:** tratar TJMG positiva (comentário + tag TJMG-PENDENTE) e cada portal com falha (comentário de diagnóstico).
4. **Executar `update-clickup.md`:** anexar PDFs no card, adicionar comentário de sucesso com links do Drive, mudar status para "Certidões emitidas".
5. **Salvar o relatório final** em `consolidado.json` com resumo completo do processo.
6. **Apresentar ao usuário** uma tabela de resultado com status de cada certidão e links para os PDFs no Drive.

## Output Format

O output MUST follow this exact structure:

```json
{
  "card_id": "string",
  "drive_folder_url": "string",
  "summary": {
    "total_persons": 0,
    "total_certidoes": 0,
    "success_count": 0,
    "failure_count": 0,
    "positive_tjmg_count": 0
  },
  "results": [
    {
      "pessoa_index": 1,
      "nome": "string",
      "certidoes": {
        "TST": {"status": "success|failure", "drive_link": "string|null"},
        "TRF6-EPROC": {"status": "...", "drive_link": "..."},
        "TRF6-PJE": {"status": "...", "drive_link": "..."},
        "TRT3": {"status": "...", "drive_link": "..."},
        "TJMG": {"status": "success|positive|failure", "drive_link": "string|null", "protocol": "string|null"},
        "RFB": {"status": "...", "drive_link": "..."}
      }
    }
  ],
  "clickup_updated": true,
  "status_changed_to": "Certidões emitidas"
}
```

## Output Example

```json
{
  "card_id": "9hz8k2p4m",
  "drive_folder_url": "https://drive.google.com/drive/folders/1Zk9Qw2e...",
  "summary": {
    "total_persons": 1,
    "total_certidoes": 6,
    "success_count": 5,
    "failure_count": 1,
    "positive_tjmg_count": 0
  },
  "results": [
    {
      "pessoa_index": 1,
      "nome": "CARLOS ALBERTO MENDES SOUZA",
      "certidoes": {
        "TST": {"status": "success", "drive_link": "https://drive.google.com/file/d/1Abc.../view"},
        "TRF6-EPROC": {"status": "success", "drive_link": "https://drive.google.com/file/d/2Bcd.../view"},
        "TRF6-PJE": {"status": "failure", "drive_link": null},
        "TRT3": {"status": "success", "drive_link": "https://drive.google.com/file/d/4Def.../view"},
        "TJMG": {"status": "success", "drive_link": "https://drive.google.com/file/d/5Efg.../view", "protocol": null},
        "RFB": {"status": "success", "drive_link": "https://drive.google.com/file/d/6Fgh.../view"}
      }
    }
  ],
  "clickup_updated": true,
  "status_changed_to": "Certidões emitidas"
}
```

## Veto Conditions

Bloquear e reportar ao usuário se:
1. card-data.json inválido ou sem card_id — não é possível atualizar o ClickUp sem o ID do card
2. Nenhum PDF foi coletado (0 successos em todos os portais) — indicar problema sistêmico

## Quality Criteria

- [ ] Todos os PDFs disponíveis enviados para o Google Drive
- [ ] Card do ClickUp atualizado com status, anexos e comentários
- [ ] Tabela de resultado apresentada ao usuário
- [ ] consolidado.json salvo com resumo completo
- [ ] TJMG positiva: tag e comentário adicionados antes do status final
