# plan005 — Adicionar telefone de contato (cod_pais + contato) ao cadastro de usuário

> **Status:** proposta / plano de implementação. Nada implementado ainda.
> **Autor do plano:** levantamento assistido por IA (leitura completa de web, admin2, API, banco e app Kotlin).
> **Regra de ouro deste plano:** o sistema está funcionando **perfeitamente**. Toda mudança aqui é **aditiva** — **não removemos nada**. Cada etapa foi desenhada para ser reversível e para não tocar em nenhum fluxo existente.

---

## 0. Decisões confirmadas pelo solicitante (base do plano)

Estas 4 decisões foram confirmadas e **definem o escopo**:

| # | Decisão | Resposta confirmada | Consequência no plano |
|---|---|---|---|
| D1 | O `User.email` também alimenta os **e-mails de emergência** do Modo Acidente (envia para o e-mail de cada colega do projeto). O que fazer? | **Manter e-mail E adicionar telefone** ("não remove nada; telefone vira campo ADICIONAL") | O plano é **100% aditivo**. O e-mail permanece em TODAS as camadas (banco, API, cadastro web/Kotlin, coluna do admin). O telefone é acrescentado ao lado. |
| D2 | O telefone deve ser obrigatório? (e-mail hoje é opcional) | **Opcional** (paridade com e-mail) | Sem quebra de compatibilidade com apps Android já publicados; cadastros sem telefone continuam válidos. |
| D3 | A coluna do admin deve ser editável? | **Editável inline** (como o e-mail é hoje) | A nova coluna CONTATO no admin terá seletor de país + campo com máscara, editável em modo de edição da linha. |
| D4 | Cobertura de países / máscara | **Lista completa (~240 países)**, sem bibliotecas externas | Dataset curado de códigos de discagem para o seletor; máscaras específicas para um subconjunto conhecido (BR/SG/CN/NL + os que quisermos detalhar) e **fallback genérico** (E.164, até 15 dígitos) para o restante. |

### 0.1 Reconciliação com o pedido original ("substituir")

O pedido original falava em **substituir** o e-mail por `cod_pais` + `contato`. A decisão **D1** ("Manter e-mail E adicionar telefone") **conscientemente sobrepõe** esse "substituir" — porque o `User.email` é **carga viva** do fluxo de e-mail de emergência (ver §1). Portanto:

- **NÃO** removemos o campo e-mail do formulário de cadastro (web nem Kotlin).
- **NÃO** removemos a coluna "Email" da tabela do admin.
- **Adicionamos** os campos `cod_pais` + `contato` (telefone) **ao lado** do e-mail em todas as telas, e **adicionamos** a coluna "Contato" **ao lado** da coluna "Email" no admin.

> ⚠️ **Ponto a confirmar antes de codar:** se, apesar de D1, você quiser que as **telas** (formulário de cadastro e coluna do admin) **deixem de exibir** o e-mail — mantendo a coluna `email` só no banco para o fluxo de emergência — isso é uma variação pequena descrita na **§11 (Variação B)**. O plano principal abaixo assume o additive puro (e-mail visível + telefone visível), que é o de menor risco e o que a resposta literal de D1 indica.

---

## 1. Descoberta crítica: por que NÃO removemos o e-mail

Durante o levantamento encontramos uma dependência **não óbvia** e **carga viva**:

- **`sistema/app/services/email_sender.py:29-77`** (`queue_help_request_emails`): quando um usuário reporta `status='help'` no Modo Acidente, o sistema busca **todos os usuários do mesmo projeto** e envia a cada um um e-mail de alerta **para o endereço `recipient.email`** (linhas `50` e `67`). Se `recipient.email` estiver vazio, grava um `EmailDeliveryLog` com `delivery_status="failed"` e `error_message="Missing recipient email"` (linhas `50-63`).

**Implicação:** `User.email` **não é apenas um dado de cadastro** — é o endereço de destino dos alertas de emergência. Removê-lo (ou parar de coletá-lo) faria novos usuários **deixarem de receber** os e-mails de emergência silenciosamente. Por isso D1 = manter e-mail. **Este fluxo NÃO é alterado por este plano** (ver §10, "NÃO TOCAR").

> O telefone novo **não** é conectado ao fluxo de emergência neste plano (essa seria a opção "Twilio/SMS", não escolhida). Fica registrado como possível trabalho futuro na §12.

---

## 2. Modelo de dados

### 2.1 Duas colunas novas, em duas tabelas

Adicionar em **`User`** (`sistema/app/models.py`, logo após `email` na linha 91) e em **`PendingUserRegistration`** (`sistema/app/models.py`, após `email` na linha 292):

