# Plano Detalhado e Minucioso de Conversão da Web Application `sistema/app/static/check` para Aplicativo Android Nativo em Kotlin

Data: 2026-04-25

## Introdução

Este documento foi elaborado para funcionar como guia completo, fechado e rastreável da conversão da web application `sistema/app/static/check` para um aplicativo Android nativo em Kotlin, sem alterar a aplicação web original e sem desviar dos contratos já existentes no backend. O plano não se limita a descrever a ideia geral da migração: ele define a fonte de verdade funcional e visual, fixa as premissas que não podem ser violadas, identifica os arquivos e contratos que precisam ser respeitados, descreve os riscos técnicos relevantes, estabelece a estratégia de implementação e organiza a execução em fases sucessivas até que o aplicativo esteja efetivamente pronto para rodar.

Ao longo do texto, o plano faz, de forma integrada, todas as seguintes funções:

- delimita exatamente o que deve ser migrado e o que não pode ser alterado;
- determina que a SPA atual é a única referência de comportamento e de layout;
- identifica os endpoints `/api/web/*` que o app Kotlin deverá reutilizar sem criar contratos paralelos;
- consolida as regras de autenticação, histórico, localização, check-in/check-out automático, transporte, SSE, persistência local e ciclo de vida da interface;
- aponta o que pode ser reaproveitado da base existente em `checking_kotlin` e o que deve ser reconstruído;
- define critérios objetivos de paridade visual e funcional;
- organiza a implementação em fases, com objetivo, atividades e critério de conclusão em cada etapa;
- transforma a migração em processo auditável, e não em uma sequência informal de alterações.

Além do plano descritivo, a checklist final foi incluída para funcionar como instrumento operacional de controle e segurança. Ela não repete o plano de forma decorativa; ela converte o conteúdo do plano em itens verificáveis de execução, revisão e aceite. Na prática, essa checklist serve para:

- impedir que alguma frente crítica da migração seja esquecida;
- permitir acompanhamento detalhado do trabalho por etapa, arquivo, fluxo e contrato;
- garantir cobertura de governança, baseline visual, sessão HTTP, UI, localização, transporte, testes, validação manual e documentação;
- reduzir o risco de retrabalho, lacunas de escopo e regressões funcionais;
- apoiar a conferência final de que o app Kotlin realmente reproduz a experiência central da SPA;
- estabelecer um critério seguro de encerramento, deixando claro o que precisa estar concluído para que o aplicativo possa ser considerado pronto para rodar.

Em conjunto, o plano e a checklist formam um pacote único de condução da migração: o plano explica com profundidade o que deve ser feito, por que deve ser feito e em que ordem deve acontecer; a checklist garante que cada parte desse plano seja efetivamente executada, validada e encerrada com segurança.

## 1. Objetivo

Transformar a web application localizada em `sistema/app/static/check` em um aplicativo Android nativo escrito em Kotlin, preservando rigorosamente:

- as mesmas tarefas executadas hoje pela aplicação web;
- os mesmos endpoints de API atualmente consumidos pela aplicação web;
- o mesmo comportamento funcional, inclusive estados intermediários, textos, bloqueios, regras e exceções;
- o layout visual com paridade máxima, tomando a SPA atual como fonte de verdade de interface.

Este plano parte das seguintes constatações verificadas no repositório:

- a aplicação web alvo está concentrada em `index.html`, `styles.css`, `app.js`, `automatic-activities.js` e `web-client-state.js` dentro de `sistema/app/static/check`;
- a fonte de verdade dos contratos web está em `sistema/app/routers/web_check.py` e `sistema/app/schemas.py`;
- existe um aplicativo Android nativo já iniciado em `checking_kotlin`, com arquitetura Kotlin/Compose/Hilt/Room/DataStore, que deve ser tratado como base preferencial de reaproveitamento técnico, mas não como fonte de verdade funcional;
- a fonte de verdade funcional e visual desta conversão é exclusivamente a SPA em `sistema/app/static/check`.

## 2. Premissas Imutáveis

As regras abaixo não devem ser flexibilizadas durante a execução:

- a aplicação web atual não deve ser alterada para acomodar o app Kotlin;
- o backend não deve receber novos endpoints para atender esta conversão;
- o app Kotlin deve consumir os mesmos endpoints `/api/web/*` usados pela SPA;
- o app Kotlin não deve substituir esses contratos por `/api/mobile/*`, `/api/scan`, `/api/provider/*` ou qualquer contrato alternativo;
- o app Kotlin não deve depender do código Flutter como fonte de verdade de regra de negócio;
- qualquer funcionalidade existente hoje em `checking_kotlin` que extrapole a SPA deve ser ocultada, desativada por flag ou removida da entrega inicial de paridade;
- a entrega inicial deve buscar paridade funcional e visual com a SPA antes de qualquer expansão nativa;
- o comportamento de sessão por cookie, hoje usado pela SPA, deve ser mantido no app Kotlin;
- os textos visíveis ao usuário devem seguir exatamente a mesma redação da SPA, salvo correções ortográficas previamente aprovadas;
- a navegação principal deve permanecer orientada ao modo retrato, reproduzindo o comportamento da aplicação web.

## 3. Fontes de Verdade Confirmadas

Os arquivos abaixo foram verificados e devem fundamentar a implementação:

- SPA alvo:
  - `sistema/app/static/check/index.html`
  - `sistema/app/static/check/styles.css`
  - `sistema/app/static/check/app.js`
  - `sistema/app/static/check/automatic-activities.js`
  - `sistema/app/static/check/web-client-state.js`
- Contratos backend usados pela SPA:
  - `sistema/app/routers/web_check.py`
  - `sistema/app/schemas.py`
- Regras operacionais documentadas:
  - `docs/regras_checkin_checkout_webapp.txt`
- Testes de comportamento e layout da SPA:
  - `tests/check_registration_widget.test.js`
  - `tests/check_user_location_ui.test.js`
  - `tests/check_auth_transport_ui.test.js`
  - `tests/check_automatic_activities_layout.test.js`
  - `tests/check_portrait_lock.test.js`
  - `tests/check_history_latest_activity_ui.test.js`
  - `tests/check_responsive_layout.test.js`
  - `tests/check_transport_layout.test.js`
  - `tests/check_transport_request_history.test.js`
- Base Kotlin existente para reaproveitamento técnico:
  - `checking_kotlin/README.md`
  - `checking_kotlin/app/build.gradle.kts`
  - `checking_kotlin/app/src/main/AndroidManifest.xml`
  - `checking_kotlin/app/src/main/java/com/br/checkingnative/MainActivity.kt`
  - `checking_kotlin/app/src/main/java/com/br/checkingnative/data/remote/WebCheckApiService.kt`
  - `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/checking/*`

## 4. Diagnóstico Consolidado do Estado Atual

### 4.1. O que a SPA realmente faz hoje

A SPA não é apenas um formulário de check-in/check-out. Ela já implementa uma experiência completa com:

- shell visual com cabeçalho, logotipo, fundo com marca d’água e card central responsivo;
- bloqueio de uso em paisagem com overlay específico e tentativa de trava em retrato;
- histórico resumido com destaque visual para a atividade mais recente;
- área de notificações em duas linhas, com tonalidades distintas por estado;
- captura de geolocalização sob demanda com atualização manual e atualização em eventos de ciclo de vida;
- autenticação por chave e senha com três estados distintos:
  - chave inexistente;
  - chave existente sem senha;
  - chave existente com senha;
- modal de cadastro de senha;
- modal de autocadastro de usuário;
- seleção de ação de registro;
- seleção de informe;
- seleção de projeto;
- seleção manual de local quando aplicável;
- modo de atividades automáticas condicionado à disponibilidade de permissão de localização;
- chamadas de atualização de projeto;
- módulo completo de transporte com tela dedicada, editor de endereço, construtor de solicitação, histórico, detalhe e atualização em tempo real por SSE;
- persistência local por `chave` para senha, preferências do usuário e estado local do histórico de transporte;
- uso de sessão autenticada via cookie para todos os endpoints protegidos.

### 4.2. O que a SPA não faz e não deve ser adicionado à entrega inicial

Com base na leitura direta do código da SPA, não fazem parte da fonte de verdade desta migração:

- rastreamento contínuo por `watchPosition`;
- serviço de localização em segundo plano como comportamento obrigatório;
- configuração de OEM auto-start, bateria ou foreground service como parte da UX principal;
- fluxos móveis baseados em `/api/mobile/*`;
- comportamentos herdados exclusivamente do app Flutter.

Isso significa que o app Kotlin pode até possuir infraestrutura nativa mais poderosa, mas a entrega inicial deve se limitar ao que a SPA faz hoje.

### 4.3. Estado relevante do `checking_kotlin`

O projeto `checking_kotlin` já oferece base técnica útil:

- aplicativo Android com `applicationId = "com.br.checkingnative"`;
- stack com Kotlin, Jetpack Compose, Hilt, Room e DataStore;
- `WebCheckApiService` já apontando para contratos `/api/web/*`;
- `MainActivity.kt` e `ui/checking/*` já estruturados com ViewModel e callbacks;
- manifesto Android com permissões sensíveis já declaradas;
- comandos de build já definidos no Gradle.

Contudo, também há sinais claros de divergência em relação à SPA:

- a base Kotlin atual carrega comportamentos de app móvel mais amplo, oriundos da migração a partir do Flutter;
- `MainActivity.kt` já expõe fluxos de permissões, monitoramento e automação nativa que não existem na SPA;
- a UI atual do app Kotlin não pode ser tratada como referência visual;
- o objetivo aqui não é aproveitar a UI existente “como está”, mas aproveitar a infraestrutura e reconstruir a interface a partir da SPA.

## 5. Escopo Funcional Obrigatório de Paridade

O aplicativo Kotlin deverá reproduzir, no mínimo, os seguintes blocos funcionais.

### 5.1. Estrutura visual principal

- cabeçalho verde com logotipo e texto `Checking`;
- fundo com gradiente claro e marca d’água da Petrobras ao centro;
- card principal centralizado com largura responsiva;
- comportamento mobile-first;
- uso prioritário em retrato;
- overlay de paisagem com os mesmos textos da SPA.

### 5.2. Card de histórico

- exibir `Último Check-In` e `Último Check-Out`;
- renderizar `--` quando ausente;
- aplicar destaque visual em verde para a atividade mais recente;
- manter a lógica que calcula qual atividade é a mais recente;
- derivar automaticamente a ação sugerida a partir do histórico, como a SPA já faz.

### 5.3. Card de notificação

- manter duas linhas independentes de texto;
- preservar a semântica de tons `success`, `error`, `info`, `warning` e `neutral`;
- aplicar a mesma lógica de quebra de mensagem em linha primária e secundária;
- preservar mensagens do backend sem reescrevê-las arbitrariamente.

### 5.4. Card de localização

- exibir rótulo `Local`;
- mostrar valor textual da localização capturada;
- mostrar precisão;
- botão de atualização manual com estado de carregamento;
- estados de localização compatíveis com a SPA:
  - `matched`;
  - `accuracy_too_low`;
  - `outside_workplace`;
  - `not_in_known_location`;
  - `no_known_locations`.

### 5.5. Identificação e senha

- campo `Chave` com no máximo 4 caracteres;
- campo `Senha`;
- botão lateral com rótulo dinâmico:
  - `Alterar`;
  - `Senha?`;
  - `Chave?`;
  - `Aguarde` quando aplicável;
