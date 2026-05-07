---
task: "Atualizar Card no ClickUp"
order: 2
input: |
  - card_id: ID do card no ClickUp
  - uploaded_files: Lista de arquivos com drive_link (da tarefa upload-to-drive)
  - upload_errors: Lista de falhas de upload
  - certidoes_results: Resultados completos de cada portal (status, error)
  - tjmg_result: Resultado específico do TJMG (status, protocol)
output: |
  - clickup_update_status: "success" | "partial" | "failure"
  - attachments_added: Quantidade de anexos adicionados
  - status_changed: Boolean se o status foi alterado
  - comments_added: Quantidade de comentários adicionados
---

# Atualizar Card no ClickUp

Anexa os PDFs coletados no card do ClickUp, atualiza o status para "Certidões emitidas" e adiciona comentários de diagnóstico para falhas e TJMG positiva.

## Process

1. **Verificar se há PDFs para anexar:** se `uploaded_files` não estiver vazio, anexar cada arquivo usando o `drive_link` como referência ou fazer upload direto via ClickUp MCP.
2. **Adicionar comentário de sucesso** listando todas as certidões emitidas com links do Drive.
3. **Para cada portal com falha (`upload_errors` ou `certidoes_results` com status "failure"):**
   - Adicionar comentário individual descrevendo: qual portal falhou, em qual etapa, e qual a mensagem de erro.
   - Não bloquear o processo por causa de falhas parciais.
4. **Para TJMG positiva** (`tjmg_result.status == "positive"`): executar `handle-exceptions.md` para tratamento específico.
5. **Mudar o status do card** para "Certidões emitidas" somente após todos os comentários e anexos estarem adicionados.
6. **Retornar resumo** com contagens de anexos, status atualizado e comentários adicionados.

## Output Format

```yaml
clickup_update_status: "success"
attachments_added: 5
status_changed: true
comments_added: 1
```

## Output Example

```yaml
clickup_update_status: "partial"
attachments_added: 4
status_changed: true
comments_added: 2
# Comentário exemplo adicionado ao card:
# "✅ Certidões emitidas (4/6):\n
# • TST: https://drive.google.com/.../TST_CARLOS...pdf\n
# • TRF6 eproc: https://drive.google.com/.../TRF6-EPROC...\n
# • TRF6 PJE: https://drive.google.com/.../TRF6-PJE...\n
# • TRT3: https://drive.google.com/.../TRT3...\n
#\n
# ❌ TRF6 eproc: Sistema retornou timeout na etapa de download. Tentar novamente manualmente.\n
# ⚠️ TJMG: Resultado POSITIVO — protocolo 2026/00123456. Emissão manual necessária em 1-2 dias úteis."
```

## Quality Criteria

- [ ] Todos os PDFs disponíveis anexados ao card do ClickUp
- [ ] Status do card alterado para "Certidões emitidas"
- [ ] Comentário de sucesso lista certidões com links do Drive
- [ ] Cada falha tem comentário específico com diagnóstico
- [ ] Atualização feita somente após uploads confirmados

## Veto Conditions

Bloquear atualização de status se:
1. card_id inválido ou card não encontrado no ClickUp
2. Nenhuma operação de atualização completou (0 anexos, 0 comentários, status não mudou)
