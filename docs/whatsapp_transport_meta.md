# Integracao WhatsApp do Transporte

Este projeto agora suporta integracao real com a Meta WhatsApp Cloud API para o fluxo de transporte.

Se esta e a sua primeira vez configurando a Meta, siga antes o guia [docs/whatsapp_meta_primeira_configuracao.md](docs/whatsapp_meta_primeira_configuracao.md).

## O que e obrigatorio

Voce vai precisar de um numero de WhatsApp Business habilitado no provedor.

O `phone_number_id` nao substitui o numero. Ele e apenas o identificador tecnico que a Meta entrega para a API depois que o numero esta conectado ao WhatsApp Business.

Resumo pratico:

- desenvolvimento: pode usar o numero de teste da Meta;
- producao: precisa de um numero real habilitado no WhatsApp Business;
- API: usa `WHATSAPP_PHONE_NUMBER_ID` para enviar mensagens;
- webhook: usa `WHATSAPP_WEBHOOK_VERIFY_TOKEN` e, de preferencia, `WHATSAPP_APP_SECRET`.

## Variaveis de ambiente

Defina no backend:

```env
WHATSAPP_ENABLED=true
WHATSAPP_PROVIDER=meta
WHATSAPP_WEBHOOK_VERIFY_TOKEN=seu-token-de-verificacao
WHATSAPP_ACCESS_TOKEN=seu-token-de-acesso-da-meta
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_BUSINESS_ACCOUNT_ID=opcional
WHATSAPP_APP_SECRET=opcional-mas-recomendado
WHATSAPP_GRAPH_API_VERSION=v22.0
```

## Como descobrir cada valor na Meta

Se hoje voce so tem o numero de telefone, isso ainda nao e suficiente para preencher o `.env`.

O fluxo correto e este:

1. Crie ou abra um app da Meta com o caso de uso WhatsApp.
2. No App Dashboard, abra `WhatsApp > API Setup`.
3. Conecte um numero real ao WhatsApp Business ou use o numero de teste da Meta para desenvolvimento.
4. Depois que o numero estiver conectado, copie os IDs exibidos pela Meta.

Mapa direto de cada variavel:

- `WHATSAPP_WEBHOOK_VERIFY_TOKEN`: este valor nao vem da Meta. Voce escolhe um valor secreto no seu `.env` e cola exatamente o mesmo no cadastro do webhook.
- `WHATSAPP_PHONE_NUMBER_ID`: fica em `App Dashboard > WhatsApp > API Setup > Phone number ID`.
- `WHATSAPP_BUSINESS_ACCOUNT_ID`: fica em `App Dashboard > WhatsApp > API Setup > WhatsApp Business Account ID`.
- `WHATSAPP_APP_SECRET`: fica em `App Dashboard > App Settings > Basic > App Secret`.
- `WHATSAPP_ACCESS_TOKEN`: gere um token permanente de System User em `Business Settings > Users > System users`.

Para gerar `WHATSAPP_ACCESS_TOKEN` do jeito certo:

1. Abra `Business Settings`.
2. Entre em `Users > System users`.
3. Crie um System User.
4. Em `Assign assets`, associe o app da Meta e o WhatsApp Business Account.
5. Gere um token com, no minimo, estas permissoes:
	`business_management`, `whatsapp_business_management`, `whatsapp_business_messaging`.

Observacao importante: o numero de telefone em si nao e salvo no `.env`. O backend usa o `WHATSAPP_PHONE_NUMBER_ID`, que so aparece depois que o numero ja esta conectado ao WhatsApp Business no painel da Meta.

## Se voce quiser testar antes do numero real

Para desenvolvimento, a Meta cria um numero de teste no proprio painel.

Nesse caso:

1. Use o numero de teste apenas para validacao tecnica.
2. Pegue o `Phone number ID` desse numero de teste em `WhatsApp > API Setup`.
3. Adicione o seu celular real na lista de destinatarios permitidos de teste.
4. Faça o webhook funcionar e valide o fluxo fim a fim.

Para producao, troque depois para um numero real do WhatsApp Business. O numero de teste nao deve ser usado como configuracao de producao.

## Endpoints

- verificacao do webhook: `GET /api/transport/whatsapp/webhook`
- webhook de mensagens/status: `POST /api/transport/whatsapp/webhook`
- reenvio manual de notificacoes pendentes: `POST /api/transport/whatsapp/notifications/dispatch`

## Como funciona

1. O usuario envia mensagem para o numero do WhatsApp Business.
2. A Meta chama `POST /api/transport/whatsapp/webhook`.
3. O backend reaproveita a logica existente de `process_bot_message()`.
4. As respostas do bot sao enviadas de volta pela Graph API.
5. Quando o admin confirma uma alocacao, a notificacao e tentada automaticamente via WhatsApp.
6. Se o envio falhar, a notificacao continua em `transport_notifications` com status `pending` para novo despacho.

## Configuracao do webhook na Meta

Use como callback URL:

```text
https://SEU_DOMINIO/api/transport/whatsapp/webhook
```

Use no campo de token de verificacao o mesmo valor definido em `WHATSAPP_WEBHOOK_VERIFY_TOKEN`.

Para o ambiente atualmente esperado deste projeto, o valor pratico fica assim:

```text
Callback URL: https://tscode.com.br/api/transport/whatsapp/webhook
Verify token: valor de WHATSAPP_WEBHOOK_VERIFY_TOKEN no arquivo .env
Webhook field: messages
App secret: o mesmo valor exibido no painel da Meta para o app, copiado para WHATSAPP_APP_SECRET
```

Checklist curto no painel da Meta:

1. Abra App Dashboard > WhatsApp > Configuration.
2. Em Webhook, informe `https://tscode.com.br/api/transport/whatsapp/webhook` como callback URL.
3. Cole exatamente o valor de `WHATSAPP_WEBHOOK_VERIFY_TOKEN` no campo Verify token.
4. Conclua a verificacao do webhook.
5. Em Webhook fields, assine pelo menos `messages`.
6. Copie o App Secret do app para `WHATSAPP_APP_SECRET` e use um access token de system user em `WHATSAPP_ACCESS_TOKEN`.

## Numero de teste x producao

O numero de teste da Meta serve para desenvolvimento e validacao inicial do fluxo.

Nao trate esse numero como configuracao de producao. Para operar em producao, use um numero real vinculado ao seu WhatsApp Business Account e gere os IDs/tokens desse numero real.

## Observacao importante

O projeto manteve o endpoint interno `POST /api/transport/bot/messages` para testes locais e integracoes controladas por chave compartilhada. A integracao oficial do WhatsApp usa o webhook novo e nao depende desse endpoint interno na operacao real.