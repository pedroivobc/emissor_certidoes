---
task: "Coletar Certidão TST (CNDT)"
order: 1
input: |
  - nome: Nome completo da pessoa
  - cpf_cnpj: CPF ou CNPJ (somente dígitos)
  - tipo_pessoa: "PF" ou "PJ"
  - nome_normalizado: Nome sem acentos para uso no nome do arquivo
output: |
  - tst_status: "success" | "failure" | "positive"
  - tst_pdf_path: Caminho local do PDF baixado (null se falhou)
  - tst_pdf_name: Nome do arquivo no padrão correto
  - tst_error: Mensagem de erro (null se sucesso)
---

# Coletar Certidão TST (CNDT)

Emite a Certidão Negativa de Débitos Trabalhistas (CNDT) no portal do Tribunal Superior do Trabalho.

## Process

1. **Navegar para** `https://cndt-certidao.tst.jus.br/gerarCertidao.faces` via Playwright.
2. **Localizar o campo de CPF/CNPJ** e preencher com `cpf_cnpj` (somente dígitos).
3. **Clicar em "Pesquisar"** ou botão equivalente de submissão do formulário.
4. **Aguardar o resultado** (até 15 segundos). Verificar se:
   - Certidão negativa foi gerada: localizar botão de download do PDF
   - Há mensagem de erro ou indisponibilidade
5. **Clicar em "Download" ou "Emitir PDF"** e salvar o arquivo com o nome: `TST_[NOME-NORMALIZADO]_[DATA].pdf`.
6. **Confirmar que o arquivo existe** no caminho de download antes de retornar.

## Output Format

```yaml
tst_status: "success"
tst_pdf_path: "/tmp/certidoes/TST_joao-silva_2026-04-23.pdf"
tst_pdf_name: "TST_JOAO-SILVA_2026-04-23.pdf"
tst_error: null
```

## Output Example

```yaml
tst_status: "success"
tst_pdf_path: "/tmp/certidoes/TST_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
tst_pdf_name: "TST_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
tst_error: null
```

## Quality Criteria

- [ ] PDF baixado e confirmado no caminho especificado
- [ ] Nome do arquivo segue o padrão TST_[NOME-MAIUSCULO]_[AAAA-MM-DD].pdf
- [ ] Status retornado corresponde ao resultado real da emissão
- [ ] Em caso de falha, mensagem de erro específica registrada

## Veto Conditions

Não tentar de novo automaticamente se:
1. Portal retornar mensagem de "sistema em manutenção" ou "fora do ar" — registrar falha e continuar
2. CPF/CNPJ inválido confirmado pelo portal — registrar falha com motivo claro