```python
cod_pais: Mapped[str | None] = mapped_column(String(8), nullable=True)
contato:  Mapped[str | None] = mapped_column(String(32), nullable=True)
```

- **`cod_pais`** — código de discagem do país, string **com** o `+`. Ex.: `"+55"`, `"+65"`, `"+86"`, `"+31"`. `String(8)` é folgado (maior código = 4 dígitos + `+`).
- **`contato`** — número **nacional**, **apenas dígitos**, sem separadores/máscara. Ex.: `"11999998888"`. `String(32)` é folgado (máx. E.164 = 15 dígitos).
- Ambas **`nullable=True`**, **sem** `unique`, **sem** `index`, **sem** `server_default` (linhas existentes ficam `NULL`, coerente com a opcionalidade — D2).

**Por que dois campos e não um só:** o solicitante pediu explicitamente `cod_pais` + `contato`. Guardar o código separado facilita: (a) escolher a máscara na exibição/edição, (b) montar o "número completo" no admin (`cod_pais + " " + contato_formatado`).

**Por que guardar `contato` só com dígitos:** segue o estilo da casa — `sanitizeChave` e o listener de ZIP guardam o valor **normalizado** e formatam só na exibição (ver `app.js:2826-2831` e `app.js:7743-7750`). A máscara é responsabilidade de **UI**, não de armazenamento. Isso evita divergência de formatação entre plataformas.

### 2.2 Identificação do país pelo código (D4) — nuance dos códigos compartilhados

O seletor mostra **países** (nome + bandeira + código). Na seleção, guardamos o **código de discagem** em `cod_pais`. Alguns códigos são compartilhados por vários países (ex.: `+1` = EUA/Canadá/vários; `+7` = Rússia/Cazaquistão). Como guardamos só o código:

- Na exibição/edição reconstruímos a máscara pela **tabela indexada por código de discagem** (máscara canônica por código; para `+1` usamos o padrão NANP `3-3-4`, etc.).
- Isso atende exatamente o pedido ("identificar o país **pelo código** e alterar a máscara **conforme o código**").
- **Trade-off aceito:** não distinguimos EUA de Canadá após salvar (mesma máscara), o que é irrelevante para exibição. Se um dia for necessário distinguir país exato, acrescenta-se depois uma coluna `iso_pais` — **fora do escopo** deste plano (mantemos os dois campos pedidos).

### 2.3 Migration Alembic

- **Última migration atual:** `0080_add_event_time_indexes.py`. **Nova:** `0081_add_user_phone_contact.py` (`down_revision = "0080"`).
- Usar **`op.batch_alter_table`** (compat SQLite em dev), no padrão de `0018` e `0079`:

```python
def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("cod_pais", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("contato",  sa.String(length=32), nullable=True))
    with op.batch_alter_table("pending_user_registrations") as batch_op:
        batch_op.add_column(sa.Column("cod_pais", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("contato",  sa.String(length=32), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table("pending_user_registrations") as batch_op:
        batch_op.drop_column("contato")
        batch_op.drop_column("cod_pais")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("contato")
        batch_op.drop_column("cod_pais")
```

- **Sem backfill** (não há como derivar telefone do e-mail; linhas existentes ficam `NULL` — aceitável por D2).
- **Idempotência/segurança:** a migration é puramente aditiva e reversível. Em produção (Postgres) `add_column` de coluna nullable é operação online barata (sem reescrita de tabela, sem lock longo).
- **Teste de migration:** criar `tests/test_user_phone_contact_migration.py` no padrão de `tests/test_pending_user_registration_migration.py` — sobe a migration em SQLite limpo e verifica que `cod_pais`/`contato` existem em `users` e `pending_user_registrations`.

---

## 3. Design da máscara de telefone (país → formato)

### 3.1 Dataset de países (fonte única + cópias por plataforma)

Como **não há build/bundler** (web e admin2 são vanilla JS servidos estáticos; ver §6.1), o dataset é **duplicado** por plataforma, mas mantido a partir de **uma fonte canônica** para evitar divergência.

- **Fonte canônica (novo arquivo, versionado):** `docs/plans/plan005-countries.json` — a lista completa (~240) de `{ iso2, name, dial, groups, min, max }`. Serve de referência para gerar/manter as cópias.
- **Cópias derivadas (4 cópias físicas):**
  1. Check Web: novo arquivo `sistema/app/static/check/phone-format.js` (dataset + helpers).
  2. admin2 (origem): **inline** dentro de `sistema/app/static/admin2/app.js` (ver §6.3 — o espelho de deploy serve um conjunto fixo de 3 arquivos; **não** adicionar arquivo novo lá).
  3. admin2 (espelho): `deploy/docker/admin2-web/app.js` (byte-idêntico ao item 2).
  4. Kotlin: novo arquivo `.../domain/clientstate/PhoneCountries.kt` (dataset + helpers).