- restauração dos valores por `chave` já usados anteriormente;
- verificação automática do status da chave;
- verificação silenciosa da senha restaurada;
- travamento da interface enquanto o usuário não estiver autenticado.

### 5.6. Modal de senha

- modo completo de alteração de senha quando a chave já possui senha;
- modo reduzido de cadastro de senha quando a chave existe sem senha;
- ocultação do campo `Senha Antiga` no modo reduzido, preservando o layout equivalente ao webapp;
- mesmo texto dos botões `Voltar` e `Alterar`;
- validação de confirmação de senha;
- envio para os mesmos endpoints da SPA.

### 5.7. Modal de autocadastro

- campos obrigatórios: `Chave`, `Nome Completo`, `Projeto`, `Senha`, `Confirma Senha`;
- campo opcional: `E-Mail`;
- não incluir endereço ou ZIP no cadastro, porque a SPA não inclui;
- após cadastro bem-sucedido, autenticar a sessão como a SPA já faz.

### 5.8. Grupo de registro

- legenda com `Atividades Automáticas` acima de `Registro`;
- opções `Check-In`, `Check-Out` e botão de transporte;
- manter o rótulo `Em breve` se este for o texto atual da SPA para o botão principal no shell;
- preservação de estados desabilitados quando a interface estiver ocupada.

### 5.9. Grupo `Informe`

- opções `Normal` e `Retroativo`;
- mesma ordem;
- mesmo layout em duas colunas;
- mesma lógica de bloqueio e habilitação.

### 5.10. Projeto e local manual

- seletor de projeto carregado por `/api/web/projects`;
- atualização do projeto por `/api/web/project`;
- seletor de local carregado por `/api/web/check/locations`;
- ocultação do campo de local manual quando a permissão GPS estiver ativa, conforme a SPA;
- ocultação do projeto quando `Atividades Automáticas` estiver ligada, conforme a SPA.

### 5.11. Botão principal `Registrar`

- mesmo texto;
- mesmo estado de bloqueio durante submissão;
- mesmo fluxo de atualização do histórico após retorno da API.

### 5.12. Atividades automáticas

- só podem aparecer quando a permissão de localização estiver disponível ou já houver flag persistida equivalente;
- devem ser desmarcadas e ocultadas quando a permissão não estiver disponível;
- devem executar apenas as regras presentes na SPA e em `docs/regras_checkin_checkout_webapp.txt`;
- não devem introduzir automações extras oriundas do Flutter ou do app Kotlin atual.

### 5.13. Tela de transporte

- abertura em tela dedicada dentro do aplicativo;
- cabeçalho próprio com botão de voltar;
- resumo do endereço;
- editor de endereço;
- construtor de solicitação para três modalidades:
  - `regular`;
  - `weekend`;
  - `extra`;
- histórico de solicitações ocupando o espaço restante da tela;
- widget de detalhe da solicitação;
- atualização em tempo real enquanto a tela estiver aberta;
- fallback de polling periódico.

### 5.14. Histórico de transporte com estado local

- persistência por `chave` do estado local em equivalente ao `checking.web.transport.local-state.by-chave`;
- listas locais de `dismissed_request_ids` e `realized_request_ids`;
- normalização do status `realized` vindo da API para `confirmed` no tratamento interno local, como a SPA faz;
- normalização de itens inativos para `cancelled`, exceto onde houver override local de `realized`;
- permitir dismiss apenas em cartões `realized` ou `cancelled`;
- manter cartões `pending` e `confirmed` sempre visíveis;
- ação local `Realizado` após o horário de partida, sem depender de novo contrato backend;
- não limpar o estado local ao fechar a tela de transporte;
- limpar esse estado apenas quando o estado protegido do app for realmente resetado, como no logout.

### 5.15. Ciclo de vida e atualização de tela

- reproduzir o comportamento de atualizar dados ao abrir a aplicação;
- reproduzir atualização ao retornar ao primeiro plano;
- reproduzir atualização ao recuperar foco quando aplicável;
- manter sincronização de medidas visuais e layout em mudanças de viewport/orientação;
- tratar perda de sessão com o mesmo rigor da SPA.

## 6. Regras de Negócio Críticas a Preservar

### 6.1. Autenticação pública por chave e senha

Com base na implementação atual:

- `GET /api/web/auth/status` é público e informa se a `chave` existe, se possui senha e se a sessão atual está autenticada para ela;
- se a chave não existir, o fluxo correto é oferecer autocadastro pelo endpoint `/api/web/auth/register-user`;
- se a chave existir sem senha, o fluxo correto é oferecer cadastro de senha via `/api/web/auth/register-password`;
- se a chave já possuir senha, o fluxo correto é autenticação via `/api/web/auth/login` e posterior possibilidade de troca via `/api/web/auth/change-password`;
- a interface só deve se liberar após autenticação válida da senha atual, não bastando cookie antigo residual;
- a senha é persistida na SPA por `chave`, e o app Kotlin deverá preservar a mesma experiência, mas usando armazenamento nativo seguro.

### 6.2. Regras de check-in/check-out automático

As cinco situações descritas em `docs/regras_checkin_checkout_webapp.txt` devem ser tratadas como cenários obrigatórios de aceite. Em resumo:

- se a última ação foi `checkin` e o usuário estiver na `Zona de CheckOut` ou distante o suficiente do trabalho, deve ocorrer `checkout` automático;
- se a última ação foi `checkout` e o usuário continuar em situação de saída, nada deve acontecer;
- se a última ação foi `checkout` e o usuário estiver em local conhecido de trabalho ou próximo do trabalho, deve ocorrer `checkin` automático;
- se a última ação foi `checkin` e o usuário mudou de local conhecido de trabalho, deve ocorrer novo `checkin` para atualizar o local;
- se a última ação foi `checkin` e o usuário estiver próximo do trabalho, mas sem correspondência exata de local, nenhuma ação deve ser feita, apenas atualização visual para `Localização não Cadastrada`.

### 6.3. Regras de transporte que não podem ser regredidas

- o acesso ao transporte no fluxo web não depende mais de check-in no mesmo dia;
- o histórico deve listar todas as solicitações relevantes em ordem correta;
- quando uma solicitação antiga deixa de ser ativa, a interface final do usuário deve refletir o estado adequado, inclusive `cancelled`;
- a conexão SSE do transporte deve existir apenas enquanto a tela de transporte estiver aberta;
- o polling de 10 segundos continua como fallback;
- o debounce de atualização em tempo real deve ser preservado.

### 6.4. Alerta sobre tolerância de localização

Existe um descompasso conhecido no backend: a geometria de localização ainda rejeita `tolerance_meters < 1` em parte do serviço geométrico, embora a API/admin aceitem tolerância zero. O plano de implementação deve prever validação específica para qualquer funcionalidade nativa que dependa da interpretação geométrica exata de tolerância zero.

## 7. Matriz Exata de Endpoints a Reutilizar

Os contratos abaixo foram confirmados em `sistema/app/routers/web_check.py` e devem ser mantidos exatamente.

| Endpoint | Método | Obrigatoriedade | Observações principais |
| --- | --- | --- | --- |
| `/api/web/auth/status?chave=...` | `GET` | obrigatório | público; informa `found`, `has_password`, `authenticated`, `message` |
| `/api/web/auth/register-password` | `POST` | obrigatório | cadastra senha para chave existente sem senha |
| `/api/web/auth/register-user` | `POST` | obrigatório | autocadastro; autentica a sessão após sucesso |
| `/api/web/auth/login` | `POST` | obrigatório | autenticação por chave e senha |
| `/api/web/auth/logout` | `POST` | obrigatório | encerra sessão web |
| `/api/web/auth/change-password` | `POST` | obrigatório | troca a senha existente |
| `/api/web/projects` | `GET` | obrigatório | retorna lista de projetos |
| `/api/web/project` | `PUT` | obrigatório | atualiza projeto do usuário autenticado |
| `/api/web/transport/state?chave=...` | `GET` | obrigatório | estado do transporte para a chave autenticada |
| `/api/web/transport/stream?chave=...` | `GET` | obrigatório | SSE, somente enquanto a tela de transporte estiver aberta |
| `/api/web/transport/address` | `POST` | obrigatório | salva endereço |
| `/api/web/transport/vehicle-request` | `POST` | obrigatório | endpoint principal de criação de solicitação |
| `/api/web/transport/request` | `POST` | compatibilidade | alias mantido no backend; o app deve preferir `vehicle-request` |
| `/api/web/transport/cancel` | `POST` | obrigatório | cancela solicitação ativa do usuário |
| `/api/web/transport/acknowledge` | `POST` | obrigatório | registra ciência da confirmação |
| `/api/web/check/state?chave=...` | `GET` | obrigatório | histórico resumido e estado atual |
| `/api/web/check/locations` | `GET` | obrigatório | lista de locais filtrada por projeto do usuário |
| `/api/web/check/location` | `POST` | obrigatório | resolve local a partir de latitude/longitude/precisão |
| `/api/web/check` | `POST` | obrigatório | submissão manual de check-in/check-out |

### 7.1. Regras de consumo desses endpoints no app Kotlin

- manter sessão por cookie, com `CookieJar` persistente ou mecanismo equivalente;
- compartilhar o mesmo armazenamento de cookie entre chamadas HTTP comuns e SSE;
- tratar `401` como sessão inválida ou expirada e retornar a UI ao estado bloqueado;
- não introduzir autenticação paralela por token;
- manter `Content-Type: application/json` e corpo JSON compatível com os schemas existentes;
- utilizar a base URL configurada em `CheckingPresetConfig`, sem hardcode espalhado pela UI.

## 8. Estratégia Técnica Recomendada

### 8.1. Estratégia-base

A estratégia mais eficiente não é iniciar um novo app do zero. O caminho recomendado é:

- usar `checking_kotlin` como base de implementação;
- criar uma linha de trabalho focada em paridade web, preferencialmente em branch dedicada;
- tratar a infraestrutura de rede, DI, persistência e build já existentes como reaproveitáveis;
- reconstruir a interface e a orquestração a partir da SPA;
- isolar ou esconder tudo o que veio da migração Flutter e não pertence ao escopo da SPA.

### 8.2. Abordagem de UI recomendada

Continuar em Jetpack Compose é aceitável e recomendado, desde que sejam obedecidas as seguintes condições:

- não usar componentes Material com aparência padrão quando isso quebrar a fidelidade visual;
- criar tokens de design explícitos equivalentes aos valores da SPA;
- controlar manualmente padding, borda, raio, tipografia, sombras, estados e tamanhos;
- validar por screenshot diff e inspeção visual em dispositivo alvo;
- criar componentes dedicados para espelhar os blocos da SPA, em vez de adaptar componentes existentes de forma improvisada.

### 8.3. Observação crítica sobre tipografia

O CSS da SPA usa `"Segoe UI", Tahoma, Geneva, Verdana, sans-serif`. `Segoe UI` é uma fonte proprietária e, em regra, não deve ser redistribuída dentro do APK sem licença apropriada. Portanto, a Fase 0 deve fechar uma decisão explícita:

- obter licença formal para empacotar a mesma fonte;
- aceitar uma fonte metrically compatible aprovada por screenshot diff;
- ou redefinir o critério de “absolutamente idêntico” como paridade visual aprovada por comparação de capturas.

Sem essa definição, a meta de identidade visual total fica tecnicamente incompleta.

