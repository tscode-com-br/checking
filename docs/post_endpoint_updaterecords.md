# Integração do Provedor com a API Checking

## Objetivo

Este documento descreve como um provedor externo deve enviar atividades para a API do sistema `checking`.

O endpoint recebe eventos de `check-in` e `check-out`, cria usuários novos quando a `chave` ainda não existe, registra todas as atividades em `checkinghistory` e mantém o estado atual do usuário na tabela `users`.

Importante:

- este endpoint atualiza apenas o banco de dados local da API;
- este endpoint nao envia nada ao FORMS;
- isso foi definido para evitar looping infinito, porque os dados postados aqui ja se originam da base do FORMS.

## Endereço de produção

- Domínio principal da API: `https://www.tscode.com.br`
- Base pública recomendada da API: `https://www.tscode.com.br/api`
- Health check público: `https://www.tscode.com.br/api/health`
- Endpoint deste provedor: `POST https://www.tscode.com.br/api/provider/updaterecords`

## Observação sobre IP público

Em `17/04/2026`, o domínio `www.tscode.com.br` resolveu para o IP público `157.230.35.21`.

Importante:

- este IP pode mudar a qualquer momento;
- o provedor deve sempre preferir o domínio `www.tscode.com.br`;
- não recomendamos fixar o IP na integração.

## Segurança e autenticação

O endpoint exige uma chave compartilhada enviada no header:

- Header obrigatório: `X-Provider-Shared-Key`

Valor esperado:

- o valor configurado no servidor através da variável de ambiente `PROVIDER_SHARED_KEY`
- valor atual configurado: `PETROBRASP80P82P83`

Exemplo:

```http
X-Provider-Shared-Key: PETROBRASP80P82P83
```

## Protocolo de conexão

- Método: `POST`
- Content-Type: `application/json`
- Transporte: `HTTPS`
- Charset recomendado: `UTF-8`

## Endpoint

```text
POST /api/provider/updaterecords
```

URL completa:

```text
https://www.tscode.com.br/api/provider/updaterecords
```

## Payload JSON

Campos aceitos pelo endpoint:

| Campo | Tipo | Obrigatório | Regras |
|---|---|---:|---|
| `chave` | string | Sim | 4 caracteres alfanuméricos |
| `nome` | string | Sim | Nome do usuário |
| `projeto` | string | Sim | Deve ser `P80`, `P82` ou `P83` |
| `atividade` | string | Sim | Deve ser `check-in` ou `check-out` |
| `informe` | string | Sim | Deve ser `normal` ou `retroativo` |
| `data` | string | Sim | Formato `dd/mm/aaaa` |
| `hora` | string | Sim | Formato `hh:mm:ss` |

## Observação importante sobre `projeto`

Embora uma descrição anterior tenha omitido `projeto` na lista de campos, este campo foi implementado como obrigatório.

Motivo:

- a tabela `users` exige `projeto`;
- quando a `chave` já existe, o endpoint precisa conseguir atualizar `users.projeto`;
- quando a `chave` ainda não existe, o endpoint precisa conseguir criar o usuário com projeto válido.

## Exemplo de payload

```json
{
  "chave": "CF10",
  "nome": "ADRIANO JOSE DA SILVA",
  "projeto": "P82",
  "atividade": "check-in",
  "informe": "normal",
  "data": "17/04/2026",
  "hora": "07:26:00"
}
```

## Regras aplicadas pela API

### 1. Validação da chave

- a `chave` é convertida para maiúsculas;
- deve ter exatamente 4 caracteres alfanuméricos;
- se for inválida, a API retorna erro `422`.

### 2. Tratamento do nome

Quando o usuário ainda não existe, o nome é salvo com normalização automática:

- apenas a primeira letra de cada palavra fica maiúscula;
- as palavras `de`, `do`, `da`, `dos`, `das` e `e` ficam sempre minúsculas.

Exemplos:

- `ADRIANO JOSE DA SILVA` -> `Adriano Jose da Silva`
- `MARIA DE FATIMA DOS SANTOS` -> `Maria de Fatima dos Santos`

Observação:

- se a `chave` já existir, o endpoint não altera `users.nome`;
- o nome enviado serve para cadastro inicial do usuário novo.

### 3. Cadastro ou atualização do usuário

Se a `chave` ainda não existir na tabela `users`:

- a API cria um novo usuário;
- preenche `chave`, `nome`, `projeto`;
- inicializa os demais campos ainda não informados como `null` quando aplicável.

Se a `chave` já existir:

- a API mantém o usuário existente;
- atualiza `users.projeto` somente se o `projeto` recebido for diferente do atual;
- não troca o nome existente.

### 4. Formação do timestamp

A API junta:

- `data` no formato `dd/mm/aaaa`
- `hora` no formato `hh:mm:ss`

e forma um único `datetime` com timezone do sistema.

Timezone atual do servidor:

- `Asia/Singapore`

Exemplo:

- `data = 17/04/2026`
- `hora = 07:26:00`

Resultado lógico gravado:

- `2026-04-17T07:26:00+08:00`

### 5. Atualização de `checkinghistory`

Toda atividade válida recebida é registrada na tabela `checkinghistory`.

Campos gravados:

- `chave`
- `atividade`
- `projeto`
- `time`
- `informe`

### 5.1. Regra de isolamento em relacao ao FORMS

Ao receber dados em `updaterecords`, a API:

- nao enfileira `FormsSubmission`;
- nao chama nenhum fluxo de envio para o FORMS;
- nao replica a atividade para o formulario externo;
- apenas atualiza `users`, `checkinghistory`, `user_sync_events` e os logs internos da API;
- registra cada recebimento para consulta posterior na aba administrativa `Forms`.