- **Checklist de sincronização** (ver §9): qualquer mudança no dataset deve ser replicada nas 4 cópias.

**Esquema de cada país:**

```jsonc
{
  "iso2": "BR",
  "name": "Brasil",           // exibido no seletor (rótulo localizável opcional; ver §3.4)
  "dial": "55",               // sem '+'; a UI prefixa '+'
  "groups": [2, 5, 4],        // tamanhos dos grupos do número nacional; null => genérico
  "min": 11, "max": 11        // limites de dígitos do número nacional (validação)
}
```

**Subconjunto com máscara específica (confirmado nos exemplos):**

| iso2 | name | dial | groups | min/max | resultado |
|---|---|---|---|---|---|
| BR | Brasil | 55 | [2,5,4] | 11/11 | `+55 00 00000 0000` |
| SG | Singapura | 65 | [4,4] | 8/8 | `+65 0000 0000` |
| CN | China | 86 | [3,4,4] | 11/11 | `+86 000 0000 0000` |
| NL | Holanda | 31 | [1,4,4] | 9/9 | `+31 0 0000 0000` |

**Fallback genérico** (para os demais ~236 países): `groups: null`, `min: 4`, `max: 15` (limites E.164). Sem agrupamento fixo — o número é exibido como bloco único (ou agrupado de 3 em 3 como estética neutra, à escolha na implementação). Mantém "qualquer país" funcionando com máscara específica onde conhecida.

> **Nota sobre a lista completa:** os ~240 pares `iso2/name/dial` saem de uma referência padrão (ISO 3166-1 alpha-2 + códigos ITU-T E.164). `groups`/`min`/`max` específicos só para o subconjunto que decidirmos detalhar; o resto usa o fallback. Podemos ampliar o subconjunto detalhado incrementalmente sem mudar a arquitetura.

### 3.2 Formato de armazenamento vs. exibição

- **Guardado:** `cod_pais = "+55"`, `contato = "11999998888"` (dígitos).
- **Exibido (número completo):** `formatPhone(contato, countryByDial("+55"))` → `"+55 11 99999 8888"`.
- Função pura `formatPhone(digitsRaw, country)`:
  1. `digits = onlyDigits(raw).slice(0, country.max)`
  2. se `country.groups` for `null` → retorna `digits` (bloco único);
  3. senão fatia `digits` conforme `groups` e junta com espaço; prefixa `country.dial`.

### 3.3 Validação (campo OPCIONAL — D2)

Regra única, idêntica nos 3 clientes e no servidor (servidor mais frouxo — ver §4.3):

- **Vazio permitido:** se `contato` (dígitos) estiver vazio → `cod_pais` e `contato` são gravados como `NULL` (par vazio = sem telefone). Não erra.
- **Se preenchido:** exige `cod_pais` válido (`^\+\d{1,4}$`) **e** `length(digitos)` dentro de `[min, max]` do país (para país específico é exato; para genérico é 4–15).
- Mensagem de erro i18n: nova chave `registrationDialog.phoneInvalid` (e equivalentes). Segue o mesmo padrão do atual `emailInvalid` (foca o campo e mostra o texto).

### 3.4 i18n dos rótulos

Novas chaves (em **todas as 6 línguas**, web e Kotlin): `countryCodeLabel`, `phoneLabel`, `phonePlaceholder`, `phoneInvalid`. (Nomes de país no seletor: por simplicidade, exibir o `name` do dataset em inglês/PT nativo — **não** traduzir 240 nomes agora; se quiser localizar, é incremento futuro.)

---

## 4. Backend (FastAPI + Pydantic + SQLAlchemy)

Todas as mudanças são **aditivas**: cada schema/handler **ganha** dois campos; nenhum campo existente (incl. `email`) é alterado.

### 4.1 Models — `sistema/app/models.py`

- `User` (após linha 91): + `cod_pais`, `contato` (§2.1).
- `PendingUserRegistration` (após linha 292): + `cod_pais`, `contato`.

### 4.2 Schemas — `sistema/app/schemas.py`