## 9. Plano de Execução por Fases

## Fase 0. Congelamento do Baseline e Critérios de Aceite

Objetivo: impedir ambiguidade sobre o que deve ser copiado e como a paridade será julgada.

Atividades:

- declarar formalmente que a fonte de verdade funcional e visual é `sistema/app/static/check`;
- congelar uma revisão exata da SPA como baseline;
- gerar capturas de tela da SPA nos estados principais em viewport de referência;
- documentar textos, cores, dimensões, espaçamentos, estados e fluxos obrigatórios;
- definir os dispositivos-alvo de validação visual, por exemplo `Pixel 7` em retrato;
- decidir o tratamento da tipografia, conforme a restrição de licença mencionada acima;
- declarar que o critério de pronto será baseado em paridade de fluxo, contrato e tela, e não apenas em “aparência parecida”.

Artefatos de saída:

- checklist oficial de telas/estados da SPA;
- pacote de screenshots baseline;
- documento de aceite visual;
- decisão formal sobre tipografia.

Critério de conclusão:

- nenhuma equipe envolvida pode alegar dúvida sobre o que copiar.

## Fase 1. Auditoria de Lacunas entre SPA e `checking_kotlin`

Objetivo: transformar o app Kotlin atual em mapa de reaproveitamento, não em fonte de improviso.

Atividades:

- auditar `WebCheckApiService.kt` endpoint por endpoint, método por método;
- auditar `MainActivity.kt`, `CheckingApp.kt`, `CheckingController.kt`, `CheckingUiState.kt` e `CheckingViewModel.kt` para identificar o que já é útil;
- separar o que já existe em três grupos:
  - reaproveitar sem alteração estrutural;
  - reaproveitar com adaptação;
  - ocultar ou remover da entrega inicial;
- marcar explicitamente recursos nativos que extrapolam a SPA, como monitoramento avançado, configurações extras e UX móvel ampliada;
- produzir uma matriz de gap `SPA -> Kotlin atual -> ação necessária`.

Artefatos de saída:

- matriz de lacunas;
- lista de arquivos Kotlin a ajustar;
- lista de arquivos Kotlin a congelar ou esconder temporariamente.

Critério de conclusão:

- o time sabe exatamente onde reaproveitar e onde reconstruir.

## Fase 2. Estabilização de Contratos e Sessão HTTP

Objetivo: garantir que o app Kotlin fale exatamente com a mesma API da SPA, sem desvios.

Atividades:

- validar `CheckingPresetConfig.kt` como ponto único de base URL;
- garantir que `WebCheckApiService.kt` use os mesmos paths confirmados em `web_check.py`;
- corrigir qualquer divergência de método HTTP, por exemplo `PUT /api/web/project`;
- implementar ou validar `CookieJar` persistente para sessão web;
- garantir que login, cadastro de senha, cadastro de usuário, troca de senha e logout compartilhem a mesma sessão;
- garantir que o cliente SSE use o mesmo contexto de cookies da sessão HTTP;
- padronizar o tratamento de `401`, `404`, `409` e `422` de acordo com a SPA;
- criar testes unitários ou de integração apenas para contratos HTTP, sem ainda discutir UI.

Arquivos preferenciais de trabalho:

- `checking_kotlin/app/src/main/java/com/br/checkingnative/core/config/CheckingPresetConfig.kt`
- `checking_kotlin/app/src/main/java/com/br/checkingnative/data/remote/WebCheckApiService.kt`
- `checking_kotlin/app/src/main/java/com/br/checkingnative/data/preferences/*`
- `checking_kotlin/app/src/main/java/com/br/checkingnative/core/*`

Critério de conclusão:

- todas as chamadas do app Kotlin correspondem 1:1 aos contratos `/api/web/*` usados pela SPA.

## Fase 3. Especificação Visual de Paridade

Objetivo: converter a aparência da SPA em tokens nativos verificáveis.

Atividades:

- extrair as variáveis CSS principais da SPA;
- traduzir as dimensões do CSS para tokens Compose testáveis;
- preservar, no mínimo, estes elementos já confirmados:
  - `--header-height: 64px`;
  - `--card-max-width: 680px`, com expansão para `760px` e `920px` em breakpoints maiores;
  - `--control-height: clamp(42px, 5.4vh, 50px)`;
  - `--card-radius: clamp(16px, 2vw, 22px)`;
  - gradiente de fundo claro;
  - cabeçalho `#0f766e`;
  - marca d’água Petrobras com opacidade baixa;
  - estados de sucesso, erro, alerta e informação;
  - card de histórico com moldura verde para a atividade mais recente;
  - tela de transporte ocupando toda a altura útil do viewport;
  - chips de dias compactos no construtor de transporte;
- reproduzir a lógica de viewport dinâmico e safe areas de forma equivalente no Android;
- preparar screenshots comparativas lado a lado.

Arquivos recomendados para criação ou ajuste:

- `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/theme/*`
- novos composables específicos para shell, cards e modais da SPA

Critério de conclusão:

- o app Kotlin exibe a estrutura principal visualmente indistinguível da SPA nos estados baseline.

## Fase 4. Construção do Shell Principal do App

Objetivo: espelhar a estrutura estática da SPA antes de plugar todos os fluxos.

Atividades:

- montar cabeçalho com logo e texto;
- montar fundo com gradiente e watermark;
- criar card principal com responsividade equivalente;
- criar seção de histórico;
- criar seção de notificação;
- criar seção de localização;
- criar linha de autenticação `Chave` + `Senha` + botão lateral;
- criar grupo `Registro` com `Atividades Automáticas` na mesma ordem visual da SPA;
- criar grupo `Informe`;
- criar linha `Projeto` + `Local`;
- criar botão principal `Registrar`;
- montar overlay de paisagem e esconder o chrome principal quando necessário;
- replicar alturas, lacunas, cantos arredondados, sombras e estados de habilitação.

Critério de conclusão:

- o app já possui um shell navegável e fiel à SPA, ainda que alguns botões estejam inicialmente plugados com stubs controlados.

## Fase 5. Fluxo de Identificação, Sessão e Desbloqueio da Tela

Objetivo: reproduzir integralmente o comportamento de bloqueio inicial e desbloqueio por senha.

Atividades:

- implementar estado inicial bloqueado;
- disparar `GET /api/web/auth/status` ao resolver a `chave`;
- persistir a última `chave` usada;
- persistir senha por `chave` usando armazenamento seguro nativo;
- restaurar senha ao voltar para a mesma `chave`;
- disparar verificação automática com a senha restaurada;
- reproduzir os três estados do botão lateral:
  - `Chave?` quando a chave não existir;
  - `Senha?` quando a chave existir sem senha;
  - `Alterar` quando a chave já possuir senha;
- aplicar destaque visual de atenção nos campos de autenticação quando a interface exigir ajuda do usuário;
- implementar restauração de valores limpos acidentalmente ao sair do campo, espelhando o comportamento existente no webapp;
- garantir que cookies antigos não liberem a UI sem validação coerente da senha atual.

Critério de conclusão:

- o shell principal só libera funcionalidades protegidas quando a autenticação reproduz exatamente o fluxo da SPA.

## Fase 6. Modal de Senha e Modal de Autocadastro

Objetivo: fechar os dois diálogos críticos do fluxo de entrada.

Atividades:

- implementar modal de senha com dois modos:
  - cadastro de senha;
  - alteração de senha;
- no modo de cadastro, ocultar `Senha Antiga`, preservando o comportamento visual equivalente ao web;
- implementar modal de autocadastro com os mesmos campos e a mesma ordem da SPA;
- plugar `POST /api/web/auth/register-password`;
- plugar `POST /api/web/auth/register-user`;
- plugar `POST /api/web/auth/change-password`;
- após sucesso, atualizar sessão e destravar a UI;
- manter os textos dos botões `Voltar`, `Alterar` e `Enviar` exatamente como a SPA usa;
- reproduzir estados de carregamento `Aguarde` e classes de atenção equivalentes.

Critério de conclusão:

- os dois diálogos funcionam com a mesma semântica, mesma ordem de campos e mesmas transições de estado da SPA.

## Fase 7. Histórico, Projeto, Localização Manual e Submissão Manual de Check

Objetivo: colocar o fluxo principal de trabalho em operação com paridade de contrato e tela.

Atividades:

- plugar `GET /api/web/check/state` e renderizar histórico;
- implementar destaque do item de atividade mais recente;
- plugar `GET /api/web/projects` e popular o seletor;
- plugar `PUT /api/web/project` ao trocar o projeto;
- plugar `GET /api/web/check/locations` para preencher o seletor de local manual;
- plugar `POST /api/web/check/location` para resolução de local por coordenadas;
- plugar `POST /api/web/check` para submissão manual;
- garantir atualização imediata do histórico após submissão bem-sucedida;
- preservar os mesmos estados de erro da SPA quando o backend responder com falha;
- manter os mesmos valores e semântica dos rádios `Check-In`, `Check-Out`, `Normal` e `Retroativo`.

Critério de conclusão:

- o usuário já consegue autenticar, selecionar projeto, resolver localização, registrar check-in/check-out e ver o histórico atualizado como no webapp.

## Fase 8. Geolocalização Sob Demanda e Lógica de Visibilidade dos Campos

Objetivo: reproduzir a lógica web de geolocalização e visibilidade condicional dos controles.

Atividades:

- usar captura de localização sob demanda, equivalente ao `getCurrentPosition` da SPA;
- acionar atualização de localização nos momentos equivalentes ao ciclo de vida do webapp;
- esconder o campo de local manual quando a permissão GPS estiver ativa, como a SPA faz;
- esconder o campo de projeto quando `Atividades Automáticas` estiver ligado, como a SPA faz;
- atualizar os estados visuais de localização:
  - aguardando localização;
  - precisão insuficiente;
  - local identificado;
  - fora do local de trabalho;
  - localização não cadastrada;
- atualizar texto e precisão conforme a mesma lógica da SPA;
- manter a ação do botão de refresh exatamente equivalente ao webapp.

Critério de conclusão:

- o comportamento de captura, resolução e apresentação de localização é indistinguível do comportamento atual da SPA.

## Fase 9. Atividades Automáticas com Regra Estritamente Equivalente à SPA

Objetivo: reproduzir a automação existente no webapp sem adicionar automações móveis novas.

Atividades:

- implementar a disponibilidade condicional do toggle `Atividades Automáticas`;
- ocultar e limpar o toggle quando a permissão GPS não estiver disponível;
- disparar reavaliação do ciclo de vida quando a localização estiver disponível e a aplicação estiver autenticada;
- implementar as cinco situações obrigatórias de `docs/regras_checkin_checkout_webapp.txt`;
- preservar o rótulo `Desative Atividades Automáticas para registrar manualmente.` quando aplicável;
- impedir submissão manual enquanto a SPA equivalente impedir;
- não ativar, nesta fase, serviço contínuo de segundo plano se ele causar divergência com a SPA;
- se a base Kotlin atual já possuir automação em segundo plano, encapsular esse comportamento atrás de flag desativada no modo de paridade web.

Critério de conclusão:

- a automação executa apenas o que a SPA executa hoje, nem mais, nem menos.

## Fase 10. Tela de Transporte, Endereço e Construtor de Solicitação

Objetivo: migrar o módulo de transporte com fidelidade estrutural e funcional.

Atividades:

