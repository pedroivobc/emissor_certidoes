# Quality Criteria — Certidões Automáticas

## Critérios de Qualidade por Fase

### Fase 1 — Intake e Validação

- [ ] Card lido com sucesso via ClickUp MCP
- [ ] NOME presente e não vazio
- [ ] CPF/CNPJ normalizado (somente dígitos, 11 ou 14 caracteres)
- [ ] TIPO DE PESSOA definido como "PF" ou "PJ"
- [ ] Para PF: DATA DE NASCIMENTO presente em formato válido
- [ ] Múltiplas pessoas detectadas e separadas individualmente
- [ ] Pasta no Google Drive criada com nome no padrão correto
- [ ] Manifesto card-data.json salvo com todos os campos

### Fase 2 — Coleta Paralela

- [ ] Todos os 5 portais têm entrada no resultado (success, failure ou indisponível)
- [ ] PDFs coletados nomeados no padrão [ORGAO]_[NOME]_[DATA].pdf
- [ ] Falhas registram mensagem de erro específica
- [ ] TRT3: fluxo de CAPTCHA executado (não skipar)
- [ ] Receita Federal: rfb_flow_used registrado (direct ou fallback)

### Fase 3 — TJMG

- [ ] Dados fixos do solicitante (Pedro Ivo) preenchidos corretamente
- [ ] Código de verificação obtido via Gmail MCP
- [ ] Resultado classificado corretamente: negativa (PDF) ou positiva (protocolo)
- [ ] Para negativa: PDF salvo; para positiva: protocolo registrado

### Fase 4 — Consolidação

- [ ] Todos os PDFs disponíveis enviados para o Google Drive
- [ ] Cada PDF nomeado corretamente no Drive
- [ ] PDFs anexados no card do ClickUp
- [ ] Status do card alterado para "Certidões emitidas"
- [ ] Comentário de sucesso com links do Drive adicionado
- [ ] Cada falha tem comentário de diagnóstico no card
- [ ] TJMG positiva: comentário de protocolo + tag TJMG-PENDENTE adicionados

## Thresholds de Aceitação

| Métrica | Threshold |
|---------|-----------|
| Taxa de coleta bem-sucedida | ≥ 5/6 portais |
| Tempo máximo por portal | 60 segundos |
| Tempo máximo TJMG (com e-mail) | 3 minutos |
| Tamanho mínimo do PDF | > 10 KB |
| Nomenclatura correta dos arquivos | 100% |

## Critérios de Falha Crítica

Um run é considerado falha crítica se:
- card_id inválido ou card não encontrado
- Pasta do Drive não foi criada
- Card do ClickUp não foi atualizado ao final
- Todos os 6 portais falharam (0 certidões coletadas)
