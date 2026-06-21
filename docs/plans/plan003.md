# plan003 — Aprovação de novos usuários (app Kotlin + Check Web + site admin)

> Status: **proposta revisada** (decisões 1–4 confirmadas pelo dono do produto — ver §11). Nada
> implementado ainda. Escopo: **backend**, **app Kotlin** (`checking_kotlin`), **Check Web**
> (`sistema/app/static/check`) e **site admin** (`sistema/app/static/admin2`), com a garantia de que
> **nenhuma funcionalidade existente seja afetada**.

---

## 0. Objetivo

Hoje, qualquer pessoa que faça o autocadastro fica **imediatamente autenticada** e com acesso ao sistema.
Vamos inserir uma **etapa de aprovação humana**, **válida para todos os clientes** (app Android **e** Check
Web — ver decisão 1, §11): o novo usuário preenche o formulário, fica em estado **"aguardando aprovação"**
(não autenticado), e só obtém acesso quando um administrador (perfil 1 ou 9) o **aprovar** no site admin. Se
**reprovar**, o cadastro é removido (silenciosamente, sem aviso ao usuário).

Fluxo desejado:

1. Usuário instala/abre o app (ou abre o Check Web) e digita a chave.
2. Se a chave é desconhecida, o **formulário de cadastro abre automaticamente** (com **seta "Voltar"** no
   canto superior esquerdo para retornar à tela principal — útil se digitou errado uma chave já cadastrada).
3. Usuário preenche e envia.
4. **Não autentica.** Campos `chave` e `senha` ficam **laranja brilhante**; a barra de notificações mostra,
   **em vermelho**: `Aguardando aprovação de cadastro.`
5. Se a fila estiver cheia (limite **300**), em vez disso mostra, em vermelho:
   `Fila de cadastro cheia. Informe ao administrador do sistema.`
6. No admin: a tabela **"Cadastro de Pendências"** vira **"Pendências de RFID"**; cria-se **"Pendências de
   Usuários"** logo acima dela, com colunas **Data, Chave, Nome Completo, Projetos, E-Mail, Ações
   (Aprovar / Reprovar)**.
7. **Reprovar** → remove o cadastro do banco (sem avisar o usuário). **Aprovar** → o cliente recebe a
   informação e **imediatamente processa o check-in/check-out pertinente à situação** do usuário.

---

## 1. Decisões de arquitetura (e por que são as mais seguras)

### 1.1 Decisão central — *tabela separada de pendências* (NÃO mexer em `users`)

| Abordagem | Como | Risco |
|---|---|---|
| **A. Coluna em `users`** (ex.: `approval_status`) | Cria o `User` já como "pending" e filtra em todo lugar | **Alto**: toda query/contagem/sync/join/relatório/admin que lista `users` precisaria filtrar; fácil quebrar algo. Viola "nada afetado". |
| **B. Tabela `pending_user_registrations` separada** ✅ | O `User` **só é criado na aprovação**; enquanto pendente vive numa tabela própria | **Baixo**: nenhuma query existente sobre `users` enxerga pendentes. Mesmo padrão já usado para RFID (`pending_registrations`). |

**Escolha: B.** Garante, por construção, que nenhuma funcionalidade existente seja afetada: enquanto
pendente, o usuário **não existe** em `users`, então login, check-in/out, motor de situações, sync,
transporte, acidente, relatórios e o admin continuam idênticos. Na aprovação, criamos o `User` reutilizando
**exatamente** a lógica de criação que já existe hoje em `register_web_user`.

"Reprovar → usuário removido do banco" (req. 7) = remover a linha de `pending_user_registrations` (nenhum
`User` chegou a existir). Semântica preservada.

### 1.2 Estado "aguardando aprovação" derivado do servidor (robustez)

