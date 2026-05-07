---
task: "Ler Card do ClickUp"
order: 1
input: |
  - card_id: ID do card no ClickUp (recebido via webhook ou input do usuário)
output: |
  - card_raw: Objeto com todos os campos e valores do card
  - custom_fields: Dicionário com campos customizados mapeados por nome
---

# Ler Card do ClickUp

Busca o card do ClickUp via MCP e extrai todos os campos relevantes para o processo de emissão de certidões.

## Process

1. Receber o `card_id` do input (webhook payload ou parâmetro manual). Se não fornecido, solicitar ao usuário.
2. Chamar `clickup_get_task` com o `card_id` para obter todos os dados do card.
3. Extrair os campos customizados: NOME, CPF ou CNPJ, TIPO DE PESSOA, DATA DE NASCIMENTO. Mapear por nome do campo (case-insensitive).
4. Verificar se o card pertence à lista "Escrituras - Projeto". Se não pertencer, registrar aviso mas continuar.
5. Retornar o `card_raw` completo e o dicionário `custom_fields` normalizado.

## Output Format

```yaml
card_id: "abc123"
card_title: "João Silva e Maria Silva - Escritura Rua das Flores"
list_name: "Escrituras - Projeto"
custom_fields:
  NOME: "João Silva"
  CPF_CNPJ: "12345678909"
  TIPO_PESSOA: "PF"
  DATA_NASCIMENTO: "1980-05-15"
```

## Output Example

```yaml
card_id: "9hz8k2p4m"
card_title: "Escritura - Imóvel Rua Diamantina 45 - Belo Horizonte"
list_name: "Escrituras - Projeto"
custom_fields:
  NOME: "CARLOS ALBERTO MENDES SOUZA"
  CPF_CNPJ: "98765432100"
  TIPO_PESSOA: "PF"
  DATA_NASCIMENTO: "1975-11-30"
  STATUS_ATUAL: "Em andamento"
  RESPONSAVEL: "Pedro Ivo"
```

## Quality Criteria

- [ ] card_id está preenchido e válido
- [ ] custom_fields contém pelo menos NOME e CPF_CNPJ
- [ ] TIPO_PESSOA está preenchido com "PF" ou "PJ"
- [ ] Para PF, DATA_NASCIMENTO está presente

## Veto Conditions

Rejeitar e reportar erro se:
1. Card não encontrado no ClickUp (ID inválido ou permissão negada)
2. Campo NOME está vazio ou ausente no card
