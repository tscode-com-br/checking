# Contexto para Login Simples no Admin

> Status em 2026-03-29: a implementacao por sessao ja foi concluida e o fallback legado por `x-admin-key`/`admin_key` foi removido da aplicacao. As secoes abaixo registram o estado anterior analisado antes da implementacao.

## Objetivo deste documento

Consolidar o estado atual da API e do website administrativo para preparar a introducao de um login simples, com o menor impacto possivel no fluxo existente do sistema.

## Arquitetura atual

### Backend

- A aplicacao e uma API FastAPI que tambem serve o frontend administrativo estatico.
- As rotas de API ficam em `sistema/app/routers`.
- O frontend admin e servido pelo proprio backend a partir de `sistema/app/static/admin`.
- A raiz `/` entrega a interface admin estaticamente, e `/admin` apenas redireciona para a raiz.

### Frontend

- O admin e um SPA simples em HTML + CSS + JavaScript puro, sem framework.
- Todo o estado do frontend e mantido em memoria no navegador.
- A comunicacao com o backend acontece via `fetch()` e `EventSource`.

## Fluxos de negocio ja implementados

### Fluxo do dispositivo

- O ESP32 autentica apenas com `device_shared_key`.
- `POST /api/device/heartbeat` registra sinal de vida do dispositivo.
- `POST /api/scan` recebe leituras RFID, aplica regras de negocio e enfileira o envio ao Microsoft Forms.

### Fluxo administrativo

- O admin lista usuarios em check-in e check-out.
- O admin cadastra usuarios a partir de pendencias de RFID desconhecido.
- O admin remove pendencias e usuarios.
- O admin visualiza eventos operacionais.
- O admin arquiva logs de eventos em CSV e faz download dos arquivos salvos.
- O admin recebe atualizacoes em tempo real por Server-Sent Events para refrescar tabelas.

## Modelo de seguranca atual

### O que existe hoje

- O backend protege as rotas administrativas com uma unica chave estatica em `settings.admin_api_key`.
- Essa chave e validada pelo header `x-admin-key`.
- O stream SSE usa a mesma chave, mas via query string `admin_key`.
- O frontend embute a chave padrao diretamente no JavaScript como constante `DEFAULT_ADMIN_KEY`.

### O que nao existe hoje

- Nao existe tabela de administradores.
- Nao existe login, logout, sessao ou cookie.
- Nao existe token Bearer, JWT ou refresh token.
- Nao existe middleware de autenticacao ou autorizacao por perfil.
- Nao existe tela de login separada.
- Nao existe persistencia segura de identidade do admin no navegador.

## Implicacoes praticas para o login

### Pontos favoraveis

- O escopo de autenticacao esta concentrado em `/api/admin`, o que facilita trocar a dependencia atual por uma verificacao de sessao.
- O frontend e pequeno e centraliza as chamadas em `adminHeaders()` e `fetchJson()`, entao a troca de estrategia de autenticacao pode ser feita em poucos pontos.
- Nao ha app mobile ou multiplos clientes administrativos para compatibilizar.

### Pontos de atencao

- O SSE atual depende de query string com segredo; com login simples, isso deve migrar para cookie de sessao ou outro mecanismo compativel com `EventSource`.
- Como o admin e servido em `/`, qualquer tela de login simples precisa conviver com o site estatico existente ou substituir o bootstrap atual.
- O frontend hoje assume acesso imediato ao carregar a pagina; nao ha estado intermediario de usuario nao autenticado.
- O projeto nao possui entidade de usuario administrativo, entao sera necessario decidir entre credenciais unicas via `.env` ou tabela `admin_users`.

## Menor caminho para um login simples

### Opcao recomendada para primeira iteracao

Implementar autenticacao por sessao baseada em cookie HttpOnly usando uma unica credencial administrativa definida em ambiente.

### Motivos

- Mantem o sistema simples.
- Evita expor segredo fixo no JavaScript.
- Funciona melhor com `fetch()` e com `EventSource` no mesmo dominio.
- Exige poucas mudancas de schema se a credencial ficar em `.env`.
- Permite evoluir depois para tabela de administradores sem reescrever toda a protecao.

### Desenho sugerido

1. Criar endpoint `POST /api/admin/login` que valida `username` e `password` vindos do formulario.
2. Ao autenticar, gerar uma sessao assinada e armazenar em cookie HttpOnly, `SameSite=Lax`.
3. Criar endpoint `POST /api/admin/logout` para invalidar a sessao.
4. Criar endpoint `GET /api/admin/session` para o frontend descobrir se ha usuario autenticado.
5. Substituir `require_admin_key()` por `require_admin_session()` em todas as rotas `/api/admin`.
6. Adaptar o SSE para validar sessao por cookie, removendo `admin_key` da query string.
7. No frontend, exibir tela de login antes do carregamento das abas quando nao houver sessao valida.

## Estrutura de dados atual relevante para o admin

### Tabelas existentes

- `users`: usuarios operacionais com RFID, chave, nome, projeto, local e estado de presenca.
- `pending_registrations`: RFIDs ainda nao cadastrados.
- `check_events`: trilha de auditoria do sistema.
- `device_heartbeats`: sinais de vida enviados pela ESP32.
- `forms_submissions`: fila persistida de envio ao Microsoft Forms.

### Observacao importante

- A tabela `users` representa pessoas lidas pelo RFID, nao administradores do sistema.
- Reutilizar `users` para login do admin seria conceitualmente incorreto e criaria acoplamento entre operacao fisica e acesso administrativo.

## Impacto esperado por camada

### Backend

- Novo modulo de autenticacao administrativa.
- Novos endpoints de login, logout e sessao.
- Nova dependencia FastAPI para validar sessao.
- Ajuste do endpoint SSE.

### Frontend

- Nova tela ou estado de login.
- Bootstrap inicial condicionado a sessao valida.
- Remocao da constante `DEFAULT_ADMIN_KEY` e do envio de `x-admin-key`.
- Tratamento centralizado de `401` para redirecionar ao login.

### Testes

- Atualizar testes que hoje acessam `/api/admin/*` com `x-admin-key`.
- Adicionar testes de login bem-sucedido, login invalido, acesso sem sessao e logout.
- Adicionar teste do stream SSE autenticado.

## Decisoes que ainda precisamos tomar

1. A primeira versao usara credencial unica no `.env` ou tabela de administradores?
2. O login precisa de um unico usuario admin ou de multiplos usuarios?
3. A sessao pode ser stateless assinada ou precisamos de invalidacao no servidor?
4. O admin deve continuar servido em `/` ou a area autenticada deve ficar em `/admin` novamente?
5. Precisamos registrar eventos de login e logout em `check_events`?

## Recomendacao objetiva

Para a primeira entrega, o melhor custo-beneficio e:

- uma unica credencial administrativa configurada via ambiente;
- sessao por cookie HttpOnly;
- tela de login simples no frontend atual;
- protecao de todas as rotas `/api/admin`, inclusive SSE;
- sem alterar o fluxo do ESP32 nem o modelo `users`.

Isso resolve a exposicao da chave fixa no frontend sem expandir desnecessariamente o escopo.