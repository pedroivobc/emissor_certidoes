---
task: "Upload PDFs para Google Drive"
order: 1
input: |
  - drive_folder_id: ID da pasta no Google Drive (criada por Carlos)
  - drive_folder_name: Nome da pasta no Google Drive
  - certidoes: Lista de objetos com pdf_path e pdf_name de cada certidão coletada
  - nome_normalizado: Nome da pessoa sem acentos
output: |
  - uploaded_files: Lista de arquivos enviados com drive_file_id e drive_link
  - upload_errors: Lista de arquivos que falharam no upload
---

# Upload PDFs para Google Drive

Renomeia e sobe todos os PDFs coletados para a pasta correta no Google Drive, usando o padrão de nomenclatura definido no squad.

## Process

1. **Carregar os dados de input:** lista de certidões com `pdf_path` (caminho local) e `pdf_name` (nome desejado no padrão [ORGAO]_[NOME-MAIUSCULO]_[DATA].pdf).
2. **Para cada certidão com status "success":**
   a. Verificar que o arquivo existe no `pdf_path`
   b. Fazer upload para o Google Drive usando `drive_folder_id` como destino
   c. Nomear o arquivo no Drive com `pdf_name` (nome normalizado em maiúsculas)
   d. Capturar `drive_file_id` e gerar o link de compartilhamento
3. **Para certidões com status "positive" (TJMG):** não há PDF, pular o upload.
4. **Para certidões com status "failure":** registrar em `upload_errors` com motivo, não tentar upload.
5. **Retornar a lista** `uploaded_files` com id e link de cada arquivo enviado com sucesso.

## Output Format

```yaml
uploaded_files:
  - orgao: "TST"
    pdf_name: "TST_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
    drive_file_id: "1xYzABCDEFGHIJKL"
    drive_link: "https://drive.google.com/file/d/1xYzABCDEFGHIJKL/view"
upload_errors:
  - orgao: "TRF6-EPROC"
    reason: "Arquivo não encontrado no caminho especificado"
```

## Output Example

```yaml
uploaded_files:
  - orgao: "TST"
    pdf_name: "TST_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
    drive_file_id: "1Abc2Def3GhI4JkL"
    drive_link: "https://drive.google.com/file/d/1Abc2Def3GhI4JkL/view"
  - orgao: "TRF6-EPROC"
    pdf_name: "TRF6-EPROC_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
    drive_file_id: "2Bcd3Efg4HiJ5KlM"
    drive_link: "https://drive.google.com/file/d/2Bcd3Efg4HiJ5KlM/view"
  - orgao: "TRF6-PJE"
    pdf_name: "TRF6-PJE_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
    drive_file_id: "3Cde4Fgh5IjK6LmN"
    drive_link: "https://drive.google.com/file/d/3Cde4Fgh5IjK6LmN/view"
  - orgao: "TRT3"
    pdf_name: "TRT3_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
    drive_file_id: "4Def5Ghi6JkL7MnO"
    drive_link: "https://drive.google.com/file/d/4Def5Ghi6JkL7MnO/view"
  - orgao: "RFB"
    pdf_name: "RFB_CARLOS-ALBERTO-MENDES-SOUZA_2026-04-23.pdf"
    drive_file_id: "5Efg6Hij7KlM8NoP"
    drive_link: "https://drive.google.com/file/d/5Efg6Hij7KlM8NoP/view"
upload_errors: []
```

## Quality Criteria

- [ ] Todos os PDFs disponíveis enviados para o `drive_folder_id` correto
- [ ] Cada arquivo nomeado exatamente no padrão [ORGAO]_[NOME-MAIUSCULO]_[DATA].pdf
- [ ] drive_file_id e drive_link capturados para cada upload bem-sucedido
- [ ] upload_errors documenta qualquer arquivo que não pôde ser enviado

## Veto Conditions

Bloquear e reportar se:
1. drive_folder_id inválido ou sem permissão de escrita
2. Nenhum arquivo foi enviado com sucesso (0 uploads bem-sucedidos com pelo menos 1 tentativa)