- criar tela/modal de transporte em altura útil integral, como a SPA;
- implementar cabeçalho com botão de retorno;
- exibir resumo do endereço;
- criar editor de endereço com os mesmos campos válidos;
- plugar `POST /api/web/transport/address`;
- plugar `GET /api/web/transport/state`;
- criar o construtor de solicitação com três modos:
  - `regular` com seleção de dias úteis;
  - `weekend` com seleção de sábado/domingo;
  - `extra` com seleção de data e hora;
- manter o rótulo do botão `Solicitar` e o estado `Solicitando...`;
- usar o endpoint principal `POST /api/web/transport/vehicle-request`;
- manter o alias `/api/web/transport/request` apenas como fallback compatível, se necessário;
- carregar histórico de solicitações ocupando o restante da altura da tela, como a SPA.

Critério de conclusão:

- o usuário consegue abrir transporte, editar endereço, criar solicitações e ver o estado refletido na tela com a mesma estrutura da SPA.

## Fase 11. Histórico de Transporte, Detalhe, Cancelamento, Ciência e Estado Local

Objetivo: fechar a parte mais sensível da fidelidade de transporte.

Atividades:

- renderizar os cartões de histórico na mesma hierarquia visual da SPA;
- implementar o widget de detalhe da solicitação;
- implementar `POST /api/web/transport/cancel`;
- implementar `POST /api/web/transport/acknowledge`;
- manter os mesmos rótulos de status exibidos ao usuário;
- normalizar `realized` vindo da API para `confirmed` no fluxo local, igual à SPA;
- transformar itens inativos em `cancelled` quando essa for a regra do webapp;
- persistir overrides locais por `chave`;
- permitir dismiss apenas quando o cartão estiver em `realized` ou `cancelled`;
- implementar a ação local `Realizado` após o horário elegível;
- não apagar os IDs locais ao fechar a tela;
- limpar o estado local apenas no reset real da sessão protegida.

Critério de conclusão:

- o histórico de transporte do app Kotlin reflete a mesma lógica híbrida `backend + estado local` da SPA.

## Fase 12. SSE, Polling de Fallback e Ciclo de Vida da Tela de Transporte

Objetivo: reproduzir o comportamento em tempo real da tela de transporte.

Atividades:

- implementar cliente SSE compatível com `GET /api/web/transport/stream?chave=...`;
- garantir compartilhamento de cookie de sessão com o cliente SSE;
- abrir a conexão apenas quando a tela de transporte estiver aberta;
- fechar a conexão ao sair da tela;
- manter polling periódico de fallback a cada 10 segundos;
- reproduzir o debounce de refresh em tempo real da SPA;
- tratar reconexão e keep-alive sem gerar duplicidade de estado;
- garantir que o estado em tempo real não contamine telas fora do escopo do transporte.

Critério de conclusão:

- a tela de transporte reage às mudanças do backend com o mesmo comportamento percebido pelo usuário no webapp.

## Fase 13. Ajuste Fino de Responsividade, Medidas e Estados Visuais

Objetivo: sair de “funciona” para “está igual”.

Atividades:

- medir o card principal em diferentes larguras e igualar aos breakpoints da SPA;
- ajustar tipografia, pesos e espaçamentos finos;
- ajustar bordas, raios, opacidades, sombras e fundos;
- ajustar estados visuais de loading, erro, foco, disabled, pending e attention;
- ajustar o destaque verde do histórico;
- ajustar a altura útil da tela de transporte;
- ajustar os chips de dias da semana para o mesmo footprint da SPA;
- ajustar o overlay de paisagem;
- ajustar o posicionamento de botões, cabeçalho e safe areas em aparelhos com recortes;
- revisar todos os textos visíveis, capitalização, acentuação e pontuação.

Critério de conclusão:

- a comparação lado a lado com a SPA revela apenas diferenças residuais toleradas formalmente na Fase 0.

## Fase 14. Suite Completa de Testes de Paridade

Objetivo: substituir percepção subjetiva por evidência automatizada e roteiros objetivos.

Atividades:

- criar testes unitários para as regras de autenticação, transformação de estado e normalização de transporte;
- criar testes de integração para os contratos `/api/web/*`;
- criar testes instrumentados para a UI Compose nos estados principais;
- criar testes de screenshot para as telas e diálogos equivalentes à SPA;
- transformar as regras dos testes JS já existentes em cenários Android equivalentes;
- cobrir, no mínimo, os seguintes cenários:
  - chave inexistente;
  - chave existente sem senha;
  - chave existente com senha;
  - cadastro de senha;
  - autocadastro;
  - troca de senha;
  - histórico com destaque da atividade mais recente;
  - visibilidade correta de projeto e local;
  - atividades automáticas disponíveis e indisponíveis;
  - fluxo manual de check-in;
  - fluxo manual de check-out;
  - transporte regular;
  - transporte weekend;
  - transporte extra;
  - cancelamento de solicitação;
  - ciência de confirmação;
  - `Realizado` local;
  - dismiss permitido e proibido conforme o status;
  - SSE ativo somente com a tela aberta;
  - overlay de paisagem;
  - perda de sessão com retorno ao estado bloqueado.

Critério de conclusão:

- o comportamento principal do app deixa de depender apenas de homologação manual.

## Fase 15. Preparação do Estado “Pronto para Rodar”

Objetivo: chegar a um build debug instalável, inicializável e operacionalmente validado.

Atividades:

- revisar `AndroidManifest.xml` e `MainActivity.kt` para garantir que apenas o comportamento compatível com a SPA esteja exposto na entrega;
- garantir que os assets reais estejam referenciados corretamente;
- revisar permissões realmente necessárias para a paridade da SPA;
- montar build debug estável;
- instalar no emulador e em pelo menos um dispositivo físico;
- validar autenticação, localização, check manual, automação equivalente à SPA e transporte;
- revisar logs, erros de rede, perda de sessão e restauração de estado;
- registrar um roteiro de execução local para desenvolvedor e homologador.

Critério de conclusão:

- o aplicativo compila, instala, abre e executa todos os fluxos obrigatórios de paridade com a SPA.

## 10. Mapeamento Recomendado de Arquivos Kotlin

Para evitar acoplamento desnecessário, recomenda-se o seguinte desenho de responsabilidades no app Kotlin.

### 10.1. Arquivos que devem permanecer como pontos centrais

- `checking_kotlin/app/src/main/java/com/br/checkingnative/core/config/CheckingPresetConfig.kt`
- `checking_kotlin/app/src/main/java/com/br/checkingnative/data/remote/WebCheckApiService.kt`
- `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/checking/CheckingController.kt`
- `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/checking/CheckingUiState.kt`
- `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/checking/CheckingViewModel.kt`
- `checking_kotlin/app/src/main/java/com/br/checkingnative/MainActivity.kt`

### 10.2. Estrutura recomendada de novos componentes de UI

Sugestão de decomposição para manter a fidelidade e evitar um `CheckingApp.kt` monolítico:

- `CheckWebShell.kt`
- `CheckHistoryCard.kt`
- `CheckNotificationCard.kt`
- `CheckLocationCard.kt`
- `CheckAuthRow.kt`
- `CheckRegistroSection.kt`
- `CheckInformeSection.kt`
- `CheckProjectLocationRow.kt`
- `PasswordDialog.kt`
- `RegistrationDialog.kt`
- `TransportScreen.kt`
- `TransportAddressEditor.kt`
- `TransportRequestBuilder.kt`
- `TransportHistoryList.kt`
- `TransportRequestDetailDialog.kt`
- `PortraitLockOverlay.kt`

### 10.3. Estrutura recomendada de apoio funcional

- helper para equivalentes de `web-client-state.js`;
- helper para equivalentes de `automatic-activities.js`;
- repositório de persistência por `chave` para senha, preferências e estado local de transporte;
- cliente SSE dedicado ao transporte;
- utilitários de mapeamento de mensagens e tons;
- utilitários de comparação de snapshots visuais.

## 11. Itens que Devem Ser Explicitamente Evitados na Primeira Entrega

- expandir o escopo para contratos móveis novos;
- adicionar fluxos que existem no app Flutter, mas não existem na SPA;
- reestilizar a interface para “ficar melhor”;
- trocar a ordem dos elementos para se adequar a convenções Android;
- substituir o comportamento de sessão por autenticação diferente;
- remover o overlay de paisagem só porque o app é nativo;
- simplificar o transporte eliminando SSE, histórico local ou widget de detalhe;
- remover a persistência por `chave` sob o argumento de segurança sem entregar UX equivalente;
- introduzir validações adicionais de negócio, como gate por check-in no mesmo dia para transporte.

## 12. Matriz de Verificação Manual Obrigatória

Antes de declarar o app pronto para rodar, executar no mínimo os cenários abaixo.

### 12.1. Entrada e autenticação

- digitar chave inexistente e confirmar rótulo `Chave?`;
- digitar chave existente sem senha e confirmar rótulo `Senha?`;
- digitar chave existente com senha e confirmar rótulo `Alterar`;
- concluir cadastro de senha;
- concluir autocadastro;
- trocar senha com sucesso;
- validar restauração da senha por `chave` após reabrir o app;
- validar retorno ao estado bloqueado após logout.

### 12.2. Histórico e registro manual

- abrir app autenticado e ver histórico carregado;
- confirmar destaque do item mais recente;
- fazer check-in manual com localização válida;
- fazer check-out manual;
- validar mensagem de sucesso e atualização de histórico;
- trocar projeto e confirmar persistência;
- validar local manual carregado conforme o projeto.

### 12.3. Localização e automação

- negar permissão de localização e confirmar ocultação de `Atividades Automáticas`;
- conceder permissão e confirmar reaparecimento do toggle;
- testar cada uma das cinco situações de `docs/regras_checkin_checkout_webapp.txt`;
- confirmar que nenhuma automação extra ocorre fora desses cenários;
- validar textos `Precisão insuficiente`, `Sem localização cadastrada`, `Localização não Cadastrada` e equivalentes.

### 12.4. Transporte

- abrir a tela de transporte;
- carregar estado inicial;
- editar endereço;
- criar solicitação regular;
- criar solicitação weekend;
- criar solicitação extra;
- cancelar solicitação ativa;
- registrar ciência;
- marcar solicitação como `Realizado` localmente;
- tentar dismiss em item `pending` e confirmar bloqueio;
- dismiss em item `cancelled` e confirmar persistência do estado local;
- fechar e reabrir a tela de transporte e confirmar restauração do estado local;
- validar atualização em tempo real com SSE e fallback de polling.

### 12.5. Layout e viewport

- validar em retrato;
- validar overlay ao forçar paisagem;
- validar aparelhos estreitos e aparelhos mais largos;
- validar teclado aberto sobre campos de autenticação e formulários;
- comparar screenshots com baseline da SPA.

## 13. Critérios Objetivos de “Pronto para Rodar”

O app poderá ser considerado pronto para rodar quando todos os itens abaixo forem verdadeiros ao mesmo tempo:

- compila em debug sem erros;
- instala no emulador e em dispositivo físico;
- abre pela `MainActivity` corretamente;
- autentica por `chave` e senha usando os endpoints `/api/web/*`;
- mantém sessão por cookie com o mesmo comportamento funcional da SPA;
- executa cadastro de senha, autocadastro e troca de senha;
- executa check-in/check-out manual;
- resolve localização e atualiza o histórico;
- executa as regras automáticas da SPA sem adicionar comportamento extra;
- executa o fluxo de transporte completo;
- conecta ao SSE de transporte enquanto a tela estiver aberta;
- preserva o estado local por `chave` no transporte;
- apresenta layout aprovado por comparação com a SPA;
- mantém a aplicação web original intacta.