Essa regra existe para impedir um ciclo infinito entre a base que origina os dados e a propria API.

### 6. Atualização de `users`

A tabela `users` representa apenas o estado atual do usuário.

Regra aplicada:

- se nao existir nenhum estado atual, a API atualiza `users` com o evento recebido;
- se o evento recebido for claramente mais antigo do que o estado atual existente, a API grava o histórico, mas preserva o estado mais novo em `users`;
- se houver conflito no mesmo dia e na mesma atividade, os dados recebidos por `updaterecords` nao tem prioridade sobre dados vindos do webapp, app mobile ou outras fontes internas de sincronizacao;
- nesses conflitos, a API grava o histórico e o log de recebimento, mas preserva em `users` o estado da fonte considerada autoritativa.

Campos atualizados quando o evento é o mais recente:

- `users.projeto`
- `users.checkin`
- `users.time`
- `users.local`, com o valor `Forms` quando o estado corrente veio deste endpoint

Conversão de atividade:

- `check-in` -> `users.checkin = true`
- `check-out` -> `users.checkin = false`

### 7. Deduplicação

A API deduplica o evento com base na combinação lógica:

- `chave`
- `projeto`
- `atividade`
- `informe`
- `time`

Se o provedor reenviar exatamente o mesmo evento:

- a API não grava uma duplicata no histórico;
- a resposta retorna `duplicate: true`.

## Resposta de sucesso

Exemplo:

```json
{
  "ok": true,
  "duplicate": false,
  "created_user": true,
  "updated_project": false,
  "updated_current_state": true,
  "message": "Provider event processed successfully",
  "chave": "CF10",
  "projeto": "P82",
  "atividade": "check-in",
  "informe": "normal",
  "time": "2026-04-17T07:26:00+08:00"
}
```

## Campos da resposta

| Campo | Tipo | Descrição |
|---|---|---|
| `ok` | boolean | Indica que a API processou a requisição |
| `duplicate` | boolean | Indica se o evento já havia sido processado antes |
| `created_user` | boolean | Indica se um usuário novo foi criado |
| `updated_project` | boolean | Indica se `users.projeto` foi alterado |
| `updated_current_state` | boolean | Indica se `users.time/checkin` foi atualizado |
| `message` | string | Mensagem textual do processamento |
| `chave` | string | Chave efetivamente usada |
| `projeto` | string | Projeto final do usuário após o processamento |
| `atividade` | string | Atividade recebida |
| `informe` | string | Informe recebido |
| `time` | string datetime ISO 8601 | Data e hora mescladas e normalizadas |

## Erros possíveis

### 401 Unauthorized

Quando o header `X-Provider-Shared-Key` estiver ausente ou inválido.

Exemplo:

```json
{
  "detail": "Invalid provider shared key"
}
```

### 422 Unprocessable Entity

Quando o payload estiver malformado.

Exemplos:

- `chave` com tamanho diferente de 4;
- `atividade` fora de `check-in` ou `check-out`;
- `informe` fora de `normal` ou `retroativo`;
- `projeto` fora de `P80`, `P82`, `P83`;
- `data` ou `hora` fora do formato esperado.

## Exemplo com cURL

```bash
curl -X POST "https://www.tscode.com.br/api/provider/updaterecords" \
  -H "Content-Type: application/json" \
  -H "X-Provider-Shared-Key: PETROBRASP80P82P83" \
  -d '{
    "chave": "CF10",
    "nome": "ADRIANO JOSE DA SILVA",
    "projeto": "P82",
    "atividade": "check-in",
    "informe": "normal",
    "data": "17/04/2026",
    "hora": "07:26:00"
  }'
```

## Exemplo com Python

```python
import requests

url = "https://www.tscode.com.br/api/provider/updaterecords"
headers = {
    "Content-Type": "application/json",
    "X-Provider-Shared-Key": "PETROBRASP80P82P83",
}
payload = {
    "chave": "CF10",
    "nome": "ADRIANO JOSE DA SILVA",
    "projeto": "P82",
    "atividade": "check-in",
    "informe": "normal",
    "data": "17/04/2026",
    "hora": "07:26:00",
}

response = requests.post(url, json=payload, headers=headers, timeout=30)
print(response.status_code)
print(response.json())
```

## Recomendação de operação do provedor

- sempre enviar via `HTTPS`;
- sempre usar o domínio `www.tscode.com.br`;
- não fixar IP;
- tratar `duplicate: true` como sucesso idempotente;
- registrar localmente o payload enviado e a resposta recebida;
- usar timeout de cliente entre `15` e `30` segundos;
- em caso de falha de rede, reenviar o mesmo evento com exatamente os mesmos dados.

## Observação sobre chave primária

Foi solicitado tornar `chave` a chave primária de cada tabela.

Isso não foi aplicado, e não é aconselhável neste sistema, pelos seguintes motivos:

- em `checkinghistory`, uma mesma `chave` precisa ter várias linhas, uma para cada atividade;
- portanto, `chave` sozinha jamais pode ser chave primária dessa tabela;
- o sistema atual já usa identificadores inteiros internos em várias tabelas e fluxos administrativos;
- trocar todas as PKs agora aumentaria bastante o risco de regressão sem trazer ganho proporcional.

Recomendação adotada:

- `users.chave` permanece como identificador de negócio único do usuário;
- `checkinghistory` mantém múltiplos registros por `chave`;
- a API sempre resolve primeiro o usuário em `users` pela `chave` e, a partir daí, atualiza os demais registros.
