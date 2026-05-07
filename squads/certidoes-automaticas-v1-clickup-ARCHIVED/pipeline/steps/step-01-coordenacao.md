---
execution: inline
agent: certidoes-automaticas/agents/carlos-coordenador
outputFile: squads/certidoes-automaticas/output/card-data.json
---

# Step 01: Coordenação — Leitura e Validação do Card

## Context Loading

Carregue estes arquivos antes de executar:
- `_opensquad/_memory/company.md` — contexto da empresa Clemente Assessoria
- `squads/certidoes-automaticas/pipeline/data/domain-framework.md` — framework de automação de certidões

## Instructions

### Process

1. **Receber o `card_id`** do input do usuário ou do payload do webhook do ClickUp. Se não fornecido, solicitar ao usuário que informe o ID ou link do card.
2. **Executar a tarefa `read-clickup-card.md`:** buscar o card via ClickUp MCP e extrair todos os campos customizados (NOME, CPF/CNPJ, TIPO DE PESSOA, DATA DE NASCIMENTO).
3. **Executar a tarefa `validate-fields.md`:** validar campos obrigatórios, normalizar CPF/CNPJ (somente dígitos) e detectar múltiplas pessoas. Se validação falhar, interromper e reportar ao usuário.
4. **Executar a tarefa `create-drive-folder.md`:** criar pasta no Google Drive com o nome `[nome-normalizado]_[card-id]` e capturar o `drive_folder_id`.
5. **Montar o manifesto completo** (`card-data.json`) com: card_id, drive_folder_id, drive_folder_name, drive_folder_url e lista de pessoas com todos os campos normalizados.
6. **Salvar o manifesto** em `squads/certidoes-automaticas/output/card-data.json`.

## Output Format

O output MUST follow this exact structure:

```json
{
  "card_id": "string",
  "card_title": "string",
  "drive_folder_id": "string",
  "drive_folder_name": "string",
  "drive_folder_url": "string",
  "persons": [
    {
      "pessoa_index": 1,
      "nome": "NOME COMPLETO EM MAIUSCULAS",
      "nome_normalizado": "nome-sem-acento",
      "cpf_cnpj": "somentedigitos",
      "tipo_pessoa": "PF",
      "data_nascimento": "AAAA-MM-DD"
    }
  ]
}
```

## Output Example

```json
{
  "card_id": "9hz8k2p4m",
  "card_title": "Escritura - Imóvel Rua Diamantina 45 - Carlos e Ana",
  "drive_folder_id": "1Zk9Qw2eTyUiOpAsD3fGhJ4kL5mNbV6cX",
  "drive_folder_name": "carlos-alberto-mendes-souza_9hz8k2p4m",
  "drive_folder_url": "https://drive.google.com/drive/folders/1Zk9Qw2eTyUiOpAsD3fGhJ4kL5mNbV6cX",
  "persons": [
    {
      "pessoa_index": 1,
      "nome": "CARLOS ALBERTO MENDES SOUZA",
      "nome_normalizado": "carlos-alberto-mendes-souza",
      "cpf_cnpj": "98765432100",
      "tipo_pessoa": "PF",
      "data_nascimento": "1975-11-30"
    },
    {
      "pessoa_index": 2,
      "nome": "ANA BEATRIZ MENDES SOUZA",
      "nome_normalizado": "ana-beatriz-mendes-souza",
      "cpf_cnpj": "12345678900",
      "tipo_pessoa": "PF",
      "data_nascimento": "1980-03-22"
    }
  ]
}
```

## Veto Conditions

Bloquear pipeline e reportar ao usuário se:
1. Campos obrigatórios (NOME, CPF/CNPJ, TIPO DE PESSOA) ausentes no card
2. Pasta no Google Drive não pôde ser criada (falha de API ou permissão negada)

## Quality Criteria

- [ ] card-data.json gerado com todos os campos obrigatórios
- [ ] Pelo menos uma pessoa na lista `persons`
- [ ] drive_folder_id e drive_folder_url preenchidos e válidos
- [ ] CPF/CNPJ normalizado (somente dígitos) para cada pessoa
