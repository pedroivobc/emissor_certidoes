---
task: "Coletar Certidão Receita Federal"
order: 6
input: |
  - nome: Nome completo da pessoa
  - cpf_cnpj: CPF ou CNPJ (somente dígitos)
  - tipo_pessoa: "PF" ou "PJ"
  - data_nascimento: Data de nascimento no formato AAAA-MM-DD (obrigatório para PF)
  - nome_normalizado: Nome sem acentos para uso no nome do arquivo
output: |
  - rfb_status: "success" | "failure"
  - rfb_pdf_path: Caminho local do PDF (null se falhou)
  - rfb_pdf_name: Nome do arquivo no padrão correto
  - rfb_flow_used: "direct" | "fallback" (qual fluxo foi usado)
  - rfb_error: Mensagem de erro (null se sucesso)
---

# Coletar Certidão Receita Federal

Emite a certidão de regularidade fiscal na Receita Federal do Brasil. Fluxo diferente para Pessoa Física (CPF + data de nascimento) e Pessoa Jurídica (CNPJ). Se a emissão imediata falhar, usa o fluxo de fallback por data de validade para baixar uma 2ª via.

## Process

### Fluxo Principal (PF — Pessoa Física):

1. **Navegar para** `https://servicos.receitafederal.gov.br/servico/certidoes/#/home` via Playwright.
2. **Selecionar "Pessoa Física"** na opção de tipo.
3. **Preencher CPF** (somente dígitos) e **data de nascimento** no formato DD/MM/AAAA.
4. **Clicar em "Emitir"** e aguardar resultado (até 20 segundos).
5. Se PDF gerado: fazer download, salvar como `RFB_[NOME-NORMALIZADO]_[DATA].pdf`.

### Fluxo Principal (PJ — Pessoa Jurídica):

1. **Navegar para** `https://servicos.receitafederal.gov.br/servico/certidoes/#/home`.
2. **Selecionar "Pessoa Jurídica"** na opção de tipo.
3. **Preencher CNPJ** (somente dígitos).
4. **Clicar em "Emitir"** e aguardar resultado.
5. Se PDF gerado: fazer download, salvar como `RFB_[NOME-NORMALIZADO]_[DATA].pdf`.

### Fluxo Fallback (quando emissão imediata falha):

1. Procurar opção **"Consultar Certidão"** na página ou menu.
2. Navegar para a consulta, inserir CPF/CNPJ.
3. Localizar a certidão mais recente pela **"Data de Validade"** (mais futura = mais recente).
4. Clicar em "Download" ou "2ª Via" para baixar o PDF.
5. Salvar como `RFB_[NOME-NORMALIZADO]_[DATA].pdf` com `rfb_flow_used: "fallback"`.

## Output Format

```yaml
rfb_status: "success"
rfb_pdf_path: "/tmp/certidoes/RFB_joao-silva_2026-04-23.pdf"
rfb_pdf_name: "RFB_JOAO-SILVA_2026-04-23.pdf"
rfb_flow_used: "direct"
rfb_error: null
```

## Output Example

```yaml
rfb_status: "success"
rfb_pdf_path: "/tmp/certidoes/RFB_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
rfb_pdf_name: "RFB_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
rfb_flow_used: "fallback"
rfb_error: null
```

## Quality Criteria

- [ ] Tipo de pessoa selecionado corretamente no portal (PF ou PJ)
- [ ] Para PF: data de nascimento preenchida no formato aceito pelo portal
- [ ] PDF baixado com nome no padrão RFB_[NOME]_[DATA].pdf
- [ ] rfb_flow_used registrado para rastreabilidade ("direct" ou "fallback")
- [ ] Arquivo confirmado em disco

## Veto Conditions

Registrar falha se:
1. Fluxo principal E fallback falharem (certidão não localizável por nenhum meio)
2. Para PF: data de nascimento ausente no input (campo obrigatório para este portal)