O estado de espera **não** depende de flag local frágil: é **derivado** do `GET …/auth/status`, que passa a
reportar `pending_approval`. Assim, mesmo fechando/reabrindo o app/navegador ou trocando de aparelho, ao
digitar a chave o servidor diz se está pendente. A senha digitada fica guardada localmente (app:
`securePasswordStore`; web: já reusa a senha do formulário em memória da sessão) para o login automático
**após** a aprovação.

### 1.3 Abrangência — **CONFIRMADA: sistema inteiro** (todos os clientes)

`POST …/auth/register-user` é **compartilhado** pelo app Kotlin e pelo Check Web (mesmo handler em
`web_check.py`). Conforme decisão 1 (§11), a aprovação passa a valer para **todos os clientes** — fechamos
também a "porta web", já que o app indo a produção pode atrair cadastros maliciosos pelo navegador.

Implicação: o gate **não** usa o header `X-Client`; é **incondicional** (controlado só pela flag §1.4). O
header `X-Client` ainda é gravado em `pending_user_registrations.client` apenas para **observabilidade**
(saber se a pendência veio do app ou do navegador). E o **Check Web ganha a mesma UI** de espera / fila
cheia (§6).

### 1.4 Feature flag de segurança (rollback sem deploy de código)

Variável **`CHECK_USER_APPROVAL_REQUIRED`** (default **`true`**) em `core/config.py`. Quando `false`,
`register-user` volta ao comportamento legado (cria + autentica) para todos os clientes — reverte o recurso
em produção instantaneamente, sem rollback de imagem.

---

## 2. Contrato (fonte da verdade entre backend ↔ app ↔ web ↔ admin)

### 2.1 Tabela nova (`sistema/app/models.py`)

```python
class PendingUserRegistration(Base):
    __tablename__ = "pending_user_registrations"
    __table_args__ = (
        UniqueConstraint("chave", name="uq_pending_user_registrations_chave"),
        Index("ix_pending_user_registrations_requested_at", "requested_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chave: Mapped[str] = mapped_column(String(4), nullable=False)
    nome_completo: Mapped[str] = mapped_column(String(180), nullable=False)
    projetos_json: Mapped[str] = mapped_column(Text, nullable=False)   # JSON em Text (convenção do projeto)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    client: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 'checking-android' / 'web' (observabilidade)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

Constante `PENDING_USER_REGISTRATION_LIMIT = 300`.

### 2.2 Migration Alembic `0079_add_pending_user_registrations`

- `op.create_table(...)` com a unique de `chave` e o índice de `requested_at`; `downgrade` faz `drop_table`.
- Testada em SQLite limpo; aditiva (cria tabela nova) — segura em Postgres. Revisão encadeada após `0078`.

### 2.3 `GET …/auth/status` — campo novo `pending_approval`

`WebPasswordStatusResponse` ganha **`pending_approval: bool = False`**:

| Situação no servidor | `found` | `has_password` | `authenticated` | `pending_approval` |
|---|---|---|---|---|
| `User` existe (normal/aprovado) | `true` | conforme hoje | conforme sessão | `false` |
| Não há `User`, há linha pendente | `false` | `false` | `false` | **`true`** |
| Não há nada | `false` | `false` | `false` | `false` |

Campo **aditivo**; nenhuma mudança nos campos atuais.

### 2.4 `POST …/auth/register-user` — comportamento novo

```
normalized = valida chave
se já existe User(chave)               -> 409 (igual hoje)
se já existe AdminAccessRequest(chave) -> 409 (igual hoje)
se já existe PendingUserRegistration(chave) -> 409 "Ja existe uma solicitacao pendente para essa chave"

gate = settings.check_user_approval_required        # incondicional (todos os clientes)

se NÃO gate:                                         # flag desligada -> LEGADO intacto
    cria User + memberships + set_session + notify  (código atual)
    return 201 {status:"registered", authenticated:true, projects, active_project}

