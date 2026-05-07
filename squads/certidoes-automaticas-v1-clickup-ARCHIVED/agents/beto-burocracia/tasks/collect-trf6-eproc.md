---
task: "Coletar Certidão TRF6 eproc"
order: 2
input: |
  - nome: Nome completo da pessoa
  - cpf_cnpj: CPF ou CNPJ (somente dígitos)
  - tipo_pessoa: "PF" ou "PJ"
  - nome_normalizado: Nome sem acentos para uso no nome do arquivo
output: |
  - trf6_eproc_status: "success" | "failure"
  - trf6_eproc_pdf_path: Caminho local do PDF (null se falhou)
  - trf6_eproc_pdf_name: Nome do arquivo no padrão correto
  - trf6_eproc_error: Mensagem de erro (null se sucesso)
---

# Coletar Certidão TRF6 eproc

Emite a certidão de ações judiciais no sistema eproc do Tribunal Regional Federal da 6ª Região.

## Process

1. **Navegar para** `https://certidao.trf6.jus.br/consulta` via Playwright.
2. **Localizar o campo de CPF/CNPJ** e preencher com `cpf_cnpj` (somente dígitos).
3. **Selecionar o tipo correto** (PF ou PJ) se houver seletor na página.
4. **Clicar em "Consultar"** ou botão equivalente.
5. **Aguardar resultado** (até 20 segundos). Verificar presença de botão de emissão/download.
6. **Clicar em "Emitir Certidão"** ou "Download PDF" e salvar como `TRF6-EPROC_[NOME-NORMALIZADO]_[DATA].pdf`.
7. **Confirmar existência do arquivo** antes de retornar.

## Output Format

```yaml
trf6_eproc_status: "success"
trf6_eproc_pdf_path: "/tmp/certidoes/TRF6-EPROC_joao-silva_2026-04-23.pdf"
trf6_eproc_pdf_name: "TRF6-EPROC_JOAO-SILVA_2026-04-23.pdf"
trf6_eproc_error: null
```

## Output Example

```yaml
trf6_eproc_status: "success"
trf6_eproc_pdf_path: "/tmp/certidoes/TRF6-EPROC_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
trf6_eproc_pdf_name: "TRF6-EPROC_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
trf6_eproc_error: null
```

## Quality Criteria

- [ ] Navegação chegou à página de resultado sem redirecionamento inesperado
- [ ] PDF baixado com nome no padrão TRF6-EPROC_[NOME]_[DATA].pdf
- [ ] Tamanho do arquivo > 0 bytes confirmado

## Veto Conditions

Não tentar de novo se:
1. Sistema retornar erro de autenticação ou CAPTCHA impossível de resolver
2. Página travar em loading por mais de 30 segundos