| Classe | Linha da classe | Ação | Campo do e-mail (referência, NÃO mexer) |
|---|---|---|---|
| `AdminUserUpsert` (request criar/editar) | 521 | + `cod_pais: str \| None = Field(default=None, max_length=8)` e `contato: str \| None = Field(default=None, max_length=32)` + validador `validate_phone` | `email` linha 534 (mantido) |
| `AdminUserListRow` (response lista admin) | 1312 | + `cod_pais: Optional[str] = None`, `contato: Optional[str] = None` | `email` linha 1326 (mantido) |
| `WebUserSelfRegistrationRequest` (request cadastro web) | 3871 | + os dois campos + validador `validate_phone` | `email` linha 3875 (mantido) |
| `AdminUserPendingRow` (response lista pendências) | 3993 | + os dois campos | `email` linha 3999 (mantido) |

**Novo validador reutilizável** (perto de `_normalize_optional_compact_text`, ~linha 108): 

```python
def _normalize_optional_cod_pais(value): ...  # strip, valida ^\+?\d{1,4}$, normaliza para "+NN", None se vazio
def _normalize_optional_contato(value): ...   # strip -> só dígitos, None se vazio, ValueError se >32
```

Aplicar via `@field_validator("cod_pais", mode="before")` / `@field_validator("contato", mode="before")` nas duas classes de **request** (`AdminUserUpsert`, `WebUserSelfRegistrationRequest`). As classes de **response** (`AdminUserListRow`, `AdminUserPendingRow`) não precisam de validador.

> **Importante (encodeDefaults do Kotlin):** declarar os campos como `default=None` garante que o cliente Kotlin (que usa `encodeDefaults=true` + `explicitNulls=true`, ver `di/NetworkModule.kt:42-53`) possa enviar `null` sem cair no 422 "Field required" — exatamente como o `email` funciona hoje.

### 4.3 Validação do servidor: proposital​mente frouxa

O servidor **NÃO** carrega o dataset de ~240 países (evita 5ª cópia da tabela e desalinho). Ele valida apenas **forma + comprimento genérico**:

- `cod_pais`: casa `^\+\d{1,4}$` (após normalizar).
- `contato`: 4–15 dígitos.

A máscara/relação país-específica fica só nos **3 clientes** (web/admin2/Kotlin), coerente com o fato de a validação atual de e-mail no servidor também ser rasa. Isso reduz a superfície de mudança no backend e o risco.

### 4.4 Handlers — `sistema/app/routers/admin.py`

Cada ponto abaixo **ganha** `cod_pais`/`contato` ao lado do `email` já existente (nenhuma linha de e-mail é removida):

| Linha | Local | Mudança |
|---|---|---|
| 3849 | `list_users` monta `AdminUserListRow(... email=row.email ...)` | + `cod_pais=row.cod_pais, contato=row.contato` |
| 3985 | `upsert_user` (edição) `user.email = payload.email` | + `user.cod_pais = payload.cod_pais; user.contato = payload.contato` |
| 4018 | `upsert_user` (criação) `User(email=payload.email ...)` | + `cod_pais=payload.cod_pais, contato=payload.contato` |
| 4174 | `list_user_pending` monta `AdminUserPendingRow(... email=row.email ...)` | + `cod_pais=row.cod_pais, contato=row.contato` |
| 4210 | `approve_user_pending` chama `create_user_from_registration(... email=pending.email ...)` | + `cod_pais=pending.cod_pais, contato=pending.contato` |

### 4.5 Handlers — `sistema/app/routers/web_check.py`

- **`create_user_from_registration`** (linha 452; assinatura em 458; construção do `User` em 468-484): + parâmetros `cod_pais: str | None`, `contato: str | None` e atribuí-los no `User(...)` (ao lado de `email=email` na linha 478).
- **`register_web_user`** (linhas 503-586):
  - Ramo criação direta (linha 528-535): passar `cod_pais=payload.cod_pais, contato=payload.contato`.
  - Ramo fila de aprovação (linha 556-566, `PendingUserRegistration(...)`): + `cod_pais=payload.cod_pais, contato=payload.contato`.

### 4.6 Construtores `User(email=None)` fora do cadastro — NÃO exigem mudança

Existem chamadas `User(email=None)` em `admin.py:1910`, `admin.py:2960`, `provider.py:88`, `services/admin_auth.py:189` e ~40 fixtures de teste. Como as novas colunas são **nullable com default None**, esses construtores **continuam válidos sem alteração** (os campos simplesmente ficam `NULL`). **Não** é preciso tocá-los — reforça a escolha aditiva.

---

## 5. Check Web (SPA vanilla — `sistema/app/static/check/`)