se gate:
    count = COUNT(pending_user_registrations)
    se count >= 300:
        return 200 {status:"queue_full", authenticated:false, pending_approval:false}
    cria PendingUserRegistration(chave, nome, projetos_json, email, password_hash,
                                 client=header X-Client or "web", requested_at=now)
    # NÃO cria User, NÃO cria sessão
    notify_admin_data_changed("admin"); notify_admin_data_changed("register")
    return 202 {status:"pending", authenticated:false, pending_approval:true, projects, active_project:""}
```

Resposta (`WebUserSelfRegistrationResponse`) ganha `status: Literal["registered","pending","queue_full"]`,
`pending_approval: bool=False`, `queue_full: bool=False`, e `projects`/`active_project` **opcionais** (na
fila não há projeto ativo). HTTP: `registered`→201, `pending`→202, `queue_full`→200 (todos 2xx → clientes
leem o corpo e decidem pelo `status`).

**Limite 300 (corrida):** `COUNT`+`INSERT` na mesma transação + revalidação pós-insert (rollback→`queue_full`
se passou). Unique de `chave` evita duplicatas.

### 2.5 Endpoints admin (`sistema/app/routers/admin.py`) — escopados por projeto (decisão 2)

Todos com `Depends(require_full_admin_session)` (garante perfil ∈ {1,9} via `user_has_admin_access`):

| Método | Path | Ação |
|---|---|---|
| `GET` | `/api/admin/user-pending` | Lista pendências (mais recentes 1º), **escopadas aos projetos do admin**; admin em N projetos vê a **união**; perfil 9 vê tudo. |
| `POST` | `/api/admin/user-pending/{id}/approve` | Cria `User`+memberships (reusa lógica de criação), apaga a pendente, `commit`, `notify_admin_views("register","event")` + `notify_web_check_data_changed()`, `log_event(action="user_approve")`. |
| `POST` | `/api/admin/user-pending/{id}/reject` | Apaga a pendente, `commit`, `notify_admin_views("register","event")`, `log_event(action="user_reject")`. |

- **Escopo por projeto:** novo helper `user_pending_matches_admin_scope(...)` análogo ao
  `pending_matches_admin_scope` do RFID, comparando `projetos_json` da pendência com
  `resolve_effective_admin_project_names(db, current_admin)`. Mesma semântica de visibilidade do RFID.
- `action` ≤ 16 chars: `user_approve`(12), `user_reject`(11), `user_pending`(12). OK.
- **Idempotência:** aprovar quando já existe `User(chave)` → tratar como "já aprovado" (limpa pendência,
  responde ok), sem 500.
- Só **leem** o admin e **criam `User` comum**; não gravam em `*_by_admin_id` → `require_full_admin_session`
  basta (ver `CLAUDE.md` §Identidade de admin).

Schema novo: `AdminUserPendingRow { id, requested_at, chave, nome_completo, projetos: list[str], email }`.

### 2.6 Mensagens i18n (exatas)

- **App Kotlin (6 idiomas):** `auth.awaitingApproval` = "Aguardando aprovação de cadastro." e
  `auth.registrationQueueFull` = "Fila de cadastro cheia. Informe ao administrador do sistema." (pt com o
  texto exato; en/zh/ms/id/tl traduzidos).
- **Check Web (6 idiomas):** mesmas 2 chaves no `i18n-dictionaries.js` (pt/en/zh/ms/id/tl, com fallback pt
  via `t()` — mesma política do app web).
- **admin2 (pt-only):** rótulos direto no HTML ("Pendências de Usuários", "Aprovar", "Reprovar",
  cabeçalhos).

---

## 3. Backend (root monolito — `git push origin main`, **requer aprovação humana**)

| Arquivo | Mudança |
|---|---|
| `models.py` | + `PendingUserRegistration` (§2.1). |
| `alembic/versions/0079_…py` | + migration (§2.2). |
| `core/config.py` | + `check_user_approval_required: bool = True`; + `pending_user_registration_limit: int = 300`. |
| `schemas.py` | `WebPasswordStatusResponse += pending_approval`; `WebUserSelfRegistrationResponse += status/pending_approval/queue_full` + `projects/active_project` opcionais; + `AdminUserPendingRow`. |
| `routers/web_check.py` | reescrever `register_web_user` (§2.4); ajustar status p/ `pending_approval` (§2.3). |
| `routers/admin.py` | + 3 endpoints + helper de escopo + `log_event` (§2.5). |
| `services/…` | extrair `create_user_from_registration(db, chave, nome, projetos, email, password_hash)` reutilizado pelo caminho legado **e** pela aprovação (evita duplicar a criação do `User`). |

Brokers SSE: registrar pendência e aprovar/reprovar chamam `notify_admin_data_changed`/`notify_admin_views`
(admin em tempo real). Aprovação chama também `notify_web_check_data_changed()`. Clientes pendentes detectam
aprovação por **polling** de `/auth/status` (não têm sessão p/ `/check/stream`).

---

## 4. Site Admin (`sistema/app/static/admin2`)

> ⚠️ **Espelho de deploy:** após editar `sistema/app/static/admin2/`, **espelhar byte-a-byte** para
> `deploy/docker/admin2-web/` (memórias *Admin2 source = deploy mirror* / *Admin2 deploy pipeline*). Sem
> isso, a mudança não chega em produção.

### 4.1 `index.html`
- Renomear `<h2>Cadastro de Pendências</h2>` → **`<h2>Pendências de RFID</h2>`**.
- Inserir **acima** do `<article … data-cadastro-section="pendencias">` um novo article:
  ```html
  <article class="cadastro-section-panel cadastro-section-panel--pending" data-cadastro-section="pendencias-usuarios">
    <div class="section-header"><h2>Pendências de Usuários</h2></div>
    <div class="table-wrap">
      <table class="responsive-table cadastro-table cadastro-pending-table">
        <thead><tr>
          <th>Data</th><th>Chave</th><th>Nome Completo</th><th>Projetos</th><th>E-Mail</th><th>Ações</th>
        </tr></thead>
        <tbody id="userPendingBody"></tbody>
      </table>
    </div>
  </article>
  ```

### 4.2 `app.js`
- `loadUserPending({silent})` espelhando `loadPending()`: `fetcher("/api/admin/user-pending")` → render em
  `#userPendingBody` (Data formatada via helper existente; Projetos como lista; botões **Aprovar**/
  **Reprovar** com `data-id`); `applyResponsiveLabels`; vazio via `renderEmptyStateRow("userPendingBody", 6, …)`.
