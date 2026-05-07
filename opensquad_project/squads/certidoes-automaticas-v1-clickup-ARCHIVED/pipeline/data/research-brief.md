# Research Brief — Certidões Automáticas

## Portais e URLs

| Portal | URL | Campos de Entrada | Observações |
|--------|-----|-------------------|-------------|
| TST CNDT | https://cndt-certidao.tst.jus.br/gerarCertidao.faces | CPF ou CNPJ | Emissão imediata, gratuita |
| TRF6 eproc | https://certidao.trf6.jus.br/consulta | CPF/CNPJ | Sistema eproc do TRF6 |
| TRF6 PJE | https://sistemas.trf6.jus.br/certidao/#/ | CPF/CNPJ | SPA — aguardar carregamento completo |
| TRT3 CEAT | https://certidao.trt3.jus.br/certidao/feitosTrabalhistas/ | PF/PJ → CPF/CNPJ → CAPTCHA → Consultar | CAPTCHA obrigatório |
| TJMG/RUPE | https://rupe.tjmg.jus.br/rupe/justica/publico/certidoes/criarSolicitacaoCertidao.rupe?solicitacaoPublica=true | CPF/CNPJ do requerido + dados do solicitante fixo | Código de verificação por e-mail |
| Receita Federal | https://servicos.receitafederal.gov.br/servico/certidoes/#/home | PF: CPF + data nascimento / PJ: CNPJ | Fallback: consultar por data de validade |

## Tipos de Certidão

- **TST CNDT:** Certidão Negativa de Débitos Trabalhistas — comprova ausência de débitos trabalhistas no Banco Nacional de Devedores Trabalhistas (BNDT). Validade: 180 dias.
- **TRF6 eproc:** Certidão de ações judiciais federais no sistema eproc. Abrange processos eletrônicos na 6ª Região (MG e ES).
- **TRF6 PJE:** Certidão de ações judiciais federais no sistema PJE. Cobre processos no sistema PJE da 6ª Região.
- **TRT3 CEAT:** Certidão Eletrônica de Ações Trabalhistas — comprova ausência de ações trabalhistas na 3ª Região (MG). Diferente do CNDT: é regional, não nacional.
- **TJMG/RUPE:** Certidão de ações cíveis no Tribunal de Justiça de MG. Resultado positivo = processos existentes (sem PDF automático, apenas protocolo).
- **Receita Federal:** Certidão de Regularidade Fiscal — comprova regularidade com impostos federais.

## Dados Fixos do Solicitante TJMG

```
Nome: PEDRO IVO BATISTA CLEMENTE
CPF: 11773105620
E-mail: contato@clementeassessoria.com
```

## Padrão de Nomenclatura de Arquivos

```
[ORGAO]_[NOME-MAIUSCULO-SEM-ACENTO]_[AAAA-MM-DD].pdf
```

Exemplos:
- `TST_JOAO-SILVA_2026-04-23.pdf`
- `TRF6-EPROC_MARIA-SANTOS_2026-04-23.pdf`
- `TRF6-PJE_CARLOS-MENDES_2026-04-23.pdf`
- `TRT3_ANA-OLIVEIRA_2026-04-23.pdf`
- `TJMG_PEDRO-COSTA_2026-04-23.pdf`
- `RFB_LUCIA-FERREIRA_2026-04-23.pdf`

## Fontes

- TST: https://www.tst.jus.br/certidao1
- TRT3 portal: https://portal.trt3.jus.br/internet/servicos/certidoes/cndt
- TJMG RUPE: https://rupe.tjmg.jus.br/
