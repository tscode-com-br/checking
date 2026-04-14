# Contexto para Login Simples no Admin

> Status em 2026-03-29: a implementação por sessão já foi concluída, e o fallback legado por `x-admin-key`/`admin_key` foi removido da aplicação. As seções abaixo registram o estado anterior analisado antes da implementação.

## Objetivo deste documento

Consolidar o estado atual da API e do website administrativo para preparar a introdução de um login simples, com o menor impacto possível no fluxo existente do sistema.

## Arquitetura atual

### Backend

- A aplicação é uma API FastAPI que também serve o frontend administrativo estático.
- As rotas de API ficam em `sistema/app/routers`.
- O frontend admin é servido pelo próprio backend a partir de `sistema/app/static/admin`.
- A raiz `/` entrega a interface admin estaticamente, e `/admin` apenas redireciona para a raiz.

### Frontend

- O admin é uma SPA simples em HTML + CSS + JavaScript puro, sem framework.
- Todo o estado do frontend é mantido em memória no navegador.
- A comunicação com o backend acontece via `fetch()` e `EventSource`.

## Fluxos de negócio já implementados

### Fluxo do dispositivo

- O ESP32 autentica apenas com `device_shared_key`.
- `POST /api/device/heartbeat` registra sinal de vida do dispositivo.
- `POST /api/scan` recebe leituras RFID, aplica regras de negócio e enfileira o envio ao Microsoft Forms.

### Fluxo administrativo

- O admin lista usuários em check-in e check-out.
- O admin cadastra usuários a partir de pendências de RFID desconhecido.
- O admin remove pendências e usuários.
- O admin visualiza eventos operacionais.
- O admin arquiva logs de eventos em CSV e faz download dos arquivos salvos.
- O admin recebe atualizações em tempo real por Server-Sent Events para refrescar tabelas.

## Modelo de segurança atual

### O que existe hoje

- O backend protege as rotas administrativas com uma única chave estática em `settings.admin_api_key`.
- Essa chave é validada pelo header `x-admin-key`.
- O stream SSE usa a mesma chave, mas via query string `admin_key`.
- O frontend embute a chave padrão diretamente no JavaScript como constante `DEFAULT_ADMIN_KEY`.

### O que não existe hoje

- Não existe tabela de administradores.
- Não existe login, logout, sessão ou cookie.
- Não existe token Bearer, JWT ou refresh token.
- Não existe middleware de autenticação ou autorização por perfil.
- Não existe tela de login separada.
- Não existe persistência segura de identidade do admin no navegador.

## Implicações práticas para o login

### Pontos favoráveis

- O escopo de autenticação está concentrado em `/api/admin`, o que facilita trocar a dependência atual por uma verificação de sessão.
- O frontend é pequeno e centraliza as chamadas em `adminHeaders()` e `fetchJson()`, então a troca de estratégia de autenticação pode ser feita em poucos pontos.
- Não há app mobile ou múltiplos clientes administrativos para compatibilizar.

### Pontos de atenção

- O SSE atual depende de query string com segredo; com login simples, isso deve migrar para cookie de sessão ou outro mecanismo compatível com `EventSource`.
- Como o admin é servido em `/`, qualquer tela de login simples precisa conviver com o site estático existente ou substituir o bootstrap atual.
- O frontend hoje assume acesso imediato ao carregar a página; não há estado intermediário de usuário não autenticado.
- O projeto não possui entidade de usuário administrativo, então será necessário decidir entre credenciais únicas via `.env` ou tabela `admin_users`.

## Menor caminho para um login simples

### Opção recomendada para a primeira iteração

Implementar autenticação por sessão baseada em cookie HttpOnly usando uma única credencial administrativa definida em ambiente.

### Motivos

- Mantém o sistema simples.
- Evita expor segredo fixo no JavaScript.
- Funciona melhor com `fetch()` e com `EventSource` no mesmo domínio.
- Exige poucas mudanças de schema se a credencial ficar em `.env`.
- Permite evoluir depois para tabela de administradores sem reescrever toda a proteção.

### Desenho sugerido

1. Criar endpoint `POST /api/admin/login` que valida `username` e `password` vindos do formulário.
2. Ao autenticar, gerar uma sessão assinada e armazená-la em cookie HttpOnly, `SameSite=Lax`.
3. Criar endpoint `POST /api/admin/logout` para invalidar a sessão.
4. Criar endpoint `GET /api/admin/session` para o frontend descobrir se há usuário autenticado.
5. Substituir `require_admin_key()` por `require_admin_session()` em todas as rotas `/api/admin`.
6. Adaptar o SSE para validar sessão por cookie, removendo `admin_key` da query string.
7. No frontend, exibir a tela de login antes do carregamento das abas quando não houver sessão válida.

## Estrutura de dados atual relevante para o admin

### Tabelas existentes

- `users`: usuários operacionais com RFID, chave, nome, projeto, local e estado de presença.
- `pending_registrations`: RFIDs ainda não cadastrados.
- `check_events`: trilha de auditoria do sistema.
- `device_heartbeats`: sinais de vida enviados pela ESP32.
- `forms_submissions`: fila persistida de envio ao Microsoft Forms.

### Observação importante

- A tabela `users` representa pessoas lidas pelo RFID, não administradores do sistema.
- Reutilizar `users` para login do admin seria conceitualmente incorreto e criaria acoplamento entre operação física e acesso administrativo.

## Impacto esperado por camada

### Backend

- Novo módulo de autenticação administrativa.
- Novos endpoints de login, logout e sessão.
- Nova dependência FastAPI para validar sessão.
- Ajuste do endpoint SSE.

### Frontend

- Nova tela ou estado de login.
- Bootstrap inicial condicionado a sessão válida.
- Remoção da constante `DEFAULT_ADMIN_KEY` e do envio de `x-admin-key`.
- Tratamento centralizado de `401` para redirecionar ao login.

### Testes

- Atualizar testes que hoje acessam `/api/admin/*` com `x-admin-key`.
- Adicionar testes de login bem-sucedido, login inválido, acesso sem sessão e logout.
- Adicionar teste do stream SSE autenticado.

## Decisões que ainda precisamos tomar

1. A primeira versão usará credencial única no `.env` ou tabela de administradores?
2. O login precisa de um único usuário admin ou de múltiplos usuários?
3. A sessão pode ser stateless assinada ou precisamos de invalidação no servidor?
4. O admin deve continuar sendo servido em `/` ou a área autenticada deve ficar em `/admin` novamente?
5. Precisamos registrar eventos de login e logout em `check_events`?

## Recomendação objetiva

Para a primeira entrega, o melhor custo-benefício é:

- uma única credencial administrativa configurada via ambiente;
- sessão por cookie HttpOnly;
- tela de login simples no frontend atual;
- proteção de todas as rotas `/api/admin`, inclusive SSE;
- sem alterar o fluxo do ESP32 nem o modelo `users`.

Isso resolve a exposição da chave fixa no frontend sem expandir desnecessariamente o escopo.
