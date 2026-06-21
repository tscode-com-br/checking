# Checking (Android) — TP9: Roteiro de teste em DISPOSITIVO REAL (mudanças de check-in / FORMS / histórico)

> **O que mudou nesta versão (plan002):** o app passou a fazer **check-in apenas quando a localização
> muda** (acabou o check-in duplicado), passou a registrar **"Localização não Cadastrada"** quando você
> sai da área estando em check-in, abrir/trazer o app ao primeiro plano **dispara a avaliação**, o
> histórico mostra **a localização**, e o FORMS é enviado **uma vez por projeto**.
>
> **O check-out NÃO mudou** — confirme que continua exatamente como antes.

## Pré-requisitos

- **Dispositivo REAL** (o emulador não dispara geofence de forma confiável). De preferência teste em um
  aparelho **restritivo** (Xiaomi/Oppo/Realme/Vivo/Huawei) **e** num "limpo" (Pixel/Motorola/Samsung).
- **APK:** `checking_kotlin/app/build/outputs/apk/debug/app-debug.apk` (instala lado a lado com o app de
  produção; ative "fontes desconhecidas").
- **Credenciais:** chave de teste **`TEST`** / senha **`000000`**. Para o item 6 (FORMS por projeto),
  use uma chave cadastrada em **2 projetos** (ex.: P80 **e** P83).
- ⚠️ **Dependência de backend (IMPORTANTE):** alguns itens só funcionam **depois** que as mudanças de
  backend forem para produção:
  - **Item 3** ("Localização não Cadastrada") precisa do **EP5** deployado.
  - **Item 6** (FORMS por projeto) precisa do **EP7** deployado.
  - **Item 7** (histórico com localização) precisa do **EP1** deployado.
  - **Itens 1, 2, 4, 5, 8** funcionam **só com o app** (mudanças no cliente), independem do deploy.

## Dados do aparelho (preencha)

Modelo: ____ · Fabricante: ____ · Android: ____ · Chave usada: ____

---

## Checklist

Marque: ✅ OK · ❌ Problema (descreva + print/vídeo) · ⏭️ Não testei.

### 1. Parado dentro de uma área → SEM check-in repetido  *(só app)*
- [ ] Atividades Automáticas **LIGADAS**, parado dentro de uma área cadastrada.
- [ ] Ao longo de **vários ciclos de 15 min** (e ao reabrir o app), **NÃO** ocorre novo check-in no mesmo
      local. (skip-if-unchanged + mudança A.)

### 2. Sair da área A e entrar na área B → UM check-in em B  *(só app — a prova do fim do duplicado)*
- [ ] Estando em check-in em A, **caminhe** para a área B (cadastrada). Ocorre **exatamente UM** check-in
      em B — mesmo que a troca dispare geofence **SAIR(A)+ENTRAR(B)** (dois gatilhos).
- [ ] Um tick de 15 min depois, ou trazer o app ao primeiro plano **em B**, **NÃO** gera novo check-in
      (mesmo local). *(Antes desta versão, aqui apareciam 2 check-ins.)*

### 3. Em check-in, sair para "perto mas fora" → "Localização não Cadastrada"  *(precisa EP5)*
- [ ] Estando em check-in, ande para um ponto **próximo, porém fora** de qualquer área cadastrada → o app
      faz **um** check-in com o local **"Localização não Cadastrada"**.
- [ ] Continuar parado nesse ponto → **não repete** (não há novo check-in "não Cadastrada").

### 4. Em check-in, ir para longe / Zona de CheckOut → CHECK-OUT  *(só app — inalterado)*
- [ ] Estando em check-in, vá para a 'Zona de CheckOut' **ou** para mais de 2 km de qualquer área → o app
      faz o **check-out**.
- [ ] Continuar longe / em check-out → **nunca** um segundo check-out.

### 5. Trazer o app ao primeiro plano numa área nova → um check-in/out correto  *(só app)*
- [ ] Abra/retorne o app ao primeiro plano com Atividades Automáticas ligadas → ele avalia e faz a ação
      correta (check-in ou check-out) **uma vez**, conforme a situação.

### 6. Usuário em P80+P83 → FORMS para os DOIS projetos  *(precisa EP7)*
- [ ] Com uma chave em 2 projetos, no **primeiro check-in do dia** → o FORMS é preenchido/enviado **uma
      vez para CADA projeto** (ex.: P80 **e** P83 → duas submissões). Verifique no admin / banco.
- [ ] Em um **check-out** → idem, uma submissão por projeto.
- [ ] Usuário de **um** projeto → exatamente **uma** submissão (como antes).

### 7. Tocar em "ÚLTIMO CHECK-IN" / "ÚLTIMO CHECK-OUT" → tabela com LOCALIZAÇÃO  *(precisa EP1)*
- [ ] Tocar em cada um dos dois cartões abre um diálogo com a tabela **Data / Hora / Local**; entradas sem
      local aparecem como "-".

### 8. Modo manual (Atividades Automáticas DESLIGADAS) → nada automático  *(só app — Situação 9)*
- [ ] Com as Atividades Automáticas **DESLIGADAS**, o app **não** faz check-in/out automático; o seletor
      **"Local"** aparece e o registro manual funciona normalmente.

---

## Como relatar
Para cada item: OK / Problema / Não testei. Em "Problema", inclua o esperado, o ocorrido, print/vídeo e os
dados do aparelho. **Prioritários:** itens **2** (fim do duplicado), **4** (check-out intacto) e **5**
(primeiro plano). Os itens 3/6/7 só após o deploy do backend.
