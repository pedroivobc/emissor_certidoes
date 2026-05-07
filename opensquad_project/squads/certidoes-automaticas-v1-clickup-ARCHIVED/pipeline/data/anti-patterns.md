# Anti-Patterns — Certidões Automáticas

## Erros Críticos (Never Do)

### 1. Passar CPF/CNPJ formatado para os portais
**Problema:** Campos como "123.456.789-09" causam erro de validação em praticamente todos os portais governamentais.
**Correto:** Normalizar sempre: remover pontos, hífens, barras e espaços. Enviar somente dígitos: "12345678909".

### 2. Fechar o browser antes de confirmar o download
**Problema:** O arquivo pode não ter sido salvo. Portais frequentemente invalidam links após navegação ou timeout.
**Correto:** Verificar que o arquivo existe no caminho especificado e tem tamanho > 0 antes de fechar a aba.

### 3. Tratar TJMG positiva como falha técnica
**Problema:** Uma certidão positiva é um resultado válido do sistema — a pessoa tem processos no TJMG. Não é um erro.
**Correto:** Registrar `status: "positive"`, capturar o protocolo e tratar com comentário + tag TJMG-PENDENTE.

### 4. Não esperar pelo código de verificação TJMG
**Problema:** O e-mail do TJMG pode levar até 2 minutos para chegar. Desistir cedo resulta em falha desnecessária.
**Correto:** Tentar 4 vezes com intervalo de 30 segundos cada antes de declarar timeout.

### 5. Processar Receita Federal PF sem DATA DE NASCIMENTO
**Problema:** O portal da Receita Federal exige data de nascimento para Pessoa Física. Sem ela, o formulário rejeita a consulta.
**Correto:** Validar a presença de DATA DE NASCIMENTO na Fase 1, antes de iniciar qualquer coleta.

### 6. Mudar status do ClickUp para "Certidões emitidas" antes dos uploads
**Problema:** O status indica conclusão. Se mudado antes dos uploads, o responsável pode assumir que tudo está anexado quando não está.
**Correto:** Mudar o status somente após confirmar todos os uploads e anexos no card.

### 7. Ignorar múltiplas pessoas no card
**Problema:** Um card pode ter mais de um CPF (ex: 2 vendedores). Ignorar a segunda pessoa gera processo incompleto.
**Correto:** Detectar todos os conjuntos de dados e processar cada pessoa individualmente.

## Boas Práticas (Always Do)

### 1. Renomear o arquivo no download, não depois
Salvar já com o nome `[ORGAO]_[NOME]_[DATA].pdf` evita arquivos com nomes de sistema temporários que podem ser difíceis de rastrear.

### 2. Documentar falhas com contexto suficiente para ação manual
Um comentário "Falhou" não ajuda ninguém. Incluir: portal, etapa, mensagem de erro exata, URL para tentativa manual.

### 3. Verificar o tipo de pessoa antes de qualquer portal
TST aceita tanto CPF quanto CNPJ no mesmo campo, mas Receita Federal tem fluxos completamente diferentes para PF e PJ. Definir tipo antes de começar.

### 4. Confirmar a pasta do Drive antes de fazer uploads
Verificar que `drive_folder_id` está disponível e tem permissão de escrita antes de tentar o upload do primeiro arquivo.

### 5. Separar o registro do TJMG dos demais portais no output
O TJMG roda em step separado (inline) por exigir e-mail. O manifesto de saída deve ter `tjmg-result.json` separado de `certidoes-parciais.json` para evitar conflito de merge de dados.