## 14. Comandos Finais Esperados para o Marco “Pronto para Rodar”

No estado final da implementação, o fluxo mínimo de execução local deverá estar validado com comandos equivalentes a:

```powershell
Set-Location .\checking_kotlin
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :app:installDebug
```

Se for necessário iniciar manualmente a activity após a instalação:

```powershell
adb shell am start -n com.br.checkingnative/.MainActivity
```

Validações automatizadas mínimas recomendadas antes de homologar o build debug:

```powershell
Set-Location .\checking_kotlin
.\gradlew.bat :app:testDebugUnitTest
.\gradlew.bat :app:assembleDebugAndroidTest
.\gradlew.bat :app:lintDebug
```

## 15. Ordem Sequencial Recomendada de Execução

Para evitar retrabalho, a ordem recomendada é:

1. congelar baseline e aceite visual;
2. auditar lacunas entre SPA e `checking_kotlin`;
3. estabilizar contratos HTTP, cookies e SSE;
4. montar shell visual fiel;
5. fechar autenticação, senha e autocadastro;
6. fechar check manual, histórico, projeto e localização;
7. fechar atividades automáticas estritamente equivalentes à SPA;
8. fechar tela de transporte e histórico local;
9. fechar SSE e polling de fallback;
10. ajustar responsividade e detalhes finos;
11. executar a suite de testes e a validação manual;
12. gerar o build debug final e validar instalação/execução.

## 16. Conclusão Executiva

O caminho tecnicamente mais sólido é aproveitar `checking_kotlin` como base de infraestrutura, mas tratar `sistema/app/static/check` como única fonte de verdade de produto. A execução correta desta conversão não é um “port” visual superficial: ela exige congelamento do baseline, paridade rigorosa de endpoints, preservação de sessão por cookie, reconstrução fiel da interface, respeito integral às regras de check-in/check-out e migração completa do módulo de transporte, inclusive SSE e estado local por `chave`.

Se esse plano for seguido na ordem proposta, o resultado esperado é um aplicativo Android nativo em Kotlin capaz de rodar localmente, com os mesmos contratos e a mesma experiência central hoje entregue pela SPA, sem alterar a aplicação web original.

## 17. To-Do List Absolutamente Completa de Execução

Esta lista deve ser tratada como checklist operacional integral do plano. Nenhum item abaixo deve ser considerado implícito.

### 17.1. Governança, premissas e congelamento de escopo

- [x] Formalizar que a fonte de verdade funcional e visual da conversão é exclusivamente `sistema/app/static/check`.
- [x] Formalizar que a aplicação web atual não poderá ser alterada para acomodar o app Kotlin.
- [x] Formalizar que o app Kotlin deverá consumir exclusivamente os endpoints `/api/web/*` usados hoje pela SPA.
- [x] Formalizar que o app Kotlin não deverá migrar o fluxo para `/api/mobile/*`, `/api/scan`, `/api/provider/*` ou qualquer outro contrato alternativo.
- [x] Formalizar que a base Kotlin existente será usada apenas como infraestrutura técnica reaproveitável, e não como referência funcional final.
- [x] Formalizar que a entrega inicial buscará paridade com a SPA antes de qualquer expansão nativa extra.
- [x] Formalizar que qualquer funcionalidade herdada do Flutter e ausente na SPA ficará fora do escopo inicial.
- [x] Registrar a data e o commit de referência da SPA que servirão de baseline da migração.
- [x] Registrar a data e o commit de referência do repositório `checking_kotlin` que servirão de baseline técnico.
- [x] Criar branch dedicada para a linha de trabalho de paridade web no repositório `checking_kotlin_new`.
- [x] Confirmar que o repositório raiz `checkcheck` e o repositório `checking_kotlin_new` serão tratados separadamente no versionamento.
- [x] Confirmar que nenhuma alteração necessária à migração será feita dentro de `sistema/app/static/check`.
- [x] Confirmar que a definição de pronto será baseada em fluxo, layout, textos, estado e contrato, e não apenas em semelhança visual subjetiva.

### 17.2. Baseline visual e captura de referência

- [x] Gerar screenshots da SPA em retrato no estado inicial bloqueado.
- [x] Gerar screenshots da SPA com chave inexistente.
- [x] Gerar screenshots da SPA com chave existente sem senha.
- [x] Gerar screenshots da SPA com chave existente com senha.
- [x] Gerar screenshots da SPA com o modal de cadastro de senha aberto.
- [x] Gerar screenshots da SPA com o modal de alteração de senha aberto.
- [x] Gerar screenshots da SPA com o modal de autocadastro aberto.
- [x] Gerar screenshots da SPA autenticada com histórico carregado.
- [x] Gerar screenshots da SPA com o card de localização em estado de espera.
- [x] Gerar screenshots da SPA com localização identificada.
- [x] Gerar screenshots da SPA com precisão insuficiente.
- [x] Gerar screenshots da SPA com `Localização não Cadastrada`.
- [x] Gerar screenshots da SPA com `Sem localização cadastrada`.
- [x] Gerar screenshots da SPA com `Atividades Automáticas` desabilitadas.
- [x] Gerar screenshots da SPA com `Atividades Automáticas` habilitadas.
- [x] Gerar screenshots da SPA com o campo de local manual visível.
- [x] Gerar screenshots da SPA com o campo de local manual oculto.
- [x] Gerar screenshots da SPA com o campo de projeto visível.
- [x] Gerar screenshots da SPA com o campo de projeto oculto.
- [x] Gerar screenshots da SPA com a tela de transporte aberta.
- [x] Gerar screenshots da SPA com o editor de endereço do transporte aberto.
- [x] Gerar screenshots da SPA com o construtor de solicitação regular aberto.
- [x] Gerar screenshots da SPA com o construtor de solicitação weekend aberto.
- [x] Gerar screenshots da SPA com o construtor de solicitação extra aberto.
- [x] Gerar screenshots da SPA com histórico de transporte exibindo item `pending`.
- [x] Gerar screenshots da SPA com histórico de transporte exibindo item `confirmed`.
- [x] Gerar screenshots da SPA com histórico de transporte exibindo item `cancelled`.
- [x] Gerar screenshots da SPA com histórico de transporte exibindo item marcado localmente como `Realizado`.
- [x] Gerar screenshots da SPA com o widget de detalhe da solicitação aberto.
- [x] Gerar screenshots da SPA com o overlay de paisagem ativo.
- [x] Arquivar as screenshots baseline em local conhecido para comparação posterior.
- [x] Definir o dispositivo ou resolução de referência principal para comparação visual.

Execução registrada em 2026-04-25:

- os artefatos de governança da etapa 17.1 foram criados em `checking_kotlin_new/docs/governance/`;
- o projeto `checking_kotlin_new` foi inicializado como repositório Git dedicado na branch `web-parity-spa-baseline`;
- o repositório raiz passou a ignorar `checking_kotlin_new/`, mantendo separação de versionamento;
- o pacote baseline visual da etapa 17.2 foi gerado em `checking_kotlin_new/docs/baseline-visual/screenshots/2026-04-25-spa-pixel7/`;
- o manifesto de captura foi gerado em `checking_kotlin_new/docs/baseline-visual/manifest.json`;
- o capturador reexecutável foi criado em `checking_kotlin_new/scripts/capture-spa-baseline.mjs`;
- a resolução de referência definida para comparação visual é `412x915` em retrato, equivalente operacional ao Pixel 7, com `915x412` para o overlay de paisagem;
- a verificação `.\scripts\verify-scope-freeze.ps1 -StrictHashes` confirmou que `sistema/app/static/check` permaneceu intacto.

### 17.3. Tipografia, licenciamento e fidelidade visual

- [x] Confirmar se há licença formal para redistribuir `Segoe UI` no APK.
- [x] Caso não haja licença, definir a fonte substituta aprovada para paridade visual aceitável.
- [x] Documentar a decisão final sobre tipografia antes da implementação da UI.
- [x] Medir se a fonte aprovada mantém largura, altura de linha e quebra visual compatíveis com a SPA.
- [x] Validar se os textos mais críticos continuam quebrando em linhas equivalentes após a decisão tipográfica.

Execução registrada em 2026-04-25:

- não foi encontrada licença formal no repositório para redistribuir `Segoe UI` dentro do APK;
- a consulta à documentação oficial da Microsoft confirmou que fontes do Windows não devem ser redistribuídas sem direitos separados e que `Segoe UI` deve ser licenciada por canal próprio quando necessário;
- a fonte aprovada para a entrega inicial é a sans-serif do sistema Android via `FontFamily.Default`, representada por Roboto no alvo Pixel/AOSP;
- a decisão foi documentada em `checking_kotlin_new/docs/typography/typography-decision.md`;
- a medição reexecutável foi criada em `checking_kotlin_new/scripts/measure-typography-parity.mjs`;
- os resultados foram gerados em `checking_kotlin_new/docs/typography/typography-metrics.json` e `checking_kotlin_new/docs/typography/typography-metrics.md`;
- a medição em viewport `412x915` aprovou os textos críticos sem overflow horizontal e sem alteração de quebra de linha relevante.

### 17.4. Auditoria do código-fonte da SPA

- [x] Revisar integralmente `sistema/app/static/check/index.html` e mapear todos os elementos interativos.
- [x] Revisar integralmente `sistema/app/static/check/styles.css` e mapear todas as variáveis, classes de estado e regras responsivas relevantes.
- [x] Revisar integralmente `sistema/app/static/check/app.js` e mapear todos os fluxos de autenticação, histórico, localização, transporte e ciclo de vida.
- [x] Revisar integralmente `sistema/app/static/check/automatic-activities.js` e mapear todas as regras de decisão automática.
- [x] Revisar integralmente `sistema/app/static/check/web-client-state.js` e mapear sanitização, persistência local, quebra de mensagens e regras auxiliares.
- [x] Documentar todos os elementos HTML por `id` que precisarão existir no app Kotlin em forma equivalente.
- [x] Documentar todos os estados visuais da SPA que dependem de classes CSS e precisarão ser refletidos na UI nativa.

Nota de execução 17.4 (2026-04-25): etapa concluída em `checking_kotlin_new/docs/spa-audit/source-audit.md`, com inventário rastreável em `checking_kotlin_new/docs/spa-audit/spa-source-inventory.json` gerado por `checking_kotlin_new/scripts/audit-spa-source.mjs`. A auditoria cobre 85 IDs HTML, 54 elementos com `id` interativos ou ligados a regiões interativas, 18 endpoints declarados, 35 ocorrências de variáveis CSS, 59 seletores de estado, 56 listeners diretos, fluxos de autenticação, histórico, localização, transporte, ciclo de vida, regras automáticas e helpers de persistência/sanitização. Nenhum arquivo em `sistema/app/static/check` foi alterado.

### 17.5. Auditoria dos contratos backend reais

