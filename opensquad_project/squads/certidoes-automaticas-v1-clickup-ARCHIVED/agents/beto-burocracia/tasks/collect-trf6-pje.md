---
task: "Coletar Certidão TRF6 PJE"
order: 3
input: |
  - nome: Nome completo da pessoa
  - cpf_cnpj: CPF ou CNPJ (somente dígitos)
  - tipo_pessoa: "PF" ou "PJ"
  - nome_normalizado: Nome sem acentos para uso no nome do arquivo
output: |
  - trf6_pje_status: "success" | "failure"
  - trf6_pje_pdf_path: Caminho local do PDF (null se falhou)
  - trf6_pje_pdf_name: Nome do arquivo no padrão correto
  - trf6_pje_error: Mensagem de erro (null se sucesso)
---

# Coletar Certidão TRF6 PJE

Emite a certidão de ações judiciais no sistema PJE do Tribunal Regional Federal da 6ª Região. Este sistema é separado do eproc — cobre processos no sistema PJE.

## Process

1. **Navegar para** `https://sistemas.trf6.jus.br/certidao/#/` via Playwright.
2. **Aguardar carregamento completo** da SPA (Single Page Application) — pode levar 5-10 segundos.
3. **Localizar o campo de CPF/CNPJ** e preencher com `cpf_cnpj` (somente dígitos).
4. **Selecionar o tipo correto** (Pessoa Física ou Jurídica) se houver seletor.
5. **Clicar em "Consultar"** ou botão equivalente.
6. **Aguardar resultado** (até 20 segundos).
7. **Clicar em botão de download/emissão** e salvar como `TRF6-PJE_[NOME-NORMALIZADO]_[DATA].pdf`.
8. **Confirmar existência do arquivo** antes de retornar.

## Output Format

```yaml
trf6_pje_status: "success"
trf6_pje_pdf_path: "/tmp/certidoes/TRF6-PJE_joao-silva_2026-04-23.pdf"
trf6_pje_pdf_name: "TRF6-PJE_JOAO-SILVA_2026-04-23.pdf"
trf6_pje_error: null
```

## Output Example

```yaml
trf6_pje_status: "success"
trf6_pje_pdf_path: "/tmp/certidoes/TRF6-PJE_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
trf6_pje_pdf_name: "TRF6-PJE_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
trf6_pje_error: null
```

## Quality Criteria

- [ ] Aguardado carregamento completo da SPA antes de interagir
- [ ] Campo CPF/CNPJ preenchido corretamente (somente dígitos)
- [ ] PDF baixado com nome no padrão TRF6-PJE_[NOME]_[DATA].pdf
- [ ] Arquivo confirmado em disco

## Veto Conditions

Não tentar de novo se:
1. Sistema PJE retornar erro de serviço indisponível (503/504)
2. Página não carregar após 30 segundos de espera
