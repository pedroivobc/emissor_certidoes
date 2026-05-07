---
task: "Coletar Certidão TJMG/RUPE"
order: 5
input: |
  - cpf_cnpj: CPF ou CNPJ da pessoa requerida (somente dígitos)
  - tipo_pessoa: "PF" ou "PJ"
  - nome_normalizado: Nome sem acentos para uso no nome do arquivo
output: |
  - tjmg_status: "success" | "positive" | "failure"
  - tjmg_pdf_path: Caminho local do PDF (null se positiva ou falhou)
  - tjmg_pdf_name: Nome do arquivo (null se positiva)
  - tjmg_protocol: Número do protocolo (para resultado positivo)
  - tjmg_error: Mensagem de erro (null se sucesso ou positiva)
---

# Coletar Certidão TJMG/RUPE

Solicita a certidão judicial no Sistema RUPE do Tribunal de Justiça de Minas Gerais. Usa dados fixos do solicitante (Pedro Ivo Batista Clemente) e requer código de verificação enviado por e-mail para contato@clementeassessoria.com.

**Nota:** Este agente executa em modo INLINE porque precisa acessar o Gmail MCP para ler o código de verificação.

## Dados Fixos do Solicitante

- **Nome:** PEDRO IVO BATISTA CLEMENTE
- **CPF:** 11773105620
- **E-mail:** contato@clementeassessoria.com

## Process

1. **Navegar para** `https://rupe.tjmg.jus.br/rupe/justica/publico/certidoes/criarSolicitacaoCertidao.rupe?solicitacaoPublica=true` via Playwright.
2. **Preencher dados do REQUERIDO** (a pessoa do card do ClickUp):
   - CPF/CNPJ: `cpf_cnpj` (somente dígitos)
   - Tipo de pessoa: `tipo_pessoa`
3. **Preencher dados do SOLICITANTE** (sempre o mesmo):
   - Nome: PEDRO IVO BATISTA CLEMENTE
   - CPF: 11773105620
   - E-mail: contato@clementeassessoria.com
4. **Clicar em "Gerar código"** e aguardar a tela de inserção do código.
5. **Ler o e-mail de verificação** via Gmail MCP:
   - Buscar o e-mail mais recente de "rupe@tjmg.jus.br" ou assunto "código de verificação" em contato@clementeassessoria.com
   - Aguardar até 2 minutos (tentar a cada 30 segundos, até 4 tentativas)
   - Extrair o código numérico do corpo do e-mail
6. **Preencher o código de verificação** no formulário e clicar em "Confirmar" ou "Salvar".
7. **Verificar resultado:**
   - Se a página indicar "certidão negativa" ou emitir PDF: download e salvar como `TJMG_[NOME-NORMALIZADO]_[DATA].pdf`
   - Se a página indicar "resultado positivo" ou listar processos: capturar o número de protocolo e registrar `tjmg_status: "positive"`
8. **Confirmar existência do arquivo** (se negativa) ou registrar protocolo (se positiva).

## Output Format

```yaml
# Resultado negativa (PDF emitido):
tjmg_status: "success"
tjmg_pdf_path: "/tmp/certidoes/TJMG_joao-silva_2026-04-23.pdf"
tjmg_pdf_name: "TJMG_JOAO-SILVA_2026-04-23.pdf"
tjmg_protocol: null
tjmg_error: null

# Resultado positiva (sem PDF):
tjmg_status: "positive"
tjmg_pdf_path: null
tjmg_pdf_name: null
tjmg_protocol: "2026/00123456"
tjmg_error: null
```

## Output Example

```yaml
tjmg_status: "success"
tjmg_pdf_path: "/tmp/certidoes/TJMG_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
tjmg_pdf_name: "TJMG_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
tjmg_protocol: null
tjmg_error: null
```

## Quality Criteria

- [ ] Dados do solicitante fixo preenchidos corretamente (Pedro Ivo / CPF 11773105620)
- [ ] Dados do requerido (pessoa do card) preenchidos corretamente
- [ ] Código de verificação lido via Gmail MCP e preenchido no formulário
- [ ] Resultado verificado: "success" para PDF, "positive" para protocolo
- [ ] Para negativa: PDF salvo no padrão correto
- [ ] Para positiva: protocolo capturado da página

## Veto Conditions

Registrar falha se:
1. E-mail com código de verificação não chegar após 4 tentativas (2 minutos)
2. Formulário retornar erro de validação dos dados do requerido