### 5.1 `index.html`
- Formulário de cadastro (`#registrationForm`, campo de e-mail em `383-393`): **manter** o `<label>`/`<input id="registrationEmailInput">` e **adicionar acima ou abaixo** um bloco novo:
  - `<select id="registrationCountryCodeSelect">` (opções geradas via JS a partir do dataset — bandeira/nome/`+dial`), e
  - `<input id="registrationPhoneInput" type="tel" inputmode="numeric" autocomplete="tel-national" maxlength="24">` (com máscara aplicada por listener).
- Registrar as novas tags `<script>` e **bump de cache-buster** (§8.3): os `?v=N` das linhas `820-827` precisam subir em `app.js`, `i18n-dictionaries.js` e no novo `phone-format.js`.

### 5.2 `phone-format.js` (novo)
- Dataset (§3.1) + `onlyDigits`, `countryByDial`, `formatPhone`, `isValidPhone`. Exposto em `window.CHECKING_PHONE` (padrão dos outros helpers globais).

### 5.3 `app.js`
- Refs dos novos elementos (perto de `registrationEmailInput` em `69,146`).
- Popular o `<select>` de países no boot do formulário; default sugerido: Brasil (`+55`) — ajustável.
- Listener `input` no telefone (espelhando o listener de ZIP em `7743-7750`): normaliza para dígitos, aplica `formatPhone` conforme país selecionado, reescreve o valor.
- Listener `change` no `<select>`: reformata o telefone ao trocar de país.
- No submit (`5089-5133` faz a validação; `5167-5181` monta o corpo): **manter** `email: email || null` e **adicionar** ao corpo `cod_pais: <dial ou null>, contato: <digitos ou null>`; validar telefone com `isValidPhone` (opcional — só valida se preenchido) e, em erro, focar o campo e mostrar `t('registrationDialog.phoneInvalid')`.
- Rótulos i18n dos novos campos (perto de `1479` e `1531-1533`).

### 5.4 `i18n-dictionaries.js`
- Em **cada uma das 6 línguas**, adicionar `countryCodeLabel`, `phoneLabel`, `phonePlaceholder`, `phoneInvalid` ao bloco `registrationDialog`. Linhas de referência dos blocos (abrem em): pt `98`, en `616`, zh `1078`, ms `1384`, id `1690`, tl `1996`. **Não** remover as chaves de e-mail existentes.

---

## 6. Admin (admin2 — `sistema/app/static/admin2/` + espelho `deploy/docker/admin2-web/`)

### 6.1 ⚠️ Restrição de deploy — dois espelhos byte-idênticos
`sistema/app/static/admin2/{app.js,index.html,styles.css}` e `deploy/docker/admin2-web/{app.js,index.html,styles.css}` são **byte-idênticos** (md5 confirmado) e servidos por nginx no container admin2. **Toda** edição abaixo deve ser aplicada **nas duas cópias**, mantendo-as idênticas. O deploy do admin2 é por **push no sub-repo** (`sistema/app/static/admin2`) que auto-deploya `/checking/admin` — ver memória `admin2_deploy_pipeline` e `admin2_mirror_sync`.

### 6.2 Tabela "Usuários Cadastrados" — adicionar coluna CONTATO (editável, D3)
- **Cabeçalho** — `index.html:525`: inserir `<th>Contato</th>` entre `<th>Email</th>` e `<th>Ações</th>`. **Manter** `<th>Email</th>`.
- **Linha** — `app.js` `makeRegisteredUserRow` (`4737`), célula do e-mail em `4752` (mantida): **adicionar** logo após uma nova célula com **dois** inputs inline (padrão dos demais, `disabled` até editar):
  - `<select class="inline user-cod-pais" disabled>...</select>` (opções do dataset)
  - `<input class="inline user-contato" inputmode="numeric" maxlength="24" value="${formatPhone(user.contato, countryByDial(user.cod_pais))}" disabled />`
- **Toggle de edição** — `toggleUserRowEditing` (`5032,5044`): incluir `.user-cod-pais` e `.user-contato` na habilitação/desabilitação (junto de `.user-email`).
- **Salvar** — `saveRegisteredUser` (`6187` lê e-mail; `6200-6210` monta o POST): ler os novos campos, normalizar (dígitos + dial) e **adicionar** ao corpo `cod_pais`, `contato` (mantendo `email: email || null`).
- **Dataset + helpers no admin2:** inline em `app.js` (§3.1, cópia 2/3) — **não** criar arquivo novo (o espelho serve apenas 3 arquivos).

