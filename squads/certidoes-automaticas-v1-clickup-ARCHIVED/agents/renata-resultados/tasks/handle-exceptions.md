---
task: "Tratar Exceções (TJMG Positiva e Falhas)"
order: 3
input: |
  - card_id: ID do card no ClickUp
  - tjmg_result: Resultado do TJMG (status, protocol, error)
  - upload_errors: Lista de portais que falharam no upload/coleta
output: |
  - exceptions_handled: Lista de exceções tratadas com ação tomada
  - tjmg_tag_added: Boolean se tag TJMG-PENDENTE foi adicionada
  - tjmg_comment_added: Boolean se comentário do protocolo foi adicionado
---

# Tratar Exceções (TJMG Positiva e Falhas)

Trata os dois casos especiais do squad: TJMG com resultado positivo (requer emissão manual) e falhas de portal que precisam de ação humana.

## Process

### Caso 1 — TJMG Positiva:

1. **Verificar** se `tjmg_result.status == "positive"`.
2. **Adicionar comentário no card** do ClickUp com o seguinte conteúdo:
   ```
   ⚠️ TJMG — Resultado POSITIVO
   Número do protocolo: [tjmg_protocol]
   CPF/CNPJ do requerente: [cpf_cnpj]
   ⚠️ Emissão manual necessária em 1-2 dias úteis.
   Acessar: https://rupe.tjmg.jus.br/ com o número do protocolo para acompanhar.
   ```
3. **Adicionar a tag "TJMG-PENDENTE"** ao card usando ClickUp MCP (`clickup_add_tag_to_task`).

### Caso 2 — Falhas de Portal:

1. **Para cada entrada em `upload_errors`** e cada portal com `status == "failure"`:
2. **Adicionar comentário no card** no formato:
   ```
   ❌ [ORGAO] — Falha na coleta
   Etapa: [etapa onde falhou]
   Motivo: [mensagem de erro]
   Ação: Tentar emitir manualmente em [URL do portal]
   ```
3. **Não mudar o status do card** para "Certidões emitidas" se houver falhas críticas que impeçam a conclusão do processo.

## Output Format

```yaml
exceptions_handled:
  - type: "tjmg_positive"
    action: "comment_added + tag_added"
    protocol: "2026/00123456"
  - type: "portal_failure"
    portal: "TRF6-EPROC"
    action: "comment_added"
tjmg_tag_added: true
tjmg_comment_added: true
```

## Output Example

```yaml
exceptions_handled:
  - type: "tjmg_positive"
    action: "comment + tag TJMG-PENDENTE adicionados"
    protocol: "2026/00456789"
    cpf_cnpj: "98765432100"
tjmg_tag_added: true
tjmg_comment_added: true
# Comentário adicionado no card:
# "⚠️ TJMG — Resultado POSITIVO\n
# Número do protocolo: 2026/00456789\n
# CPF do requerente: 98765432100\n
# ⚠️ Emissão manual necessária em 1-2 dias úteis.\n
# Acesse https://rupe.tjmg.jus.br/ com o protocolo para acompanhar."
```

## Quality Criteria

- [ ] Para TJMG positiva: comentário com protocolo e CPF/CNPJ adicionado ao card
- [ ] Para TJMG positiva: tag "TJMG-PENDENTE" adicionada ao card
- [ ] Para cada falha de portal: comentário específico com portal, etapa e URL para ação manual
- [ ] exceptions_handled lista todas as exceções tratadas

## Veto Conditions

Registrar falha se:
1. tag_add_task do ClickUp falhar após 2 tentativas (tag "TJMG-PENDENTE" é crítica)
2. Comentários não puderem ser adicionados (card sem permissão de escrita)
