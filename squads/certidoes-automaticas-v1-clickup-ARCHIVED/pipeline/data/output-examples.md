# Output Examples — Certidões Automáticas

## Exemplo 1 — Sucesso Completo (PF, 1 pessoa)

**Contexto:** Card do ClickUp com CPF de Pessoa Física, todas as 6 certidões coletadas com sucesso.

### card-data.json

```json
{
  "card_id": "9hz8k2p4m",
  "card_title": "Escritura - Rua das Flores, 123 - João da Silva",
  "drive_folder_id": "1Zk9Qw2eTyUiOp",
  "drive_folder_name": "joao-da-silva_9hz8k2p4m",
  "drive_folder_url": "https://drive.google.com/drive/folders/1Zk9Qw2eTyUiOp",
  "persons": [
    {
      "pessoa_index": 1,
      "nome": "JOÃO DA SILVA",
      "nome_normalizado": "joao-da-silva",
      "cpf_cnpj": "12345678909",
      "tipo_pessoa": "PF",
      "data_nascimento": "1980-07-15"
    }
  ]
}
```

### consolidado.json

```json
{
  "card_id": "9hz8k2p4m",
  "drive_folder_url": "https://drive.google.com/drive/folders/1Zk9Qw2eTyUiOp",
  "summary": {
    "total_persons": 1,
    "total_certidoes": 6,
    "success_count": 6,
    "failure_count": 0,
    "positive_tjmg_count": 0
  },
  "results": [
    {
      "pessoa_index": 1,
      "nome": "JOÃO DA SILVA",
      "certidoes": {
        "TST": {"status": "success", "drive_link": "https://drive.google.com/file/d/abc1/view"},
        "TRF6-EPROC": {"status": "success", "drive_link": "https://drive.google.com/file/d/abc2/view"},
        "TRF6-PJE": {"status": "success", "drive_link": "https://drive.google.com/file/d/abc3/view"},
        "TRT3": {"status": "success", "drive_link": "https://drive.google.com/file/d/abc4/view"},
        "TJMG": {"status": "success", "drive_link": "https://drive.google.com/file/d/abc5/view", "protocol": null},
        "RFB": {"status": "success", "drive_link": "https://drive.google.com/file/d/abc6/view"}
      }
    }
  ],
  "clickup_updated": true,
  "status_changed_to": "Certidões emitidas"
}
```

---

## Exemplo 2 — Resultado Parcial com TJMG Positiva (PJ, 1 empresa)

**Contexto:** CNPJ de Pessoa Jurídica. TJMG retornou positiva (processos existentes) e TRF6 PJE falhou por indisponibilidade.

### Comentários adicionados ao card do ClickUp:

```
✅ Certidões emitidas (4/6) — EMPRESA EXEMPLO LTDA

• TST: https://drive.google.com/file/d/xyz1/view
• TRF6 eproc: https://drive.google.com/file/d/xyz2/view
• TRT3: https://drive.google.com/file/d/xyz3/view
• Receita Federal: https://drive.google.com/file/d/xyz4/view (via fallback - 2ª via)

❌ TRF6 PJE: Sistema retornou erro 503 - serviço temporariamente indisponível. 
   Tentar manualmente em: https://sistemas.trf6.jus.br/certidao/#/

⚠️ TJMG — Resultado POSITIVO
Número do protocolo: 2026/00789012
CNPJ do requerente: 12345678000195
⚠️ Emissão manual necessária em 1-2 dias úteis.
Acessar https://rupe.tjmg.jus.br/ com o protocolo para acompanhar.
```

### Tag adicionada ao card:

`TJMG-PENDENTE`

---

## Exemplo 3 — Múltiplas Pessoas (PF, 2 vendedores)

**Contexto:** Card com 2 Pessoas Físicas (vendedor e coproprietário). Total de 12 certidões (6 × 2 pessoas).

### Tabela de resultado apresentada ao usuário:

```
✅ Squad Certidões Automáticas — Conclusão

Pasta no Drive: https://drive.google.com/drive/folders/1Abc...
Card ClickUp: Escritura - Rua das Acácias 456

PESSOA 1 — MARIA APARECIDA SANTOS
┌─────────────┬─────────┬──────────────────────────────────┐
│ Certidão    │ Status  │ Link Drive                       │
├─────────────┼─────────┼──────────────────────────────────┤
│ TST         │ ✅ OK   │ https://drive.google.com/...     │
│ TRF6 eproc  │ ✅ OK   │ https://drive.google.com/...     │
│ TRF6 PJE   │ ✅ OK   │ https://drive.google.com/...     │
│ TRT3        │ ✅ OK   │ https://drive.google.com/...     │
│ TJMG        │ ✅ OK   │ https://drive.google.com/...     │
│ Receita Fed.│ ✅ OK   │ https://drive.google.com/...     │
└─────────────┴─────────┴──────────────────────────────────┘

PESSOA 2 — JOSÉ CARLOS OLIVEIRA
┌─────────────┬──────────┬──────────────────────────────────┐
│ Certidão    │ Status   │ Link Drive / Observação          │
├─────────────┼──────────┼──────────────────────────────────┤
│ TST         │ ✅ OK    │ https://drive.google.com/...     │
│ TRF6 eproc  │ ✅ OK    │ https://drive.google.com/...     │
│ TRF6 PJE   │ ✅ OK    │ https://drive.google.com/...     │
│ TRT3        │ ✅ OK    │ https://drive.google.com/...     │
│ TJMG        │ ⚠️ POS  │ Protocolo 2026/00112233         │
│ Receita Fed.│ ✅ OK    │ https://drive.google.com/...     │
└─────────────┴──────────┴──────────────────────────────────┘

Status do card: "Certidões emitidas"
Tag adicionada: TJMG-PENDENTE (José Carlos)
```