### 6.3 CSS — `styles.css`
- Adicionar regra de largura/estilo para `.user-contato` e `.user-cod-pais` espelhando `.user-email` (`1078`: `min-width`; `1110`: `nowrap/overflow`).
- ⚠️ Conferir as regras `nth-child` de largura (`1122-1124` cobrem colunas 1/3/4). A coluna "Ações" passa de índice 9 → 10; verificar que nenhuma regra `nth-child`/`last-child` de largura quebra com a coluna extra. Ajustar se necessário.

### 6.4 Tabela "Pendências de Usuários" (consistência — recomendado, secundário)
`makeUserPendingRow` (`app.js:4728`) exibe `row.email`; cabeçalho `index.html:380` ("E-Mail"). Para consistência, **adicionar** uma coluna "Contato" (somente leitura, exibindo `formatPhone`), já que os pendentes agora carregam `cod_pais`/`contato`. **Opcional** — se preferir manter o escopo mínimo, deixar para depois; não bloqueia o principal.

### 6.5 Sem impacto em busca/ordenação
Não há ordenação/filtro/busca sobre a coluna de e-mail (`populateReportsSearchOptions` usa só `chave`/`nome`); `applyResponsiveLabels` copia o texto do `<th>` automaticamente, então o `data-label` do "Contato" é tratado sozinho. Nada a fazer aqui além de adicionar a coluna.

---

## 7. App Kotlin (`checking_kotlin/`)

Todas aditivas; o campo de e-mail permanece.

### 7.1 DTO — `data/dto/AuthDtos.kt`
- `WebUserSelfRegistrationRequest` (24-32): **manter** `email` (29); **adicionar**:
  ```kotlin
  @SerialName("cod_pais") val codPais: String? = null,
  val contato: String? = null,
  ```
  (`@SerialName` para casar a chave JSON `cod_pais`; `contato` já casa.)

### 7.2 Estado de UI — `presentation/check/CheckUiState.kt`
- `SelfRegistrationFields` (email em `48`): + `val codPais: String = "+55"` (default sugerido), `val contato: String = ""`.

### 7.3 ViewModel — `presentation/check/CheckViewModel.kt`
- Handlers novos ao lado de `onRegEmailChanged` (`882-883`): `onRegCountryChanged(dial)` e `onRegContatoChanged(v)` (este normaliza para dígitos + cap por `max` do país, análogo a `sanitizeSettingsChave`).
- No `submitSelfRegistration` (`897-946`): validar telefone (opcional; só se preenchido) com mensagem `registrationDialog.phoneInvalid`; passar `codPais`/`contato` ao `authRepository.selfRegister(...)` (linha 940-947), mantendo `email = email.ifEmpty { null }`.

### 7.4 Repositório — `domain/repository/AuthRepository.kt` + `data/repository/AuthRepositoryImpl.kt`
- Interface (`selfRegister`, param `email` em `19`): + `codPais: String?`, `contato: String?`.
- Impl (`102,111`): construir `WebUserSelfRegistrationRequest(... codPais = codPais?.takeIf{it.isNotBlank()}, contato = contato?.takeIf{it.isNotBlank()} ...)` (mesmo padrão do `email`).

### 7.5 Dataset/máscara — `domain/clientstate/PhoneCountries.kt` (novo)
- Dataset (§3.1, cópia 4/4) + `countryByDial`, `formatPhone`, `isValidPhone`, `onlyDigits`.
- **Testes unit** em `ClientStateFunctionsTest` (ou novo `PhoneCountriesTest`): casos BR/SG/CN/NL + fallback genérico + vazio.

### 7.6 UI — `presentation/components/SelfRegistrationDialog.kt`
- Assinatura (`44-55`): manter `onEmailChanged`; adicionar `onCountryChanged: (String) -> Unit`, `onContatoChanged: (String) -> Unit`.
- Adicionar, ao lado do campo de e-mail (`119-132`):
  - Seletor de país: `ExposedDropdownMenuBox` (Material3) listando bandeira/nome/`+dial`.
  - Campo de telefone: `OutlinedTextField` com `KeyboardType.Phone` e uma `PhoneVisualTransformation(country)` (o componente da casa `GlowField/LabeledField` já aceita `visualTransformation`, mas o formulário usa `OutlinedTextField`, que também suporta `visualTransformation` nativamente).
  - `PhoneVisualTransformation`: `filter()` retorna a string agrupada + `OffsetMapping` (offset original → offset exibido contando os espaços inseridos). O valor **guardado** continua só-dígitos; o prefixo `+dial` é adornado à esquerda (não editável) para simplificar o offset.
