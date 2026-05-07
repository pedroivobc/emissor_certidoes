# Domain Framework — Automação de Certidões

## Visão Geral do Processo

A emissão de certidões para escrituras imobiliárias envolve 6 portais federais e estaduais, cada um com fluxo diferente. O processo manual leva 30-60 minutos por pessoa. O squad automatiza isso em paralelo.

## Framework de Execução

### Fase 1 — Intake e Validação

1. Receber `card_id` do ClickUp
2. Extrair campos customizados: NOME, CPF/CNPJ, TIPO DE PESSOA, DATA DE NASCIMENTO
3. Validar e normalizar (CPF/CNPJ somente dígitos, datas em AAAA-MM-DD)
4. Detectar múltiplas pessoas no card
5. Criar pasta no Google Drive

### Fase 2 — Coleta Paralela (5 portais)

Executar simultaneamente para cada pessoa:

| Portal | Tipo | Campos | Especial |
|--------|------|--------|---------|
| TST CNDT | Trabalhista nacional | CPF ou CNPJ | Emissão imediata |
| TRF6 eproc | Federal (eproc) | CPF/CNPJ | — |
| TRF6 PJE | Federal (PJE) | CPF/CNPJ | SPA, aguardar JS |
| TRT3 CEAT | Trabalhista MG | PF/PJ + CPF/CNPJ | CAPTCHA obrigatório |
| Receita Federal | Fiscal | PF: CPF+nasc / PJ: CNPJ | Fallback por validade |

### Fase 3 — TJMG (sequencial, inline)

Para cada pessoa, sequencialmente:
1. Acessar RUPE com dados do requerido + solicitante fixo (Pedro Ivo)
2. Gerar código → aguardar e-mail → extrair código → submeter
3. Resultado: negativa (PDF) ou positiva (protocolo)

### Fase 4 — Consolidação

1. Upload dos PDFs para o Google Drive (pasta criada na Fase 1)
2. Renomear com padrão `[ORGAO]_[NOME]_[DATA].pdf`
3. Anexar PDFs no card do ClickUp
4. Mudar status para "Certidões emitidas"
5. Tratar exceções: TJMG positiva → comentário + tag TJMG-PENDENTE

## Regras de Negócio

- **TJMG negativa** → PDF automático disponível → download e upload
- **TJMG positiva** → Sem PDF → registrar protocolo, comentar card, adicionar tag TJMG-PENDENTE
- **Falha de portal** → registrar comentário com diagnóstico, não bloquear os demais portais
- **Múltiplas pessoas por card** → processar cada uma independentemente, consolidar tudo no final
- **PF na Receita Federal** → obrigatório informar DATA DE NASCIMENTO

## Tratamento de Erros por Portal

| Portal | Erro Comum | Ação |
|--------|-----------|------|
| TST | CPF/CNPJ com formatação | Normalizar antes de preencher |
| TRF6 eproc | Timeout de sessão | Renavegar e tentar novamente |
| TRF6 PJE | SPA não carregou | Aguardar e tentar 1x |
| TRT3 | CAPTCHA falhou | Tentar no máximo 2x |
| TJMG | E-mail atrasou | Aguardar 2 min (4 tentativas de 30s) |
| Receita Federal | Emissão não disponível | Usar fallback (2ª via por data de validade) |
