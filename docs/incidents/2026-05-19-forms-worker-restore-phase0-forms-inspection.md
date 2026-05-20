# Phase 0 / Prompt 0.2 — Inspeção do Microsoft Forms

> **Status:** observação somente; nenhum envio foi feito ao form, nenhum código alterado.
>
> **Quando:** 2026-05-19 (mesma janela do Prompt 0.1).
>
> **Como:** Playwright 1.55 + Chromium 1187 local, modo headless, contexto incógnito limpo, viewport 1366×900, sem cookies/sessão Microsoft. Script em `c:/tmp/forms_inspect.py` (não comitado).
>
> **URL inspecionada:** `settings.forms_url` ([sistema/app/core/config.py:29](../sistema/app/core/config.py#L29))
> `https://forms.office.com/Pages/ResponsePage.aspx?id=QWJvW1ea5EuOUB36cueaV-4C0XpFTa1LmJM_FjZpp4pUOTFGR1QwSk00Vk5KQ0ExNUMzQldRSkpHWCQlQCN0PWcu&origin=QRCode`

## 1. Resposta às duas perguntas críticas do Prompt 0.2

| Pergunta | Resposta | Evidência |
|---|---|---|
| O form aceita envio anônimo ou exige login Microsoft? | **Anônimo.** Sem login wall. | `is_login_wall: false`, `initial_response_status: 200`, URL final idêntica à inicial, página renderiza inputs e botão de envio. |
| O form ainda tem os 5 campos esperados pelo worker (chave, confirmação, normal/retroativo, check-in/check-out, projeto)? | **Não.** Tem 4 campos. A pergunta de projeto P80/P82/P83 **não existe mais**. | `attribute_inventory.data-automation-id.questionItem = 4`. Body innerText lista apenas Q1–Q4. Veja §4. |

**Implicações imediatas para o plano:**

1. ✅ **Prompt 6.3 pode ser pulado.** Não há necessidade de wiring de SSO / `storage_state.json` / `playwright codegen` — o form aceita anônimo.
2. 🚨 **Bloqueio para a Fase 1.** Se o worker for restabelecido **como está hoje** (`_submit_once` em [sistema/app/services/forms_worker.py](../sistema/app/services/forms_worker.py)), **toda submissão de check-in falhará** ao clicar em `botao_projeto_*` — esses 3 XPaths retornam `count=0`. O backlog de 1287 itens viraria 1287 falhas. **Não restabelecer o worker antes de tratar isso.** Ver §6 para as opções.

## 2. Metadata da página

| Atributo | Valor |
|---|---|
| Título | `Petrobras Check-In/Check-Out - TBY` |
| Subtítulo | `Tuas Boulevard Yard` |
| Status HTTP | 200 |
| URL final | igual à inicial (sem redirect para login.microsoftonline.com) |
| Idioma da UI | pt-BR (campos: "Chave Petrobras", "Tipo de Informe", "Enviar", etc.) |

## 3. Inventário de atributos estáveis (`data-automation-id` por contagem)

Coleta via `document.querySelectorAll('[data-automation-id]')`:

| `data-automation-id` | quantidade |
|---|---|
| `formTitle` | 1 |
| `formSubTitle` | 1 |
| `noticeContainer` | 1 |
| `questionItem` | **4** |
| `questionTitle` | 4 |
| `questionOrdinal` | 4 |
| `requiredStar` | 4 |
| `textInput` | 2 |
| `choiceItem` | 4 |
| `radio` | 4 |
| `submitButton` | 1 |

Observações sobre nomes que o plano (Prompt 6.1) supôs existirem:

- `radioOption` → **não existe nesta versão**. A opção de rádio aparece como `data-automation-id="radio"` (singular) embrulhada num `data-automation-id="choiceItem"`. O **`data-automation-value`** (atributo separado) traz o texto da opção: `Normal`, `Retroativo`, `Check-In`, `Check-Out`.
- `checkboxOption` → não existe (form não tem checkbox).
- `thankYouPage` → não existe na página inicial (provavelmente aparece só após envio).

`input type` distribution: 2× `text`, 4× `radio`.

## 4. Estrutura real do formulário (4 perguntas)

Extraído de `body.innerText` (`role="heading"` para cada title) e do `outerHTML` dos `questionItem`:

| # | Pergunta | Tipo | Opções / Validação |
|---|---|---|---|
| 1 | **Chave Petrobras** | Texto linha única | `maxlength="4000"` (mas placeholder diz "Insira no máximo 4 caracteres" — limite ainda é semântico, não duro) |
| 2 | **Confirme Chave Petrobras** | Texto linha única | idem |
| 3 | **Tipo de Informe** | Rádio | `Normal` / `Retroativo` |
| 4 | **Tipo de Registro** | Rádio | `Check-In` / `Check-Out` |

**Pergunta 5 (Projeto P80/P82/P83) não existe.** Os XPaths `botao_projeto_P80.txt`, `botao_projeto_P82.txt`, `botao_projeto_P83.txt` retornam `count=0`.

Screenshot do form vazio: [`docs/temp002_phase0_screenshots/01_initial_render.png`](temp002_phase0_screenshots/01_initial_render.png) — confirma visualmente as 4 perguntas.

Como o form foi alterado para anônimo (`origin=QRCode`), é razoável supor que o dono do form decidiu remover a pergunta de projeto por algum motivo operacional (talvez porque a `chave` já implique o projeto, ou porque o dashboard gerencial não usa mais essa dimensão). **Decisão de produto necessária antes do Prompt 1.x.**

## 5. Auditoria dos 11 XPaths atuais (read-only, antes de qualquer ação no form)

Cada XPath em [assets/xpath/](../assets/xpath/) foi avaliado com `page.locator(f"xpath={…}").count()` contra o DOM real:

| Arquivo | XPath (atual, posicional) | count | Veredito |
|---|---|---|---|
| `digitar_chave.txt` | `//*[@id="question-list"]/div[1]/div[2]/div/span/input` | **1** | OK |
| `confirmar_chave.txt` | `//*[@id="question-list"]/div[2]/div[2]/div/span/input` | **1** | OK |
| `botao_normal.txt` | `//*[@id="question-list"]/div[3]/div[2]/div/div/div[1]/div/label/span[1]/input` | **1** | OK |
| `botao_retroativo.txt` | `//*[@id="question-list"]/div[3]/div[2]/div/div/div[2]/div/label/span[1]/input` | **1** | OK |
| `botao_checkin.txt` | `//*[@id="question-list"]/div[4]/div[2]/div/div/div[1]/div/label/span[1]/input` | **1** | OK |
| `botao_checkout.txt` | `//*[@id="question-list"]/div[4]/div[2]/div/div/div[2]/div/label/span[1]/input` | **1** | OK |
| `botao_enviar.txt` | `//*[@id="form-main-content1"]/div/div/div[2]/div[3]/div/button` | **1** | OK |
| `botao_projeto_P80.txt` | `//*[@id="question-list"]/div[5]/div[2]/div/div/div[1]/div/label/span[1]/input` | **0** | **QUEBRADO** — pergunta não existe |
| `botao_projeto_P82.txt` | `//*[@id="question-list"]/div[5]/div[2]/div/div/div[2]/div/label/span[1]/input` | **0** | **QUEBRADO** |
| `botao_projeto_P83.txt` | `//*[@id="question-list"]/div[5]/div[2]/div/div/div[3]/div/label/span[1]/input` | **0** | **QUEBRADO** |
| `sucesso.txt` | `//*[@id="form-main-content1"]/div/div/div[2]/div[1]/div[2]/div[2]/span` | **0** | Esperado — só aparece após envio. Não testado nesta inspeção (que é read-only). Plano original (Prompt 6.1) já sinaliza que `sucesso` deve usar texto, não posição. |

## 6. Opções para resolver o gap dos 3 XPaths de projeto (necessário antes do Deploy A)

Sem ação nessa frente, **toda submissão pós-restart vai falhar**.

**Opção (A) — Tornar a pergunta de projeto opcional no worker.**

- Em `_submit_once`, embrulhar o clique de projeto em `try/except`.
- Se o XPath não casar (count=0), pular a etapa em vez de levantar `FormsStepTimeoutError`.
- Vantagem: zero mudança no form, processa backlog imediato.
- Risco: o dashboard gerencial perde a dimensão "projeto" (provavelmente já adaptado, dado que rodou anônimo nesse formato por dias).
- **Recomendada se** o dono do form confirmar que a pergunta foi removida intencionalmente.

**Opção (B) — Pedir ao dono do form que re-adicione a pergunta "Projeto".**

- O Forms aceita edição via portal Microsoft.
- Adicionar Q5 com opções P80/P82/P83 e remover/atualizar a pergunta seria suficiente.
- Vantagem: nenhuma mudança no worker; o XPath posicional `/div[5]/…` voltaria a casar.
- Risco: depende de stakeholder externo + janela de mudança no dashboard receptor.

**Opção (C) — Refatorar os XPaths para semânticos antes de Deploy A (parte da Fase 6 antecipada).**

- Trocar `digitar_chave.txt` por `(//input[@data-automation-id="textInput"])[1]`, etc.
- Para projetos: aceitar inexistência. Se algum dia voltar, o seletor `//label[normalize-space(.)="P80"]//input` casaria automaticamente.
- Vantagem: deixa a integração robusta a redesigns futuros.
- Risco: mais escopo no Deploy A — mais coisas para validar antes do go-live.

**Recomendação:** primeiro conversar com o dono do form (10 min) para entender qual é a verdade de produto, e **só então** escolher entre (A) + (C) (caminho mais barato) ou (B). Esta decisão deve preceder o Prompt 1.1.

## 7. Seletores propostos (alimenta o Prompt 6.1 e 6.2)

Baseado nos atributos estáveis observados. Cada arquivo em `assets/xpath/` deverá suportar múltiplos candidatos (Prompt 6.2). Ordem sugerida — do mais estável ao "último recurso":

| Arquivo | Proposta (estável) | Fallback semântico | Fallback posicional (legado) |
|---|---|---|---|
| `digitar_chave.txt` | `(//input[@data-automation-id="textInput"])[1]` | `//div[@data-automation-id="questionItem"][1]//input[@data-automation-id="textInput"]` | `//*[@id="question-list"]/div[1]/div[2]/div/span/input` |
| `confirmar_chave.txt` | `(//input[@data-automation-id="textInput"])[2]` | `//div[@data-automation-id="questionItem"][2]//input[@data-automation-id="textInput"]` | `//*[@id="question-list"]/div[2]/div[2]/div/span/input` |
| `botao_normal.txt` | `//span[@data-automation-value="Normal"]//input[@type="radio"]` | `//label[normalize-space(.)="Normal"]//input` | `//*[@id="question-list"]/div[3]/.../div[1]/.../input` |
| `botao_retroativo.txt` | `//span[@data-automation-value="Retroativo"]//input[@type="radio"]` | `//label[normalize-space(.)="Retroativo"]//input` | `//*[@id="question-list"]/div[3]/.../div[2]/.../input` |
| `botao_checkin.txt` | `//span[@data-automation-value="Check-In"]//input[@type="radio"]` | `//label[normalize-space(.)="Check-In"]//input` | `//*[@id="question-list"]/div[4]/.../div[1]/.../input` |
| `botao_checkout.txt` | `//span[@data-automation-value="Check-Out"]//input[@type="radio"]` | `//label[normalize-space(.)="Check-Out"]//input` | `//*[@id="question-list"]/div[4]/.../div[2]/.../input` |
| `botao_enviar.txt` | `//button[@data-automation-id="submitButton"]` | `//button[normalize-space(.)="Enviar"]` | `//*[@id="form-main-content1"]/div/div/div[2]/div[3]/div/button` |
| `botao_projeto_*` | n/a hoje. Manter arquivo? | Se a pergunta voltar: `//span[@data-automation-value="P80"]//input` etc. | (legado) |
| `sucesso.txt` | `//*[@role="heading" and (contains(., "Sua resposta foi enviada") or contains(., "obrigad"))]` | `//*[@data-automation-id="thankYouPage"]` | (legado) |

Validados nos 7 que devem casar **antes** do envio (counts no §5 = 1). Os 4 restantes (projeto + sucesso) só validáveis no Prompt 8.3 / smoke real com `RUN_LIVE_FORMS_SMOKE=1`.

## 8. Texto provável da página de sucesso (alimentação para `sucesso.txt`)

A página inicial inclui na sua tira de rodapé/notice o termo "enviar" várias vezes. A página de sucesso do MS Forms em pt-BR exibe usualmente: **"Sua resposta foi enviada."** + um botão "Enviar outra resposta".

Em inglês: **"Your response was submitted."**

Como o form está configurado em pt-BR e o `localStorage` da MS faz fallback por `Accept-Language`, o seletor seguro é:

```
//*[@role="heading" and (
    contains(., "Sua resposta foi enviada") or
    contains(., "Your response was submitted") or
    contains(., "obrigad")
)]
```

Esse seletor não pode ser confirmado sem efetivamente submeter — a confirmação fica para o Prompt 8.3 (smoke gated por `RUN_LIVE_FORMS_SMOKE=1`).

## 9. Screenshots

Captura nesta inspeção (1 arquivo — não fizemos screenshots de form preenchido nem de tela de sucesso para evitar qualquer side-effect):

- `docs/temp002_phase0_screenshots/01_initial_render.png` — form em branco logo após `networkidle`, viewport 1366×900.

Os 3 screenshots restantes que o plano sugeriu (preenchido, momento do clique, sucesso) seriam capturas durante um envio real → ficam para o Prompt 8.3.

## 10. Comandos para reprodução

```powershell
# (assume venv ativo com `playwright==1.55.0` + `playwright install chromium`)
python c:/tmp/forms_inspect.py > c:/tmp/forms_inspect_output.json
```

Saída completa preservada em `c:/tmp/forms_inspect_output.json` (não comitado).
