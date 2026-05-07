---
task: "Validar Campos do Card"
order: 2
input: |
  - custom_fields: Dicionário com campos customizados do card
  - card_id: ID do card para referência
output: |
  - validation_result: Objeto com status (valid/invalid) e lista de erros
  - persons: Lista de pessoas com dados normalizados (suporta múltiplas por card)
---

# Validar Campos do Card

Valida todos os campos obrigatórios do card e normaliza os dados para uso nos portais governamentais. Detecta múltiplas pessoas no mesmo card.

## Process

1. **Verificar campos obrigatórios para TODOS os tipos de pessoa:**
   - NOME: deve ser string não vazia
   - CPF ou CNPJ: deve conter apenas dígitos após normalização
   - TIPO DE PESSOA: deve ser "PF" ou "PJ" (case-insensitive)

2. **Para Pessoa Física (PF), verificar campos adicionais:**
   - DATA DE NASCIMENTO: obrigatória para a Receita Federal
   - Formato aceito: DD/MM/AAAA ou AAAA-MM-DD

3. **Normalizar CPF/CNPJ:** remover pontos, hífens, barras e espaços. Verificar se CPF tem 11 dígitos ou CNPJ tem 14 dígitos.

4. **Detectar múltiplas pessoas:** procurar por campos com sufixo numérico (ex: NOME_2, CPF_2) ou campos separados por delimitador no mesmo campo. Para cada pessoa adicional, criar entrada separada na lista `persons`.

5. **Retornar manifesto de pessoas** com dados normalizados prontos para os agentes coletores.

## Output Format

```yaml
validation_result:
  status: "valid" | "invalid"
  errors:
    - campo: "NOME"
      mensagem: "Campo obrigatório ausente"
persons:
  - pessoa_index: 1
    nome: "NOME COMPLETO EM MAIUSCULAS"
    nome_normalizado: "nome-completo-sem-acento"
    cpf_cnpj: "somente_digitos"
    tipo_pessoa: "PF" | "PJ"
    data_nascimento: "AAAA-MM-DD"  # apenas para PF
```

## Output Example

```yaml
validation_result:
  status: "valid"
  errors: []
persons:
  - pessoa_index: 1
    nome: "CARLOS ALBERTO MENDES SOUZA"
    nome_normalizado: "carlos-alberto-mendes-souza"
    cpf_cnpj: "98765432100"
    tipo_pessoa: "PF"
    data_nascimento: "1975-11-30"
  - pessoa_index: 2
    nome: "ANA BEATRIZ MENDES SOUZA"
    nome_normalizado: "ana-beatriz-mendes-souza"
    cpf_cnpj: "12345678900"
    tipo_pessoa: "PF"
    data_nascimento: "1980-03-22"
```

## Quality Criteria

- [ ] Todos os campos obrigatórios validados e presentes
- [ ] CPF/CNPJ normalizado (somente dígitos) com contagem correta (11 ou 14)
- [ ] Para PF, data de nascimento em formato AAAA-MM-DD
- [ ] nome_normalizado sem acentos, espaços substituídos por hífens, em minúsculas
- [ ] Múltiplas pessoas detectadas e separadas em entradas individuais

## Veto Conditions

Bloquear pipeline se:
1. NOME, CPF/CNPJ ou TIPO DE PESSOA estão ausentes (campos mínimos obrigatórios)
2. CPF não tem 11 dígitos ou CNPJ não tem 14 dígitos após normalização