- Adicionar `loadUserPending()` nos mesmos pontos de `loadPending()`: `Promise.all` inicial, refreshes do
  **SSE** (`EventSource("/api/admin/stream")`) e refresh manual; incluir `#userPendingBody` no guard de
  edição (linha ~4965).
- Handler de clique em `#userPendingBody`: **Aprovar** → `postJson(".../approve")`; **Reprovar** →
  `confirm("Reprovar remove o cadastro. Confirmar?")` + `postJson(".../reject")`; depois `loadUserPending()`
  + `loadRegisteredUsers()`.

### 4.3 `styles.css`
- Reutiliza `.cadastro-pending-table`/`--pending`; ajustes mínimos só se a coluna E-Mail exigir largura.

---

## 5. App Kotlin (`checking_kotlin` — repo próprio; distribui via AAB)

### 5.1 Dados
- `data/dto`: `WebPasswordStatusResponse += pendingApproval=false`; `WebUserSelfRegistrationResponse +=
  status, pendingApproval=false, queueFull=false`, `projects` opcional. (Manter `explicitNulls=true`; enviar
  `""` não `null` p/ strings-com-default — contrato de serialização.)
- `domain/model/AuthStatus += pendingApproval=false` (+ transitório `queueFull=false`).
- `AuthRepositoryImpl`: mapear `pendingApproval` em `getStatus`/`login`; em `selfRegister`, mapear `status`
  → `pendingApproval`/`queueFull`.

