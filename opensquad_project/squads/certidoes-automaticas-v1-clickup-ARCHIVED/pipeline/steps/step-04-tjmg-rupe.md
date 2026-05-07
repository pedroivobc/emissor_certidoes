---
execution: inline
agent: certidoes-automaticas/agents/beto-burocracia
inputFile: squads/certidoes-automaticas/output/card-data.json
outputFile: squads/certidoes-automaticas/output/tjmg-result.json
---

# Step 04: TJMG/RUPE — Certidão com Verificação de E-mail

## Context Loading

Carregue estes arquivos antes de executar:
- `squads/certidoes-automaticas/output/card-data.json` — manifesto com dados de cada pessoa
- `squads/certidoes-automaticas/pipeline/data/domain-framework.md` — dados fixos do solicitante TJMG

## Instructions

### Process

Este step executa **em modo inline** porque requer acesso ao Gmail MCP para recuperar o código de verificação enviado por e-mail durante o processo no portal TJMG/RUPE.

1. **Para cada `pessoa` em `card_data.persons`**, executar `collect-tjmg-rupe.md`:
   - Navegar para `https://rupe.tjmg.jus.br/rupe/justica/publico/certidoes/criarSolicitacaoCertidao.rupe?solicitacaoPublica=true`
   - Preencher o **requerido** com os dados da pessoa (CPF/CNPJ, tipo de pessoa)
   - Preencher o **solicitante** com dados fixos: Pedro Ivo Batista Clemente / CPF 11773105620 / contato@clementeassessoria.com
   - Clicar em "Gerar código"
   - Usar Gmail MCP para buscar e-mail de verificação em contato@clementeassessoria.com
   - Aguardar até 2 minutos (4 tentativas de 30s) pelo código
   - Preencher o código e submeter o formulário
   - Capturar resultado: negativa (PDF) ou positiva (protocolo)

2. **Se múltiplas pessoas** no card: processar uma de cada vez (sequencial, não paralelo — cada formulário requer um código de e-mail separado).

3. **Salvar resultado** em `tjmg-result.json`.

## Output Format

O output MUST follow this exact structure:

```json
{
  "tjmg_results": [
    {
      "pessoa_index": 1,
      "nome": "string",
      "nome_normalizado": "string",
      "tjmg_status": "success|positive|failure",
      "tjmg_pdf_path": "string|null",
      "tjmg_pdf_name": "string|null",
      "tjmg_protocol": "string|null",
      "tjmg_error": "string|null"
    }
  ]
}
```

## Output Example

```json
{
  "tjmg_results": [
    {
      "pessoa_index": 1,
      "nome": "CARLOS ALBERTO MENDES SOUZA",
      "nome_normalizado": "carlos-alberto-mendes-souza",
      "tjmg_status": "success",
      "tjmg_pdf_path": "/tmp/certidoes/TJMG_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
      "tjmg_pdf_name": "TJMG_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
      "tjmg_protocol": null,
      "tjmg_error": null
    },
    {
      "pessoa_index": 2,
      "nome": "ANA BEATRIZ MENDES SOUZA",
      "nome_normalizado": "ana-beatriz-mendes-souza",
      "tjmg_status": "positive",
      "tjmg_pdf_path": null,
      "tjmg_pdf_name": null,
      "tjmg_protocol": "2026/00456789",
      "tjmg_error": null
    }
  ]
}
```

## Veto Conditions

Registrar falha para a pessoa afetada se:
1. Código de verificação por e-mail não chegar após 4 tentativas (2 minutos total)
2. Formulário retornar erro de validação dos dados do requerente

## Quality Criteria

- [ ] Dados do solicitante fixo preenchidos corretamente para cada tentativa
- [ ] Gmail MCP usado para ler o código de verificação
- [ ] Para resultado negativo: PDF salvo no padrão correto
- [ ] Para resultado positivo: protocolo capturado e registrado no resultado
- [ ] tjmg-result.json salvo com estrutura válida
