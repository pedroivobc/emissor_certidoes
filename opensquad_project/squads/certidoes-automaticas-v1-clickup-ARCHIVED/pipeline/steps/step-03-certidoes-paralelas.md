---
execution: subagent
agent: certidoes-automaticas/agents/beto-burocracia
inputFile: squads/certidoes-automaticas/output/card-data.json
outputFile: squads/certidoes-automaticas/output/certidoes-parciais.json
model_tier: powerful
---

# Step 03: Certidões em Paralelo (TST, TRF6 eproc, TRF6 PJE, TRT3, Receita Federal)

## Context Loading

Carregue estes arquivos antes de executar:
- `squads/certidoes-automaticas/output/card-data.json` — manifesto com dados de cada pessoa
- `squads/certidoes-automaticas/pipeline/data/domain-framework.md` — URLs e fluxos de cada portal

## Instructions

### Process

Execute as seguintes tarefas **em paralelo** para cada pessoa no manifesto. Para múltiplas pessoas, as coletas de cada portal podem ser paralelas dentro de cada pessoa.

1. **Para cada `pessoa` em `card_data.persons`**, executar as 5 tarefas de coleta em paralelo:
   - `collect-tst.md` — portal: `https://cndt-certidao.tst.jus.br/gerarCertidao.faces`
   - `collect-trf6-eproc.md` — portal: `https://certidao.trf6.jus.br/consulta`
   - `collect-trf6-pje.md` — portal: `https://sistemas.trf6.jus.br/certidao/#/`
   - `collect-trt3.md` — portal: `https://certidao.trt3.jus.br/certidao/feitosTrabalhistas/` (atenção ao fluxo de CAPTCHA)
   - `collect-receita-federal.md` — portal: `https://servicos.receitafederal.gov.br/servico/certidoes/#/home`

2. **Para cada tarefa**, registrar o resultado com: `status`, `pdf_path`, `pdf_name` e `error`.

3. **Consolidar todos os resultados** por pessoa em um array `results_per_person`.

4. **Salvar o resultado consolidado** em `certidoes-parciais.json`.

**Nota sobre TJMG:** O portal TJMG/RUPE é executado no Step 04 (inline) por requerer verificação de e-mail. Não incluir neste step.

## Output Format

O output MUST follow this exact structure:

```json
{
  "results_per_person": [
    {
      "pessoa_index": 1,
      "nome": "CARLOS ALBERTO MENDES SOUZA",
      "nome_normalizado": "carlos-alberto-mendes-souza",
      "certidoes": {
        "tst": {
          "status": "success|failure",
          "pdf_path": "string|null",
          "pdf_name": "string|null",
          "error": "string|null"
        },
        "trf6_eproc": { "status": "...", "pdf_path": "...", "pdf_name": "...", "error": "..." },
        "trf6_pje": { "status": "...", "pdf_path": "...", "pdf_name": "...", "error": "..." },
        "trt3": { "status": "...", "pdf_path": "...", "pdf_name": "...", "error": "..." },
        "receita_federal": { "status": "...", "pdf_path": "...", "pdf_name": "...", "rfb_flow_used": "direct|fallback", "error": "..." }
      }
    }
  ]
}
```

## Output Example

```json
{
  "results_per_person": [
    {
      "pessoa_index": 1,
      "nome": "CARLOS ALBERTO MENDES SOUZA",
      "nome_normalizado": "carlos-alberto-mendes-souza",
      "certidoes": {
        "tst": {
          "status": "success",
          "pdf_path": "/tmp/certidoes/TST_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
          "pdf_name": "TST_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
          "error": null
        },
        "trf6_eproc": {
          "status": "success",
          "pdf_path": "/tmp/certidoes/TRF6-EPROC_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
          "pdf_name": "TRF6-EPROC_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
          "error": null
        },
        "trf6_pje": {
          "status": "failure",
          "pdf_path": null,
          "pdf_name": null,
          "error": "Sistema PJE retornou erro 503 — serviço temporariamente indisponível"
        },
        "trt3": {
          "status": "success",
          "pdf_path": "/tmp/certidoes/TRT3_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
          "pdf_name": "TRT3_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
          "error": null
        },
        "receita_federal": {
          "status": "success",
          "pdf_path": "/tmp/certidoes/RFB_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
          "pdf_name": "RFB_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf",
          "rfb_flow_used": "direct",
          "error": null
        }
      }
    }
  ]
}
```

## Veto Conditions

Considerar o step como falha total somente se:
1. Nenhum portal retornou resultado (todos falharam sem registrar erro — indica problema sistêmico)
2. card-data.json está vazio ou sem a lista `persons`

## Quality Criteria

- [ ] Todos os 5 portais têm entrada no resultado para cada pessoa
- [ ] Falhas registram mensagem de erro específica (não apenas null)
- [ ] certidoes-parciais.json salvo com estrutura válida
- [ ] TRT3: fluxo de CAPTCHA (PF/PJ → CPF/CNPJ → captcha → Consultar) seguido corretamente