### 5.2 ViewModel / estado
- `CheckUiState`: `val isAwaitingApproval get() = authStatus?.pendingApproval == true`.
- `submitSelfRegistration()` (novo bloco de sucesso): **sempre** `securePasswordStore.setPassword`; se
  `queueFull` → notificação vermelha `auth.registrationQueueFull`, não autentica, não entra em espera; se
  `pending` → `authStatus(pendingApproval=true, authenticated=false)` + notificação vermelha
  `auth.awaitingApproval` + fecha diálogo; **remover** `onAuthenticationSucceeded` desses caminhos.
- **Detecção de aprovação (polling):** enquanto `isAwaitingApproval`, *poll* leve periódico (≈20–30 s via
  `viewModelScope`+`delay`, cancelado ao sair) **e** revalidação no `onForegroundResume` (já existente):
  - `pending_approval==true` → continua em espera;
  - `found==true` (**aprovado**) → `login(chave, senhaArmazenada)` → `onAuthenticationSucceeded` → **dispara
    a atividade automática** (req. 7);
  - `found==false && pending_approval==false` (**reprovado**) → sai da espera e **volta ao estado de chave
    desconhecida SEM nenhum aviso** (decisão 4).
- **Reinício:** `getStatus` inicial reconstrói a espera a partir de `pending_approval`.
- **Auto-abrir formulário (decisão 3):** ao `getStatus` retornar `found=false && pending_approval=false`
  para uma chave de 4 chars recém-digitada, abrir o diálogo de cadastro automaticamente (uma vez por chave,
  respeitando `dismissedAssistanceForChave`).

### 5.3 UI
- `AuthRow`: novo `awaitingApproval: Boolean=false`; glow = `FieldGlow.Pending` (laranja) quando em espera e
  não autenticado; senão regra atual. Cumpre "campos laranja brilhante". `CheckScreen` passa
  `awaitingApproval = state.isAwaitingApproval`. A barra vermelha sai do `NotificationCard` com
  `notificationTone = Error` (→ `CheckingErrorVivid`).
- **Seta "Voltar" no formulário (decisão 3):** o diálogo de cadastro (`RegistrationDialog`) ganha, no canto
  superior esquerdo, um `IconButton` com `Icons.AutoMirrored.Filled.ArrowBack` que **fecha o diálogo** e
  volta à tela principal (limpa `selfRegistrationFields`; não altera a chave digitada). Acessibilidade:
  `contentDescription = t("settings.backButton")` (ou nova chave `auth.backToMain`).

### 5.4 i18n (6 idiomas)
- + `auth.awaitingApproval`, `auth.registrationQueueFull` (e, se necessário, `auth.backToMain`) em Pt, En,
  Zh, Ms, Id, Tl. `I18nTest` segue válido.

### 5.5 Garantias de não-regressão (app)
- Usuário em espera **não** autenticado → `canSubmit` falso (sem check-in manual); o motor de atividades
  automáticas já é *gated* por `isAuthenticated` → **não roda** p/ pendentes. Check-out automático,
  *skip-if-unchanged*, fila offline, geofencing, transporte e acidente: **inalterados**. `onAuthenticationSucceeded`
  segue idêntico; só deixa de ser chamado no autocadastro (que agora vai p/ espera). Login/troca de senha:
  inalterados.

---

## 6. Check Web (`sistema/app/static/check`) — **deploy pelo root monolito** (decisão 1)

> Servido em produção pelo monólito (`tscode.com.br/checking/user`). Deploy junto com o backend (`git push
> origin main`). Espelhar o comportamento do app Kotlin.

Hooks existentes confirmados: `authStatusEndpoint`/`authUserRegisterEndpoint`, `notificationState{message,
tone}` + `renderNotifications()`/`applyNotificationLine(el,msg,tone)`, classes `auth-field-pending`
(laranja)/`auth-field-authenticated` (verde) (toggle ~linha 1257), `registrationDialog`,
`requestRegistrationButton`, `userSelfRegistrationInProgress`.