- **Wiring** em `presentation/check/CheckScreen.kt` (~`480`, onde `onEmailChanged = vm::onRegEmailChanged`): ligar os dois novos callbacks.

### 7.7 i18n — `i18n/dictionaries/{Pt,En,Zh,Ms,Id,Tl}.kt`
- Adicionar `countryCodeLabel`, `phoneLabel`, `phonePlaceholder`, `phoneInvalid` ao bloco `registrationDialog` de **cada** arquivo (linhas do bloco de e-mail: Pt `179-188`, En `177-186`, Zh/Ms/Id/Tl `107-116`). **Não** remover as chaves de e-mail.

### 7.8 Testes Kotlin
- `data/repository/AuthMappingTest.kt`: cobrir o mapeamento `codPais/contato` → DTO (hoje só testa `email=null`).
- Smoke de UI `SelfRegistrationApprovalUiSmokeTest.kt` (`112,137`): passar os novos callbacks `onCountryChanged={}`, `onContatoChanged={}`.
- Unit da máscara (§7.5).

### 7.9 Publicação
- Bump de `versionCode`/`versionName` (memória `kotlin_play_publishing`: último = 1.6.3/22 → próximo ≥ 23). Gerar AAB e subir manual. **Serialização:** manter `explicitNulls=true`/`encodeDefaults=true` (memória `kotlin_api_serialization_contract`).

---

## 8. Ordem de implementação e deploy

### 8.1 Sequência recomendada (cada etapa é independente e segura por ser aditiva)
1. **Banco + backend primeiro** (migration `0081` → models → schemas → handlers). Deploy da API. Como tudo é opcional/nullable e o servidor ignora campos extras (Pydantic default `extra='ignore'`), **clientes antigos continuam funcionando** e **novos campos passam a ser aceitos**.
2. **Check Web** (mesmo container/monólito da API; deploy por root/oceandrive — memória `checkweb_public_served_by_monolith`). Requer **bump de cache-buster** (§8.3).
3. **admin2** (as duas cópias; deploy por push no sub-repo — §6.1).
4. **Kotlin** (release na Play Store; roll-out gradual).

> Ordem crítica: **backend antes dos clientes**. Um cliente enviando `cod_pais/contato` antes de a coluna/coluna existir apenas teria o campo ignorado — mas para persistir de fato, o backend precisa estar no ar primeiro.

### 8.2 Compatibilidade retroativa (apps já publicados)
- Campos **opcionais** (D2) + `WebUserSelfRegistrationRequest` **sem** `extra='forbid'` (confirmado) ⇒ apps Android antigos (que não enviam telefone) **não** recebem 422; seus cadastros seguem válidos com telefone `NULL`.
- Novos apps enviam `cod_pais/contato` e continuam enviando `email` (nada removido).

### 8.3 Cache-busting do Check Web (⚠️ fácil de esquecer)
`index.html` carrega os JS com `?v=N` (linhas `820-827`). Ao alterar `app.js`, `i18n-dictionaries.js` e adicionar `phone-format.js`, **subir os `?v=`** correspondentes, senão o navegador serve JS em cache e o formulário quebra parcialmente.

---

## 9. Checklist mestre "mudar em conjunto" (nada pode ficar dessincronizado)

| Item | Arquivo(s) | Obs |
|---|---|---|
| Colunas DB | `models.py` (User ~91, Pending ~292) + migration `0081` | aditivo, nullable |
| Schemas | `schemas.py` 521, 1312, 3871, 3993 (+ validadores ~108) | manter os `email` |
| Handlers | `admin.py` 3849, 3985, 4018, 4174, 4210; `web_check.py` 452-484, 533, 561 | manter os `email` |
| Check Web | `index.html` (383-393, scripts 820-827), novo `phone-format.js`, `app.js` (69,146,1479,1531,5089-5181,7743±), `i18n-dictionaries.js` (6 blocos) | bump `?v=` |
| admin2 ×2 espelhos | `index.html` 525 (+380 opc.), `app.js` 4728(opc.),4737/4752/5032/5044/6187/6209 + dataset inline, `styles.css` 1078/1110/nth-child | **byte-idênticos** |
| Kotlin | `AuthDtos.kt` 24-32, `CheckUiState.kt` 48, `CheckViewModel.kt` 882/897-946, `AuthRepository.kt` 19, `AuthRepositoryImpl.kt` 102/111, novo `PhoneCountries.kt`, `SelfRegistrationDialog.kt` 44-132, `CheckScreen.kt` ~480, i18n ×6 | manter `email` |
| Dataset países (4 cópias) | `docs/plans/plan005-countries.json` (fonte), `phone-format.js`, admin2 `app.js` ×2, `PhoneCountries.kt` | manter sincronizado |
| Testes | pytest (endpoint self-reg, admin upsert, pending approve, migration) + Kotlin (mapping, máscara, smoke) | |

