---
task: "Criar Pasta no Google Drive"
order: 3
input: |
  - persons: Lista de pessoas validadas
  - card_id: ID do card no ClickUp
output: |
  - drive_folder_id: ID da pasta criada no Google Drive
  - drive_folder_name: Nome exato da pasta criada
  - drive_folder_url: URL de acesso à pasta
---

# Criar Pasta no Google Drive

Cria a pasta de destino no Google Drive onde todos os PDFs das certidões serão armazenados. O nome da pasta é derivado do nome da primeira pessoa no card e do ID do card.

## Process

1. **Montar nome da pasta:** usar o `nome_normalizado` da primeira pessoa + `_` + `card_id`. Ex: `carlos-alberto-mendes-souza_9hz8k2p4m`.
2. **Verificar se pasta já existe** com esse nome para evitar duplicatas. Se existir, usar a existente e logar aviso.
3. **Criar pasta no Google Drive** via MCP na localização padrão (Drive raiz ou pasta "Certidões Clemente Assessoria" se existir).
4. **Capturar o ID e URL da pasta criada** para incluir no manifesto de execução.
5. **Retornar o manifesto completo** com dados das pessoas + informações da pasta.

## Output Format

```yaml
drive_folder_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
drive_folder_name: "carlos-alberto-mendes-souza_9hz8k2p4m"
drive_folder_url: "https://drive.google.com/drive/folders/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
manifest:
  card_id: "9hz8k2p4m"
  drive_folder_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
  drive_folder_name: "carlos-alberto-mendes-souza_9hz8k2p4m"
  persons:
    - pessoa_index: 1
      nome: "CARLOS ALBERTO MENDES SOUZA"
      nome_normalizado: "carlos-alberto-mendes-souza"
      cpf_cnpj: "98765432100"
      tipo_pessoa: "PF"
      data_nascimento: "1975-11-30"
```

## Output Example

```yaml
drive_folder_id: "1Zk9Qw2eTyUiOpAsD3fGhJ4kL5mNbV6cX"
drive_folder_name: "ana-beatriz-mendes-souza_7px3r9qn2"
drive_folder_url: "https://drive.google.com/drive/folders/1Zk9Qw2eTyUiOpAsD3fGhJ4kL5mNbV6cX"
manifest:
  card_id: "7px3r9qn2"
  drive_folder_id: "1Zk9Qw2eTyUiOpAsD3fGhJ4kL5mNbV6cX"
  drive_folder_name: "ana-beatriz-mendes-souza_7px3r9qn2"
  persons:
    - pessoa_index: 1
      nome: "ANA BEATRIZ MENDES SOUZA"
      nome_normalizado: "ana-beatriz-mendes-souza"
      cpf_cnpj: "12345678900"
      tipo_pessoa: "PF"
      data_nascimento: "1980-03-22"
```

## Quality Criteria

- [ ] Pasta criada no Google Drive com nome no padrão [nome-normalizado]_[card-id]
- [ ] drive_folder_id capturado e incluído no manifesto
- [ ] drive_folder_url capturado e válido
- [ ] Manifesto inclui todos os campos necessários para os agentes coletores

## Veto Conditions

Bloquear pipeline se:
1. Falha na criação da pasta no Google Drive (erro de API ou permissão)
2. drive_folder_id retornado está vazio ou nulo