### 6.1 `app.js`
- **Status:** ler `pending_approval` da resposta de `auth/status`; manter um `authState.pendingApproval`.
- **Campos laranja:** quando `pendingApproval`, forçar `auth-field-pending` (laranja) nos campos chave/senha
  (mesmo efeito do app).
- **Barra vermelha:** `notificationState` = mensagem `t('auth.awaitingApproval')` com o **tom de erro**
  (vermelho) já usado pelo `notificationState.tone`; `renderNotifications()`.
- **Envio do cadastro:** ao receber `status==="pending"` → entrar no estado de espera (laranja + vermelho),
  **não** autenticar; `status==="queue_full"` → barra vermelha `t('auth.registrationQueueFull')`, **não**
  autenticar.
- **Polling de aprovação:** enquanto em espera, revalidar `auth/status` periodicamente (reusar o mecanismo
  de status existente). `found==true` → autenticar com a senha em memória (ou re-login) e seguir o fluxo
  normal (dispara a atividade pertinente); `found==false && !pending_approval` → **reprovado**: voltar ao
  estado de chave desconhecida **sem aviso** (decisão 4).
- **Auto-abrir formulário (decisão 3):** quando a chave digitada é desconhecida, abrir `registrationDialog`
  automaticamente (já há `requestRegistrationButton`; manter como fallback).

### 6.2 `index.html` + `styles.css`
- **Seta "Voltar" (decisão 3):** botão de voltar no canto superior esquerdo do `registrationDialog` que o
  fecha e retorna à tela principal. Reutilizar estilo existente de botão de fechar/voltar de diálogo.
- Cache-busting: bump `?v=` dos assets alterados no `index.html` (regra do projeto p/ `static/check`).

### 6.3 i18n
- + `auth.awaitingApproval` e `auth.registrationQueueFull` no `i18n-dictionaries.js` (6 idiomas, fallback pt).

---

## 7. Invariantes a preservar e não-objetivos

**Preservar exatamente:**
1. `users` e todas as queries/contagens/sync/relatórios sobre ela (pendentes não entram em `users`).
2. Login, `register-password`, troca de senha, e `/auth/status` para usuários **já existentes**.
3. Pendências de **RFID** (`/api/admin/pending`, approve/reject) — só o **título** muda no HTML.
4. Motor de situações (check-in/out), check-out automático, *skip-if-unchanged*, fila offline/replay,
   geofencing, FGS, transporte, modo acidente — em ambos os clientes.
5. Para clientes **já autenticados** (app e web): nenhuma mudança de comportamento. A mudança afeta **apenas
   o caminho de autocadastro** de chave nova.
6. Contrato de serialização Kotlin↔API (campos aditivos; `explicitNulls=true`; `""` em vez de `null`).

**Não-objetivos (deste plano):**
- Notificar admin por e-mail sobre nova pendência (adendo futuro).
- Expiração automática de pendências antigas (housekeeping futuro).
- Aprovação de RFID (inalterada).

---

## 8. Rotina de testes (robusta — impedir que passe com falha)

### 8.1 Backend — pytest (`python -m pytest -q --ignore=tests/test_api_flow.py`)
- `tests/test_pending_user_registration_migration.py`: migration `0079` aplica em SQLite limpo; tabela,
  unique de `chave`, índice de `requested_at`.
