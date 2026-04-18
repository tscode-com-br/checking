# Primeira Configuracao da Meta para WhatsApp

Este guia e para o caso mais comum: voce ja tem um numero que pretende usar, mas nunca criou um app da Meta nem registrou esse numero no WhatsApp Business Platform.

## Resultado esperado

Ao final deste roteiro, voce tera:

- um app da Meta criado com o produto WhatsApp;
- um WhatsApp Business Account ligado ao app;
- um numero registrado na Meta;
- os valores necessarios para preencher o `.env`;
- o webhook do projeto validado na Meta.

## O que ter em maos antes de comecar

- uma conta Meta/Facebook com acesso ao Meta for Developers;
- acesso ao numero de telefone que vai receber o codigo por SMS ou ligacao;
- este endpoint publico do projeto:
  `https://tscode.com.br/api/transport/whatsapp/webhook`
- o valor ja preparado em [.env](.env) para `WHATSAPP_WEBHOOK_VERIFY_TOKEN`.

## Caminho mais seguro para quem esta fazendo isso pela primeira vez

Se voce nunca configurou nada na Meta, o caminho mais seguro e:

1. criar o app da Meta;
2. validar o webhook primeiro com o numero de teste da Meta;
3. so depois registrar o numero real.

Isso reduz risco de travar a configuracao logo no numero real.

## Passo 1. Criar o app da Meta

1. Abra `https://developers.facebook.com/apps`.
2. Clique em `Create App`.
3. Escolha o caso de uso `Connect with customers through WhatsApp`.
4. Informe nome do app e email.
5. Escolha um `Business Portfolio` existente ou crie um novo.
6. Finalize a criacao.

Ao terminar, a Meta costuma abrir a area `WhatsApp > Quickstart` ou `WhatsApp > API Setup`.

## Passo 2. Ativar o produto WhatsApp

1. No App Dashboard, abra `WhatsApp > API Setup`.
2. Clique em `Start using the API`, se essa opcao aparecer.
3. Confirme ou crie o `WhatsApp Business Account`.

Ao final dessa etapa, a Meta passa a exibir pelo menos:

- `WhatsApp Business Account ID`
- um numero de teste da Meta
- `Phone number ID` do numero de teste

## Passo 3. Fazer a primeira validacao com o numero de teste da Meta

Antes de mexer no numero real, faca isto:

1. Ainda em `WhatsApp > API Setup`, use o numero de teste da Meta.
2. Adicione o seu celular real na lista de destinatarios permitidos de teste.
3. Envie a mensagem inicial de teste que a Meta oferece no painel.
4. Responda essa mensagem no WhatsApp para abrir a janela de atendimento de 24 horas.

Se isso funcionar, a parte de conta/app/permissoes esta saudável.

## Passo 4. Registrar o webhook deste projeto

1. No App Dashboard, abra `WhatsApp > Configuration`.
2. Na area de Webhook, clique para configurar ou editar.
3. Use estes valores:

```text
Callback URL: https://tscode.com.br/api/transport/whatsapp/webhook
Verify token: o valor de WHATSAPP_WEBHOOK_VERIFY_TOKEN salvo no arquivo .env
```

4. Salve e conclua a verificacao.
5. Em `Webhook fields`, assine pelo menos `messages`.

Se a verificacao falhar, normalmente o problema e um destes:

- URL publica incorreta;
- backend fora do ar;
- token digitado diferente do valor em [.env](.env);
- `WHATSAPP_ENABLED` ainda desativado no ambiente que esta recebendo o webhook.

## Passo 5. Gerar o token permanente

O token temporario do Quickstart nao serve para operacao normal. Gere um token permanente:

1. Abra `https://business.facebook.com/latest/settings`.
2. Entre em `Users > System users`.
3. Clique em `Add` e crie um `System User`.
4. Selecione esse System User e clique em `Assign assets`.
5. Associe:
   - o app da Meta, com `Manage app`;
   - o WhatsApp Business Account, com `Manage WhatsApp Business Accounts`.
6. Gere um token para esse System User com estas permissoes:
   - `business_management`
   - `whatsapp_business_management`
   - `whatsapp_business_messaging`

Esse valor vai para `WHATSAPP_ACCESS_TOKEN`.

## Passo 6. Copiar os valores certos para o `.env`

Depois dessas etapas, preencha assim:

- `WHATSAPP_ENABLED=true`
- `WHATSAPP_PROVIDER=meta`
- `WHATSAPP_WEBHOOK_VERIFY_TOKEN`: ja existe em [.env](.env)
- `WHATSAPP_ACCESS_TOKEN`: token do System User
- `WHATSAPP_PHONE_NUMBER_ID`: valor exibido em `WhatsApp > API Setup`
- `WHATSAPP_BUSINESS_ACCOUNT_ID`: valor exibido em `WhatsApp > API Setup`
- `WHATSAPP_APP_SECRET`: `App Settings > Basic > App Secret`
- `WHATSAPP_GRAPH_API_VERSION=v22.0`

## Passo 7. Registrar o numero real

Quando a validacao com o numero de teste estiver pronta, ai sim registre o numero real.

No geral, o fluxo fica em `WhatsApp > API Setup` com opcao de adicionar numero. A Meta vai pedir dados como:

- nome de exibicao;
- categoria do negocio;
- numero completo com codigo do pais;
- confirmacao via SMS ou ligacao.

Pontos importantes:

- o numero precisa estar sob seu controle para receber o codigo;
- se o numero ja estiver em uso em outro fluxo de WhatsApp, a Meta pode exigir migracao ou desvinculacao antes de concluir;
- depois do cadastro, a Meta passa a mostrar um novo `Phone number ID` para esse numero real.

Quando isso acontecer, substitua no `.env` o `WHATSAPP_PHONE_NUMBER_ID` do teste pelo do numero real.

## Passo 8. Teste fim a fim deste projeto

Com o `.env` preenchido e o webhook configurado:

1. deixe `WHATSAPP_ENABLED=true`;
2. garanta que o backend exposto em `https://tscode.com.br` esta atualizado;
3. envie uma mensagem para o numero conectado;
4. confirme se a Meta entrega evento em `POST /api/transport/whatsapp/webhook`;
5. confirme se o bot responde;
6. crie uma alocacao no painel e veja se a notificacao sai via WhatsApp.

## O que voce pode preencher agora, sem registrar o numero real

Voce ja consegue preencher ou validar estas partes:

- `WHATSAPP_WEBHOOK_VERIFY_TOKEN`: ja esta pronto em [.env](.env)
- `WHATSAPP_APP_SECRET`: assim que o app existir
- `WHATSAPP_ACCESS_TOKEN`: assim que o System User existir
- `WHATSAPP_BUSINESS_ACCOUNT_ID`: assim que o produto WhatsApp estiver ativo
- `WHATSAPP_PHONE_NUMBER_ID`: primeiro do numero de teste, depois do numero real

## O que muda entre teste e producao

- teste: use o numero de teste da Meta para validar app, token e webhook;
- producao: use um numero real conectado ao WhatsApp Business;
- o numero de teste nao deve ser mantido como configuracao de producao.

## Se algo der errado

Os erros mais comuns no primeiro setup sao:

1. webhook nao verifica porque o token no painel nao bate com o `.env`;
2. token de acesso temporario expira e o envio para de funcionar;
3. `Phone number ID` copiado do numero errado;
4. campo `messages` do webhook nao foi assinado;
5. o numero real ainda nao foi concluido na etapa de verificacao por SMS/ligacao.

Se voce quiser, o proximo passo pode ser simplesmente abrir o painel da Meta e seguir este guia em paralelo, item por item.