---

## 10. NÃO TOCAR (e-mails/telefones não relacionados)

Estes contêm "email"/"phone" mas **não** têm relação com o contato do usuário. **Não alterar**:

- `Project.email_local_emergency` — `models.py:28`; schemas `1097/1181`; admin `1430/2736-2737`; admin2 `#ecEmailEmergency` (`index.html:883`, `app.js:7694/7709`); Kotlin `ProjectDtos.kt:25`. (E-mail de emergência **do projeto**.)
- `EmailDeliveryLog` / `recipient_email` — `models.py:973-986`; migration `0061`. (Log de entrega de e-mail de acidente.)
- **Fluxo de e-mail de emergência** — `services/email_sender.py`, `services/email_templates.py`. Consome `User.email` (que **mantemos**). **Não** é religado ao telefone neste plano.
- SMTP/config — `core/config.py`, `deploy/.env.production.example:72,78`.
- LGPD/privacidade — `services/account_deletion.py` (scrub de `recipient_email`), `PrivacyConfig.kt`, `PrivacyScreen.kt`, textos `{privacyEmail}`.
- `accident_user_reports.user_phone_snapshot` (`models.py:864`) — hoje sempre `None`; **não** é o novo campo (não confundir).
- Tabela `admin_users` (auditoria) — não tem e-mail de cadastro.

---

## 11. Variações de escopo

- **Variação A (plano principal, recomendado):** e-mail **visível** no cadastro/admin **+** telefone adicionado. Menor risco, 100% aditivo. É o que a resposta de D1 indica.
- **Variação B (se você quiser esconder o e-mail das telas):** manter a coluna `email` no banco e o fluxo de emergência, mas **remover o e-mail do formulário de cadastro (web/Kotlin) e da coluna do admin**, exibindo só o telefone. Delta em relação ao principal: (1) remover/ocultar o `<input>` de e-mail em `index.html:383-393` e o campo Compose em `SelfRegistrationDialog.kt:119-132`; (2) parar de enviar `email` nos corpos de cadastro; (3) trocar o `<th>Email</th>` por `<th>Contato</th>` (em vez de adicionar) no admin. ⚠️ Consequência: novos usuários ficam sem e-mail ⇒ **não recebem o alerta de emergência** — só siga a Variação B se isso for aceitável. **Confirme antes de implementar.**

## 12. Trabalho futuro (fora deste plano)
- Ligar o telefone ao Modo Acidente via **SMS/ligação Twilio** (Twilio já configurado; ver memória `project_twilio`) — substituiria/complementaria o e-mail de emergência.
- Localizar os ~240 nomes de país no seletor.
- Coluna `iso_pais` se for necessário distinguir países que compartilham código de discagem.

---

## 13. Estratégia de testes (antes de cada deploy)

- **Backend (pytest):**
  - Self-registration aceita `cod_pais/contato` válidos, persiste em `User`/`PendingUserRegistration`; aceita ausência (opcional); rejeita formato inválido (422).
  - `AdminUserUpsert` (criar/editar) round-trip dos dois campos; `AdminUserListRow`/`AdminUserPendingRow` retornam os campos.
  - `approve_user_pending` copia `cod_pais/contato` do pendente para o `User`.
  - Migration `0081` (SQLite limpo) cria as 4 colunas.
  - **Regressão:** e-mail e fluxo de emergência intactos (rodar suíte de `email_sender`/acidente).
- **Check Web:** manual — trocar país muda a máscara; envio com/sem telefone; erro de telefone inválido; e-mail continua funcionando.
- **admin2:** manual nas duas cópias — coluna Contato aparece, editar/salvar persiste, número completo exibido; e-mail continua editável.
- **Kotlin:** unit (máscara/validação/mapping) + smoke de UI + teste manual em device; `am instrument` para os instrumentados (memória `kotlin_notifications`).

---

## 14. Plano de rollback

- **Backend:** a migration `0081` tem `downgrade` que dropa as 4 colunas. Como nada existente depende delas, reverter é seguro. Alternativa mais branda: reverter apenas o código (as colunas nullable ficam ociosas, sem efeito).
- **Check Web / admin2:** reverter os commits (e, no admin2, o push do sub-repo) restaura o estado anterior; e-mail nunca deixou de funcionar.
- **Kotlin:** manter a versão anterior na store até validar; roll-out gradual.