- `tests/routers/test_web_self_registration_pending.py`:
  - **Flag on (padrão), qualquer cliente** (com e sem `X-Client`): `register-user` → **202**,
    `status=="pending"`, `authenticated==false`; **nenhum** `User` criado; 1 linha pendente; sem sessão;
    `client` gravado conforme header (`checking-android` ou `web`).
  - `/auth/status` depois → `pending_approval==true`, `found==false`.
  - **Duplicidade**: 2ª pendência mesma chave → 409; chave já `User` → 409; chave em
    `admin_access_requests` → 409.
  - **Fila cheia**: 300 pendências → próximo → **200** `status=="queue_full"`; contagem permanece 300.
  - **Validação**: payloads inválidos → 422, sem linha pendente.
  - **Flag off** (`CHECK_USER_APPROVAL_REQUIRED=false`): → **201**, `authenticated==true`, `User` criado
    (legado intacto) — para web **e** android.
- `tests/test_admin_user_pending_endpoints.py`:
  - `GET` sem sessão admin → 401; `User` perfil 0 → 403; admin perfil 1 → lista **escopada aos seus
    projetos**; admin em 2 projetos → vê união; **perfil 9 vê tudo**.
  - **Aprovar** → cria `User`+memberships (projetos corretos), remove pendente, some do `GET`, `/auth/status`
    vira `found==true`; **idempotente** se já existir `User`.
  - **Reprovar** → remove pendente, **nenhum** `User`; `/auth/status` → `found==false && pending_approval==false`.
  - `log_event` (`user_approve`/`user_reject`) gravado; ações ≤16 chars.
- **Baseline:** manter os 33 *fails* pré-existentes de `test_transport_ai_suggestion_commands.py` como único
  vermelho; **zero** novas falhas.

### 8.2 App Kotlin — `./gradlew compileDebugKotlin compileDebugAndroidTestKotlin testDebugUnitTest`
- `AuthMappingTest`: `getStatus`/`selfRegister` mapeiam `pending_approval`/`status` corretamente.
- `SelfRegistrationApprovalTest` (VM, mocks; `runTest`):
  - `pending` → `isAwaitingApproval==true`, notificação vermelha `auth.awaitingApproval`,
    `onAuthenticationSucceeded` **NÃO** chamado (motor não roda), senha armazenada.
  - `queue_full` → notificação vermelha `auth.registrationQueueFull`, não em espera, não autenticado.
  - **aprovação**: `getStatus`→`found=true` → `login` → `onAuthenticationSucceeded` (avaliação disparada).
  - **reprovação**: `found=false && !pending` → sai da espera, **sem** notificação (decisão 4).
  - **reinício**: `getStatus` inicial com `pending_approval=true` → espera reconstruída.
- Guards: usuário pendente/não autenticado **não** dispara o motor (estender testes de gate existentes).
- Instrumentado (opcional, estilo `SettingsDialogSmokeTest`): `AuthRow awaitingApproval=true` → glow laranja;
  diálogo de cadastro tem a seta "Voltar" que fecha e volta à tela principal.
- `I18nTest` verde; as 2–3 chaves novas nos 6 dicionários. Contagem ≥ baseline + novos, 0 falhas; **nunca**
  `connectedAndroidTest`.

### 8.3 Check Web — JS (harness `tests/*.test.js` na raiz, ex.: `check_user_location_ui.test.js`)
- Novo `tests/check_user_approval_ui.test.js`:
  - `auth/status` com `pending_approval=true` → campos com classe `auth-field-pending` (laranja) e
    `notificationState` com mensagem `auth.awaitingApproval` em tom de erro (vermelho); **não** autenticado.
  - resposta de `register-user` `queue_full` → barra `auth.registrationQueueFull` (vermelho).
  - aprovação (`found=true` no próximo status) → segue p/ estado autenticado.
  - reprovação (`found=false && !pending`) → volta a desconhecido **sem** aviso.
  - auto-abertura do `registrationDialog` em chave desconhecida; botão "Voltar" fecha o diálogo.
- Rodar a suíte JS existente p/ garantir não-regressão (`check_transport_request_history`,
  `check_user_location_ui`).