- [x] Revisar `sistema/app/routers/web_check.py` endpoint por endpoint.
- [x] Revisar `sistema/app/schemas.py` para confirmar todos os payloads de entrada e saída do fluxo web.
- [x] Confirmar a obrigatoriedade de `GET /api/web/auth/status` como etapa pública inicial.
- [x] Confirmar a semântica de `POST /api/web/auth/register-password`.
- [x] Confirmar a semântica de `POST /api/web/auth/register-user`.
- [x] Confirmar a semântica de `POST /api/web/auth/login`.
- [x] Confirmar a semântica de `POST /api/web/auth/logout`.
- [x] Confirmar a semântica de `POST /api/web/auth/change-password`.
- [x] Confirmar a semântica de `GET /api/web/projects`.
- [x] Confirmar a semântica de `PUT /api/web/project`.
- [x] Confirmar a semântica de `GET /api/web/check/state`.
- [x] Confirmar a semântica de `GET /api/web/check/locations`.
- [x] Confirmar a semântica de `POST /api/web/check/location`.
- [x] Confirmar a semântica de `POST /api/web/check`.
- [x] Confirmar a semântica de `GET /api/web/transport/state`.
- [x] Confirmar a semântica de `GET /api/web/transport/stream`.
- [x] Confirmar a semântica de `POST /api/web/transport/address`.
- [x] Confirmar a semântica de `POST /api/web/transport/vehicle-request`.
- [x] Confirmar a semântica do alias `POST /api/web/transport/request`.
- [x] Confirmar a semântica de `POST /api/web/transport/cancel`.
- [x] Confirmar a semântica de `POST /api/web/transport/acknowledge`.
- [x] Confirmar todos os códigos HTTP esperados para sucesso e erro em cada endpoint protegido.
- [x] Confirmar todas as mensagens de erro e sucesso relevantes que precisam ser preservadas na UX.

Nota de execução 17.5 (2026-04-25): etapa concluída em `checking_kotlin_new/docs/backend-contracts/backend-contracts.md`, com inventário rastreável em `checking_kotlin_new/docs/backend-contracts/backend-contract-inventory.json` gerado por `checking_kotlin_new/scripts/audit-backend-contracts.mjs`. A auditoria confirma 19 endpoints reais em `/api/web` (incluindo o alias `/api/web/transport/request`), 24 schemas relevantes, obrigatoriedade de `GET /api/web/auth/status` como chamada pública inicial, uso de sessão HTTP/cookie por `web_user_chave`, contratos de entrada/saída, códigos 200/201/401/404/409/422 e mensagens de UX que precisam ser preservadas. A etapa não editou arquivos de backend; alterações locais pré-existentes fora do escopo foram preservadas.

### 17.6. Auditoria da base técnica existente em `checking_kotlin`

- [x] Revisar `checking_kotlin/README.md` para inventariar o estado atual do projeto.
- [x] Revisar `checking_kotlin/app/build.gradle.kts` para confirmar versão, dependências e fluxo de build.
- [x] Revisar `checking_kotlin/app/src/main/AndroidManifest.xml` para mapear permissões, service, receivers e activity principal.
- [x] Revisar `checking_kotlin/app/src/main/java/com/br/checkingnative/MainActivity.kt` e identificar o que excede o escopo da SPA.
- [x] Revisar `checking_kotlin/app/src/main/java/com/br/checkingnative/data/remote/WebCheckApiService.kt` e validar aderência aos endpoints reais.
- [x] Revisar `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/checking/CheckingApp.kt`.
- [x] Revisar `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/checking/CheckingController.kt`.
- [x] Revisar `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/checking/CheckingUiState.kt`.
- [x] Revisar `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/checking/CheckingViewModel.kt`.
- [x] Revisar `checking_kotlin/app/src/main/java/com/br/checkingnative/ui/theme/*`.
- [x] Revisar a camada de persistência local e preferências já existente.
- [x] Revisar a infraestrutura de HTTP, cookies e serialização já existente.
- [x] Classificar cada arquivo Kotlin em `reaproveitar sem alteração`, `reaproveitar com adaptação` ou `não usar na entrega inicial`.

Nota de execução 17.6 (2026-04-25): etapa concluída em `checking_kotlin_new/docs/existing-kotlin-audit/technical-audit.md`, com inventário rastreável em `checking_kotlin_new/docs/existing-kotlin-audit/existing-kotlin-inventory.json` gerado por `checking_kotlin_new/scripts/audit-existing-kotlin-base.mjs`. A auditoria confirma 43 arquivos Kotlin de produção, 11 permissões Android e 5 componentes no manifest da base antiga. A decisão técnica foi reaproveitar seletivamente Compose/Hilt/DataStore, parte do cliente HTTP, cookie de sessão e modelos web; adaptar `WebCheckApiService`, estado, controller, ViewModel e tema; e não portar inicialmente foreground service, boot receiver, notificações, background location, Room/migração Flutter e fluxo mobile com shared key. Nenhum arquivo em `checking_kotlin` foi alterado.

### 17.7. Matriz de lacunas SPA x Kotlin atual

- [x] Criar uma matriz completa `recurso da SPA -> implementação atual no Kotlin -> ação necessária`.
- [x] Mapear quais elementos da UI principal já existem no Kotlin e quais precisarão ser refeitos.
- [x] Mapear quais fluxos de autenticação já existem no Kotlin e quais divergem da SPA.
- [x] Mapear quais fluxos de localização já existem no Kotlin e quais divergem da SPA.
- [x] Mapear quais fluxos de transporte já existem no Kotlin e quais divergem da SPA.
- [x] Mapear quais regras de persistência local já existem no Kotlin e quais ainda não existem.
- [x] Mapear quais diferenças de layout são apenas cosméticas e quais afetam fluxo e comportamento.
- [x] Registrar a matriz de lacunas em documento rastreável antes de começar a mexer na UI final.

Nota de execução 17.7 (2026-04-25): etapa concluída em `checking_kotlin_new/docs/gap-analysis/spa-kotlin-gap-matrix.md`, com artefato rastreável em `checking_kotlin_new/docs/gap-analysis/spa-kotlin-gap-matrix.json` gerado por `checking_kotlin_new/scripts/audit-gap-matrix.mjs`. A matriz registra 20 lacunas agrupadas por governança, shell visual, notificações, histórico, autenticação, senha, autocadastro, projetos, registro manual, localização, atividades automáticas, transporte, SSE, persistência local, HTTP/cookies, contratos, layout/CSS, tipografia, background Android antigo e testes. A conclusão técnica é que a base Kotlin antiga tem blocos reaproveitáveis, mas a paridade exige refazer UI, autenticação, transporte, persistência por chave e estados visuais conforme a SPA antes da UI final.

### 17.8. Sessão HTTP, cookies e transporte de autenticação

- [ ] Validar se o cliente HTTP atual do Kotlin persiste cookies entre chamadas.
- [ ] Implementar `CookieJar` persistente se ainda não existir comportamento equivalente ao navegador.
- [ ] Garantir que o cookie de sessão seja reaproveitado entre autenticação, check, localização e transporte.
- [ ] Garantir que o cliente SSE use o mesmo contexto de sessão do cliente HTTP comum.
- [ ] Garantir limpeza completa da sessão local ao chamar logout.
- [ ] Garantir limpeza completa da sessão local quando o backend responder `401`.
- [ ] Garantir que a UI volte ao estado bloqueado quando a sessão expirar.
- [ ] Garantir que cookies residuais não liberem a UI sem coerência com a autenticação exigida pela SPA.

### 17.9. Base URL, configuração e segurança de ambiente

- [ ] Validar `CheckingPresetConfig.apiBaseUrl` como ponto único de configuração da API.
- [ ] Validar os fallbacks de URL existentes.
- [ ] Eliminar qualquer hardcode alternativo de base URL fora do ponto central.
- [ ] Validar se o app debug consegue apontar para o ambiente correto da API.
- [ ] Garantir que o app não dependa de chave compartilhada móvel para o fluxo equivalente à SPA.
- [ ] Garantir que o fluxo web não seja misturado com contratos protegidos por outro modelo de autenticação.

### 17.10. Implementação ou ajuste da camada de modelos e mapeamento

- [ ] Confirmar que todos os modelos de request do Kotlin refletem os campos exatos dos schemas web.
- [ ] Confirmar que todos os modelos de response do Kotlin refletem os campos exatos dos schemas web.
- [ ] Ajustar serialização de booleanos, datas, horários e listas conforme o backend espera.
- [ ] Ajustar serialização de `selected_weekdays`, `requested_date` e `requested_time` conforme o contrato real.
- [ ] Ajustar leitura dos estados de transporte e normalizações locais necessárias.
- [ ] Ajustar leitura dos campos de mensagem retornados pelo backend para renderização fiel na UI.

### 17.11. Tokens visuais e fundação da interface nativa

- [ ] Criar tokens equivalentes para altura do cabeçalho.
- [ ] Criar tokens equivalentes para largura máxima do card principal.
- [ ] Criar tokens equivalentes para altura dos controles.
- [ ] Criar tokens equivalentes para raio dos cards e dos campos.
- [ ] Criar tokens equivalentes para espaçamento vertical entre seções.
- [ ] Criar tokens equivalentes para tamanho de labels, corpo, opções e título.
- [ ] Implementar o gradiente de fundo equivalente ao CSS da SPA.
- [ ] Implementar a marca d’água da Petrobras em camada de fundo com opacidade equivalente.
- [ ] Implementar a cor do cabeçalho `#0f766e`.
- [ ] Implementar a paleta de textos principal, sucesso, erro, informação e alerta.
- [ ] Implementar sombras equivalentes para card principal e overlays.
- [ ] Implementar tratamento de safe areas e recortes de tela.
- [ ] Implementar lógica de viewport dinâmico equivalente ao `100svh/100dvh` da SPA.

### 17.12. Estrutura do shell principal

- [ ] Criar o composable do shell principal do check.
- [ ] Criar o cabeçalho com logo e texto `Checking`.
- [ ] Criar o card central com largura e padding equivalentes.
- [ ] Criar o card de histórico com duas colunas.
- [ ] Criar o card de notificação com duas linhas fixas.
- [ ] Criar o card de localização com título, valor, precisão e botão refresh.
- [ ] Criar a linha de autenticação com `Chave`, `Senha` e botão lateral.
- [ ] Criar o grupo `Registro`.
- [ ] Criar o grupo `Informe`.
- [ ] Criar a linha `Projeto` + `Local`.
- [ ] Criar o botão principal `Registrar`.
- [ ] Garantir que os estados disabled e busy de todos os controles estejam implementados.

### 17.13. Overlay de paisagem e comportamento de orientação

- [ ] Implementar overlay que informe ao usuário que o app foi otimizado para visualização vertical.
- [ ] Implementar ocultação do conteúdo principal quando a paisagem estiver ativa.
- [ ] Implementar a lógica equivalente de detecção de paisagem.
- [ ] Garantir que a activity continue utilizável em retrato sem glitches após rotação.
- [ ] Validar se será necessário forçar orientação em nível de activity ou apenas reproduzir o overlay da SPA.
- [ ] Garantir que a decisão adotada preserve a experiência funcional da SPA.

### 17.14. Estado inicial bloqueado e resolução da chave

- [ ] Implementar estado inicial bloqueado do app antes da autenticação válida.
- [ ] Implementar sanitização da `chave` equivalente à SPA.
- [ ] Persistir a última `chave` usada.
- [ ] Restaurar a última `chave` usada ao reabrir o app.
- [ ] Chamar `GET /api/web/auth/status` ao resolver a `chave`.
- [ ] Atualizar a UI conforme o retorno de `found`, `has_password` e `authenticated`.
- [ ] Limpar sessão protegida local se o status indicar que a autenticação não está mais válida.
- [ ] Garantir que o estado bloqueado persista enquanto a senha não estiver verificada.

