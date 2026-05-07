---
task: "Coletar Certidão TRT3 (CEAT)"
order: 4
input: |
  - nome: Nome completo da pessoa
  - cpf_cnpj: CPF ou CNPJ (somente dígitos)
  - tipo_pessoa: "PF" ou "PJ"
  - nome_normalizado: Nome sem acentos para uso no nome do arquivo
output: |
  - trt3_status: "success" | "failure"
  - trt3_pdf_path: Caminho local do PDF (null se falhou)
  - trt3_pdf_name: Nome do arquivo no padrão correto
  - trt3_error: Mensagem de erro (null se sucesso)
---

# Coletar Certidão TRT3 (CEAT)

Emite a Certidão Eletrônica de Ações Trabalhistas (CEAT) no portal do Tribunal Regional do Trabalho da 3ª Região (Minas Gerais). Este portal usa CAPTCHA e requer navegação específica por tipo de pessoa.

## Process

1. **Navegar para** `https://certidao.trt3.jus.br/certidao/feitosTrabalhistas/` via Playwright.
2. **Selecionar o tipo de pessoa:** clicar em "Pessoa Física" ou "Pessoa Jurídica" conforme `tipo_pessoa`.
3. **Preencher o campo CPF ou CNPJ** com `cpf_cnpj` (somente dígitos).
4. **Resolver o CAPTCHA:** usar `browser_snapshot` para capturar a imagem do CAPTCHA e `browser_evaluate` ou leitura visual para identificar o texto. Preencher no campo indicado.
5. **Clicar em "Consultar"** e aguardar resultado (até 20 segundos).
6. **Verificar o resultado:** se certidão disponível, clicar em "Emitir" ou "Download PDF".
7. **Salvar como** `TRT3_[NOME-NORMALIZADO]_[DATA].pdf` e confirmar existência do arquivo.

## Output Format

```yaml
trt3_status: "success"
trt3_pdf_path: "/tmp/certidoes/TRT3_joao-silva_2026-04-23.pdf"
trt3_pdf_name: "TRT3_JOAO-SILVA_2026-04-23.pdf"
trt3_error: null
```

## Output Example

```yaml
trt3_status: "success"
trt3_pdf_path: "/tmp/certidoes/TRT3_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
trt3_pdf_name: "TRT3_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
trt3_error: null
```

## Quality Criteria

- [ ] Tipo de pessoa selecionado corretamente antes de preencher CPF/CNPJ
- [ ] CAPTCHA resolvido com sucesso
- [ ] PDF baixado com nome no padrão TRT3_[NOME]_[DATA].pdf
- [ ] Arquivo confirmado em disco após download

## Veto Conditions

Registrar falha e não tentar mais de 2 vezes se:
1. CAPTCHA não for resolúvel após 2 tentativas
2. Sistema retornar mensagem de indisponibilidade