### 8.4 admin2 (sem harness JS) — verificação manual + cobertura via API
- Checklist: título "Pendências de RFID"; nova tabela "Pendências de Usuários" acima; colunas corretas;
  pendência aparece após autocadastro; **Aprovar** some e cria usuário; **Reprovar** some sem criar;
  atualização via SSE; **espelho** `deploy/docker/admin2-web/` idêntico.

### 8.5 Matriz de não-regressão (rodar antes de fechar)
- Login normal (app+web), troca de senha, pendências **RFID**, check-in/out automático e manual, fila
  offline, transporte, acidente, e usuários **já autenticados** → inalterados.

---

## 9. Sequência de implementação (segura e incremental)

1. **Backend atrás da flag** (default on): modelo + migration `0079` + config + schemas + `register-user`
   (flag/cap) + `/auth/status` + endpoints admin + helper `create_user_from_registration`. Testes 8.1 verdes.
2. **Check Web** (mesmo repo root): UI de espera/fila/auto-abrir/voltar + i18n + cache-busting. Testes 8.3.
3. **Deploy backend + Check Web** — `git push origin main` **somente após aprovação humana**; rodar migration
   em prod (pipeline); validar `Deploy OceanDrive` verde + `curl /api/health`.
4. **admin2** — HTML/JS/CSS + **espelho** `deploy/docker/admin2-web/`; deploy pela pipeline do repo pai;
   validar tabela e ações.
5. **App Kotlin** — DTO/repo/AuthStatus/VM/UI (incl. seta Voltar)/i18n/polling + testes 8.2; gerar AAB (novo
   `versionCode`/`versionName`) e publicar via Play Store — **sem** commit/push/deploy sem aprovação.
6. **Validação ponta-a-ponta** (app + web + admin): autocadastro → espera (laranja+vermelho) → aprovação →
   autentica e processa check-in/out; reprovação → some do banco, cliente volta ao normal sem aviso; fila
   cheia (300) → mensagem vermelha correta; seta "Voltar" funciona.

**Rollback rápido:** `CHECK_USER_APPROVAL_REQUIRED=false` em produção restaura o autocadastro imediato sem
rollback de código (tabela/endpoints podem ficar inertes).

---

## 10. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Mudança no `register-user` afetar usuários **já autenticados** | A mudança só toca o caminho de autocadastro de chave nova; testes de regressão (8.1/8.5). |
| Esquecer o **espelho admin2** → admin não atualiza em prod | Passo 4 obriga espelhar `deploy/docker/admin2-web/`; checklist 8.4. |
| **Corrida** no limite de 300 / chave duplicada | Unique de `chave` + `COUNT`+`INSERT` na mesma transação + revalidação pós-insert. |
| Cliente **preso** em "aguardando" se SSE/aprovação falhar | Estado derivado do servidor + polling + revalidação no foreground; nada depende de push. |
| Check Web ficar inconsistente com o app | §6 espelha exatamente o comportamento; testes JS (8.3). |
| Migration em Postgres (prod) | `0079` testada em SQLite limpo; aditiva (tabela nova); aplicada pela pipeline. |
| Regressão silenciosa no motor/check-out | Suíte 8.5 + testes de gate (pendente não dispara motor). |

---

## 11. Decisões confirmadas pelo dono do produto

1. **Abrangência:** **sistema inteiro** — a aprovação vale para o app Android **e** para o Check Web
   (fechar a "porta web" contra cadastros maliciosos). → §1.3, §6.
2. **Listagem no admin:** **escopada por projeto** — cada admin vê as pendências dos seus projetos; admin em
   vários projetos vê a união de todos. → §2.5.
3. **Formulário:** **abrir automaticamente** ao digitar chave desconhecida, **com seta "Voltar"** no canto
   superior esquerdo para retornar à tela principal (caso a chave já cadastrada tenha sido digitada errada).
   → §5.2/5.3, §6.1/6.2.
4. **Reprovação:** **nenhum aviso** ao usuário reprovado — o cliente apenas volta ao estado de chave
   desconhecida. → §5.2, §6.1.