### 17.15. Persistência local por `chave`

- [ ] Implementar armazenamento seguro da senha por `chave`.
- [ ] Implementar armazenamento da última `chave` usada.
- [ ] Implementar armazenamento das preferências do usuário por `chave`.
- [ ] Implementar armazenamento do estado local do transporte por `chave`.
- [ ] Implementar armazenamento da flag de tentativa de permissão de localização.
- [ ] Implementar armazenamento da flag de permissão de localização concedida.
- [ ] Garantir que os dados persistidos sejam restaurados no momento equivalente ao webapp.
- [ ] Garantir que o logout limpe o que a SPA considera estado protegido.

### 17.16. Botão lateral de autenticação e estados assistidos

- [ ] Implementar o rótulo `Alterar` quando a chave possuir senha.
- [ ] Implementar o rótulo `Senha?` quando a chave existir sem senha.
- [ ] Implementar o rótulo `Chave?` quando a chave não existir.
- [ ] Implementar o rótulo `Aguarde` em estados de operação pendente.
- [ ] Implementar estilo visual de atenção equivalente ao webapp.
- [ ] Implementar estilo visual de estado pendente equivalente ao webapp.
- [ ] Implementar travamento de outros botões enquanto o fluxo de autenticação estiver ocupado.

### 17.17. Restauração de campos de autenticação e ergonomia

- [ ] Implementar restauração da senha previamente persistida quando a mesma `chave` for revisitada.
- [ ] Implementar restauração da `chave` se o usuário a apagar e sair do campo sem intenção de mudança confirmada.
- [ ] Implementar restauração da senha se o usuário a apagar e sair do campo sem intenção de mudança confirmada.
- [ ] Implementar gatilho de verificação automática da senha restaurada.
- [ ] Preservar o mesmo comportamento de travamento e desbloqueio observado na SPA.

### 17.18. Modal de senha

- [ ] Criar diálogo equivalente ao `passwordDialog` da SPA.
- [ ] Implementar o modo `Cadastrar Senha`.
- [ ] Implementar o modo `Alterar Senha`.
- [ ] Ocultar `Senha Antiga` no modo de cadastro, mantendo o comportamento visual equivalente.
- [ ] Implementar validação de tamanho mínimo e máximo da senha.
- [ ] Implementar validação de confirmação de senha.
- [ ] Plugar `POST /api/web/auth/register-password`.
- [ ] Plugar `POST /api/web/auth/change-password`.
- [ ] Atualizar sessão local após sucesso.
- [ ] Atualizar a UI principal após sucesso.
- [ ] Exibir mensagens de erro e sucesso exatamente conforme o backend e a SPA orientam.

### 17.19. Modal de autocadastro

- [ ] Criar diálogo equivalente ao `registrationDialog` da SPA.
- [ ] Implementar os campos `Chave`, `Nome Completo`, `Projeto`, `E-Mail`, `Senha` e `Confirma Senha`.
- [ ] Garantir que o campo `E-Mail` permaneça opcional.
- [ ] Garantir que endereço e ZIP não sejam adicionados ao fluxo de autocadastro.
- [ ] Plugar `POST /api/web/auth/register-user`.
- [ ] Garantir autenticação automática após cadastro bem-sucedido.
- [ ] Atualizar o estado principal do app após sucesso.
- [ ] Exibir mensagens equivalentes às da SPA para sucesso e erro.

### 17.20. Histórico de check e sugestão de atividade

- [ ] Implementar carregamento de histórico via `GET /api/web/check/state`.
- [ ] Renderizar `Último Check-In`.
- [ ] Renderizar `Último Check-Out`.
- [ ] Renderizar `--` quando o valor estiver ausente.
- [ ] Implementar cálculo da atividade mais recente com a mesma lógica da SPA.
- [ ] Destacar visualmente o item mais recente com moldura verde equivalente.
- [ ] Aplicar a ação sugerida a partir do histórico, como a SPA faz.
- [ ] Garantir atualização do histórico após check manual e após fluxos automáticos.

### 17.21. Card de notificação

- [ ] Implementar quebra em linha primária e secundária equivalente à SPA.
- [ ] Implementar tons de mensagem `success`, `error`, `info`, `warning` e `neutral`.
- [ ] Garantir que textos longos quebrem de modo equivalente ao webapp.
- [ ] Garantir que mensagens vindas do backend não percam informação relevante.

### 17.22. Catálogo de projetos

- [ ] Implementar carregamento de projetos via `GET /api/web/projects`.
- [ ] Popular o seletor de projeto com a mesma ordem e os mesmos valores da SPA.
- [ ] Persistir o projeto selecionado por `chave`.
- [ ] Restaurar o projeto persistido ao revisitar a mesma `chave`.
- [ ] Atualizar o projeto remoto via `PUT /api/web/project` quando o usuário trocar a seleção.
- [ ] Garantir tratamento coerente de carregamento, erro e fallback do catálogo.

### 17.23. Catálogo de locais e seleção manual

- [ ] Implementar carregamento de locais via `GET /api/web/check/locations`.
- [ ] Filtrar o catálogo conforme o backend retornar para o projeto do usuário.
- [ ] Popular o seletor de local manual.
- [ ] Desabilitar o seletor enquanto estiver carregando ou quando a UI equivalente assim exigir.
- [ ] Ocultar o campo de local manual quando a lógica da SPA assim exigir.

### 17.24. Localização sob demanda

- [ ] Implementar captura de localização sob demanda equivalente ao `getCurrentPosition` da SPA.
- [ ] Implementar o botão de refresh de localização.
- [ ] Plugar `POST /api/web/check/location`.
- [ ] Atualizar o valor textual da localização na UI.
- [ ] Atualizar a precisão exibida na UI.
- [ ] Implementar os estados `matched`, `accuracy_too_low`, `outside_workplace`, `not_in_known_location` e `no_known_locations`.
- [ ] Garantir que as mensagens equivalentes da SPA sejam exibidas corretamente.
- [ ] Reexecutar a atualização de localização nos eventos de ciclo de vida equivalentes ao webapp.

### 17.25. Regras de visibilidade dos campos

- [ ] Ocultar o campo de projeto quando `Atividades Automáticas` estiver ligada, conforme a SPA.
- [ ] Ocultar o campo de local manual quando a permissão GPS estiver ativa, conforme a SPA.
- [ ] Reavaliar a visibilidade desses campos quando a permissão GPS mudar.
- [ ] Reavaliar a visibilidade desses campos quando as preferências persistidas forem restauradas.
- [ ] Garantir coerência visual e funcional entre controles visíveis e invisíveis.

### 17.26. Grupo `Registro`

- [ ] Implementar os rádios `Check-In` e `Check-Out`.
- [ ] Implementar o botão de transporte com o rótulo e a aparência equivalentes à SPA.
- [ ] Manter a legenda com `Atividades Automáticas` acima de `Registro`.
- [ ] Implementar desabilitação dos controles quando a SPA equivalente assim o fizer.
- [ ] Garantir que o botão de transporte respeite os estados de bloqueio da tela principal.

### 17.27. Grupo `Informe`

- [ ] Implementar os rádios `Normal` e `Retroativo`.
- [ ] Garantir a mesma ordem visual e semântica da SPA.
- [ ] Garantir desabilitação quando a UI estiver travada ou o fluxo equivalente exigir.

### 17.28. Fluxo manual de check-in/check-out

- [ ] Montar o payload equivalente ao usado pela SPA em `POST /api/web/check`.
- [ ] Garantir envio de `chave`, `projeto`, `action`, `informe`, `local`, `event_time` e `client_event_id` conforme o contrato usado pelo webapp.
- [ ] Implementar botão `Registrar` com estado de carregamento.
- [ ] Bloquear nova submissão enquanto houver submissão em andamento.
- [ ] Atualizar histórico após sucesso.
- [ ] Atualizar notificações após sucesso ou erro.
- [ ] Garantir que o fluxo manual respeite as mesmas regras de bloqueio do webapp quando `Atividades Automáticas` estiverem ativas.

### 17.29. Atividades automáticas

- [ ] Implementar o toggle `Atividades Automáticas`.
- [ ] Exibir o toggle apenas quando a condição de disponibilidade equivalente à SPA for satisfeita.
- [ ] Ocultar o toggle e limpar seu estado quando a condição deixar de ser satisfeita.
- [ ] Restaurar a preferência persistida por `chave` para atividades automáticas.
- [ ] Reexecutar a sequência de atualização quando a aplicação entrar em primeiro plano e estiver autenticada.
- [ ] Implementar a Situação 1 de `docs/regras_checkin_checkout_webapp.txt`.
- [ ] Implementar a Situação 2 de `docs/regras_checkin_checkout_webapp.txt`.
- [ ] Implementar a Situação 3 de `docs/regras_checkin_checkout_webapp.txt`.
- [ ] Implementar a Situação 4 de `docs/regras_checkin_checkout_webapp.txt`.
- [ ] Implementar a Situação 5 de `docs/regras_checkin_checkout_webapp.txt`.
- [ ] Garantir que nenhuma automação adicional herdada do Flutter seja disparada na entrega inicial.
- [ ] Garantir que a mensagem `Desative Atividades Automáticas para registrar manualmente.` apareça quando aplicável.

### 17.30. Decisão operacional sobre background nativo na entrega inicial

- [ ] Decidir formalmente se o background service existente no Kotlin ficará desabilitado na entrega de paridade com a SPA.
- [ ] Se ficar desabilitado, garantir que nenhuma UI exponha esse comportamento como ativo.
- [ ] Se algum trecho técnico de background permanecer no app, encapsular por flag para não alterar a experiência exigida pela SPA.
- [ ] Validar que a entrega inicial não dependa de monitoramento contínuo para funcionar como a SPA.

### 17.31. Tela de transporte

- [ ] Criar a tela ou diálogo de transporte com altura útil equivalente à SPA.
- [ ] Criar o cabeçalho da tela de transporte com botão de voltar.
- [ ] Criar a linha de resumo de endereço.
- [ ] Criar o editor de endereço.
- [ ] Criar o painel de opções `regular`, `weekend` e `extra`.
- [ ] Criar o construtor de solicitação com o mesmo texto e semântica da SPA.
- [ ] Criar a seção de histórico de solicitações ocupando o espaço restante da tela.
- [ ] Criar o widget de detalhe da solicitação.
- [ ] Implementar estados vazios, de carregamento e de erro da tela de transporte.

### 17.32. Endereço do transporte

- [ ] Implementar carregamento do endereço atual a partir de `GET /api/web/transport/state`.
- [ ] Implementar edição de endereço com os mesmos campos da SPA.
- [ ] Plugar `POST /api/web/transport/address`.
- [ ] Atualizar o estado da tela de transporte após salvar o endereço.
- [ ] Atualizar o resumo do endereço após salvar.

### 17.33. Construtor de solicitação regular, weekend e extra

- [ ] Implementar o modo `regular` com os dias úteis permitidos.
- [ ] Implementar o modo `weekend` com os dias de fim de semana permitidos.
- [ ] Implementar o modo `extra` com data e hora.
- [ ] Implementar subtítulos e textos equivalentes aos da SPA.
- [ ] Implementar botão `Solicitar` com estado `Solicitando...`.
- [ ] Implementar validações locais coerentes com a SPA antes do envio.
- [ ] Plugar `POST /api/web/transport/vehicle-request` como endpoint principal.
- [ ] Tratar `/api/web/transport/request` apenas como alias de compatibilidade, se necessário.
- [ ] Recarregar o estado do transporte após criação ou reaproveitamento de solicitação ativa.

### 17.34. Histórico de solicitações de transporte

- [ ] Renderizar lista completa de solicitações retornadas pelo backend, e não apenas a ativa.
- [ ] Garantir ordenação visual coerente com o estado retornado pela API.
- [ ] Implementar badges, estados e rótulos equivalentes aos do webapp.
- [ ] Implementar o botão local `Realizado` quando elegível.
- [ ] Implementar lógica de dismiss apenas para cartões `realized` ou `cancelled`.
- [ ] Implementar persistência local de `dismissed_request_ids`.
- [ ] Implementar persistência local de `realized_request_ids`.
- [ ] Garantir que o estado local sobreviva ao fechamento e à reabertura da tela.
- [ ] Garantir que o estado local não seja limpo prematuramente.
- [ ] Garantir que o estado local seja limpo quando o reset protegido da sessão realmente ocorrer.

### 17.35. Normalizações de status de transporte

- [ ] Implementar normalização de `realized` da API para `confirmed` no fluxo local, como a SPA faz.
- [ ] Implementar normalização de solicitações inativas para `cancelled`, salvo override local de `realized`.
- [ ] Garantir que a UI não volte indevidamente um item já marcado localmente como realizado.
- [ ] Garantir que `pending` e `confirmed` permaneçam visíveis.
- [ ] Garantir que cartões `cancelled` e `realized` possam ser ocultados localmente.

### 17.36. Ações do histórico de transporte

- [ ] Implementar cancelamento via `POST /api/web/transport/cancel`.
- [ ] Implementar ciência via `POST /api/web/transport/acknowledge`.
- [ ] Implementar o gesto ou ação equivalente ao dismiss da SPA.
- [ ] Implementar o pop-up ou diálogo de detalhe da solicitação.
- [ ] Garantir que o detalhe exponha veículo, placa, cor, horários e demais campos equivalentes ao webapp.

### 17.37. SSE de transporte e fallback de polling

- [ ] Escolher a biblioteca ou abordagem de SSE para Android compatível com o restante da stack.
- [ ] Implementar o cliente SSE de `GET /api/web/transport/stream?chave=...`.
- [ ] Garantir envio automático dos cookies de sessão no handshake da conexão SSE.
- [ ] Abrir a conexão apenas ao entrar na tela de transporte.
- [ ] Fechar a conexão ao sair da tela de transporte.
- [ ] Implementar keep-alive e reconexão segura.
- [ ] Implementar polling de fallback a cada 10 segundos.
- [ ] Implementar debounce de refresh em tempo real equivalente ao webapp.
- [ ] Garantir que SSE e polling não gerem duplicidade de atualização ou regressão visual.

### 17.38. Responsividade e precisão visual fina

- [ ] Ajustar largura máxima do card em telas pequenas, médias e grandes.
- [ ] Ajustar gaps verticais entre seções.
- [ ] Ajustar padding interno dos cards.
- [ ] Ajustar altura dos botões e inputs.
- [ ] Ajustar cantos arredondados de cards, campos e botões.
- [ ] Ajustar espaçamento e alinhamento do cabeçalho.
- [ ] Ajustar o layout da linha de autenticação.
- [ ] Ajustar a linha de projeto/local.
- [ ] Ajustar a grade de opções de registro.
- [ ] Ajustar a grade de opções de informe.
- [ ] Ajustar o tamanho e o espaçamento dos chips de dias no transporte.
- [ ] Ajustar o crescimento da lista de histórico de transporte dentro do espaço restante da tela.
- [ ] Ajustar estados de foco e de teclado aberto em telas pequenas.
- [ ] Ajustar as opacidades, cores e bordas dos estados de atenção e pending.

### 17.39. Textos, ortografia e consistência de linguagem

- [ ] Conferir que todos os textos visíveis reproduzem os textos atuais da SPA.
- [ ] Conferir capitalização consistente em `Último Check-In`, `Último Check-Out`, `Projeto`, `Local`, `Registro`, `Informe`, `Alterar`, `Voltar`, `Enviar` e `Registrar`.
- [ ] Conferir acentuação correta em `Solicitação`, `Ciência`, `Precisão`, `Localização` e demais termos exibidos ao usuário.
- [ ] Conferir que as mensagens de erro e ajuda não perderam o sentido original do webapp.
- [ ] Conferir que o overlay de paisagem use o mesmo texto da SPA.

### 17.40. Testes unitários de lógica

- [ ] Criar testes para sanitização de `chave`.
- [ ] Criar testes para quebra de notificação em linha primária/secundária.
- [ ] Criar testes para decisão do rótulo do botão lateral de autenticação.
- [ ] Criar testes para cálculo da atividade mais recente do histórico.
- [ ] Criar testes para restauração de projeto e senha por `chave`.
- [ ] Criar testes para normalização de status de transporte.
- [ ] Criar testes para elegibilidade de `Realizado` local.
- [ ] Criar testes para elegibilidade de dismiss do cartão de transporte.
- [ ] Criar testes para as regras de atividades automáticas derivadas de `automatic-activities.js`.

### 17.41. Testes de integração e contrato HTTP

- [ ] Testar `GET /api/web/auth/status` a partir do app Kotlin.
- [ ] Testar `POST /api/web/auth/register-password` a partir do app Kotlin.
- [ ] Testar `POST /api/web/auth/register-user` a partir do app Kotlin.
- [ ] Testar `POST /api/web/auth/login` a partir do app Kotlin.
- [ ] Testar `POST /api/web/auth/logout` a partir do app Kotlin.
- [ ] Testar `POST /api/web/auth/change-password` a partir do app Kotlin.
- [ ] Testar `GET /api/web/projects` a partir do app Kotlin.
- [ ] Testar `PUT /api/web/project` a partir do app Kotlin.
- [ ] Testar `GET /api/web/check/state` a partir do app Kotlin.
- [ ] Testar `GET /api/web/check/locations` a partir do app Kotlin.
- [ ] Testar `POST /api/web/check/location` a partir do app Kotlin.
- [ ] Testar `POST /api/web/check` a partir do app Kotlin.
- [ ] Testar `GET /api/web/transport/state` a partir do app Kotlin.
- [ ] Testar `POST /api/web/transport/address` a partir do app Kotlin.
- [ ] Testar `POST /api/web/transport/vehicle-request` a partir do app Kotlin.
- [ ] Testar `POST /api/web/transport/cancel` a partir do app Kotlin.
- [ ] Testar `POST /api/web/transport/acknowledge` a partir do app Kotlin.
- [ ] Testar `GET /api/web/transport/stream` a partir do app Kotlin.
- [ ] Testar tratamento de `401` em fluxos protegidos.
- [ ] Testar tratamento de `404` em fluxos de chave inexistente e senha ausente.
- [ ] Testar tratamento de `409` nos fluxos que o backend usa para conflito.
- [ ] Testar tratamento de `422` para validações de payload.

### 17.42. Testes instrumentados de UI e screenshot

- [ ] Criar teste instrumentado do estado inicial bloqueado.
- [ ] Criar teste instrumentado do estado de chave inexistente.
- [ ] Criar teste instrumentado do estado de chave sem senha.
- [ ] Criar teste instrumentado do estado autenticado principal.
- [ ] Criar teste instrumentado do modal de senha em modo cadastro.
- [ ] Criar teste instrumentado do modal de senha em modo alteração.
- [ ] Criar teste instrumentado do modal de autocadastro.
- [ ] Criar teste instrumentado do card de histórico com destaque em `checkin`.
- [ ] Criar teste instrumentado do card de histórico com destaque em `checkout`.
- [ ] Criar teste instrumentado do card de localização em cada estado principal.
- [ ] Criar teste instrumentado da tela de transporte.
- [ ] Criar teste instrumentado do construtor regular.
- [ ] Criar teste instrumentado do construtor weekend.
- [ ] Criar teste instrumentado do construtor extra.
- [ ] Criar teste instrumentado do histórico de transporte com diferentes status.
- [ ] Criar teste instrumentado do overlay de paisagem.
- [ ] Criar testes de screenshot comparáveis com as capturas baseline da SPA.

### 17.43. Testes manuais obrigatórios

- [ ] Executar manualmente os cenários de entrada e autenticação listados na Seção 12.1.
- [ ] Executar manualmente os cenários de histórico e registro manual listados na Seção 12.2.
- [ ] Executar manualmente os cenários de localização e automação listados na Seção 12.3.
- [ ] Executar manualmente os cenários de transporte listados na Seção 12.4.
- [ ] Executar manualmente os cenários de layout e viewport listados na Seção 12.5.
- [ ] Registrar evidência de cada cenário manual executado.
- [ ] Registrar qualquer divergência residual, por menor que seja.

### 17.44. Validação de não regressão da aplicação web

- [ ] Confirmar que nenhum arquivo em `sistema/app/static/check` foi alterado ao final do trabalho.
- [ ] Confirmar que nenhum endpoint do backend precisou ser alterado para a entrega inicial do app Kotlin.
- [ ] Confirmar que a SPA continua funcionando normalmente após a conclusão da implementação no app Kotlin.
- [ ] Confirmar que a implantação do app Kotlin não introduziu dependências de runtime que quebrem o webapp.

### 17.45. Build, instalação e execução local

- [ ] Garantir que `checking_kotlin` compile com `:app:assembleDebug`.
- [ ] Garantir que `:app:installDebug` instale o app no emulador ou dispositivo.
- [ ] Garantir que a `MainActivity` abra corretamente após a instalação.
- [ ] Garantir que o app inicialize sem crash no primeiro start.
- [ ] Garantir que o app inicialize sem crash após rotação, background/foreground e reabertura.
- [ ] Garantir que o app consiga se autenticar contra a API real do ambiente configurado.

### 17.46. Logs, observabilidade e depuração de falhas

- [ ] Revisar logs do app para autenticação.
- [ ] Revisar logs do app para localização.
- [ ] Revisar logs do app para transporte.
- [ ] Revisar logs do app para SSE e reconexão.
- [ ] Garantir que erros críticos fiquem rastreáveis para depuração.
- [ ] Garantir que logs não exponham senha em texto puro.

### 17.47. Documentação final da entrega

- [ ] Atualizar a documentação do `checking_kotlin` para descrever o fluxo equivalente à SPA.
- [ ] Documentar como configurar a base URL da API no app Kotlin.
- [ ] Documentar como compilar e instalar o build debug.
- [ ] Documentar como executar os testes relevantes.
- [ ] Documentar qualquer limitação residual aprovada formalmente.
- [ ] Documentar a decisão final sobre tipografia.
- [ ] Documentar a decisão final sobre background nativo na entrega inicial.

### 17.48. Critério final de fechamento

- [ ] Confirmar que todos os itens desta checklist foram executados ou formalmente dispensados com justificativa.
- [ ] Confirmar que os critérios da Seção 13 foram atendidos integralmente.
- [ ] Confirmar que o app Kotlin reproduz a mesma experiência central hoje entregue pela SPA.
- [ ] Confirmar que o aplicativo está efetivamente pronto para rodar localmente em build debug.
- [ ] Confirmar que a aplicação web original permaneceu intacta.
