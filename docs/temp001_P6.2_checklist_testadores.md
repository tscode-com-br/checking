# Checking (Android) — Roteiro de teste para os testadores (P6.2)

> **O que mudou nesta versão:** uma reorganização **visual/UX** dos Ajustes e do fluxo de permissões.
> **Nada do comportamento de fundo deveria ter mudado** (check-in/check-out, geofencing, verificação de
> 15 em 15 min, pausa programada, modo acidente). Seu papel é confirmar que **tudo continua funcionando
> igual** e que as novidades de tela estão corretas.
>
> ⚠️ **Se QUALQUER item abaixo se comportar diferente do que você já conhecia, ANOTE e avise** — mesmo que
> pareça pequeno.

## Antes de começar — anote os dados do aparelho

Preencha no topo do seu relato (são importantes p/ interpretar os resultados):

- **Modelo do aparelho:** __________________________
- **Fabricante (Xiaomi / Samsung / Motorola / etc.):** __________________________
- **Versão do Android:** __________________________
- **Idioma do aparelho:** __________________________
- **Chave usada no teste:** __________________________

> Por que importa: a linha **"Iniciar com o aparelho"** e a confiabilidade do **geofencing em segundo
> plano** dependem do fabricante. Precisamos de testes em aparelhos **Xiaomi/Oppo/Realme/Vivo/Huawei**
> (restritivos) **e** em um "limpo" (Motorola/Pixel/Samsung) para cobrir os dois casos.

---

## Itens a testar

Marque cada item: ✅ OK (igual ao de antes) · ❌ Problema (descreva) · ⏭️ Não consegui testar.

### 1. Login (autenticação)
- [ ] Digite uma **chave conhecida**: os campos ficam com **brilho LARANJA** ("encontrado").
- [ ] Informe a **senha correta** e entre: o brilho passa para **VERDE** e aparece "Autenticação concluída".
- [ ] Tente uma **senha errada**: o erro é tratado normalmente (sem travar).
- [ ] Saia/desconecte: a tela **volta ao estado inicial** corretamente.

### 2. Check-in / Check-out MANUAL  *(caminho crítico — NÃO pode ter mudado)*
- [ ] Com **"Atividades Automáticas" DESLIGADAS**, aparece o seletor **"Local"** (dropdown).
- [ ] Faça um **Check-In** manual escolhendo um local → confirma e o **histórico atualiza**.
- [ ] Faça um **Check-Out** manual → confirma e o **histórico atualiza**.
> Este é o item mais importante: o check-in/out manual precisa funcionar **exatamente** como antes.

### 3. Atividades Automáticas LIGADAS  *(área mais sensível)*
- [ ] Abra **Ajustes (engrenagem) › Atividades Automáticas** e marque **"Habilitar Atividades Automáticas"**.
- [ ] Surge a **checklist de permissões** (Notificações / Localização 'o tempo todo' / Bateria / e, só em
      aparelhos restritivos, **"Iniciar com o aparelho"**). Tocar em cada linha **abre a tela do sistema**
      para conceder aquela permissão.
- [ ] Concedendo o **mínimo** (Notificações + Localização precisa), aparece a **notificação fixa do serviço**
      na barra de status e o **card "Local" (GPS)** na tela principal.
- [ ] Revogue uma permissão **recomendada** (ex.: tire "Permitir o tempo todo" ou reative a otimização de
      bateria): o estado vira **degradado (LARANJA)**, mas **o serviço continua rodando** (não desliga).
- [ ] **Geofencing (precisa de aparelho real + deslocamento):** ao **entrar/sair** de um local cadastrado,
      o app faz o check-in/out automático. *(Pode não disparar em emulador — teste andando de verdade.)*

### 4. Brilho da engrenagem (gear)
- [ ] **Desligado** (sem atividades automáticas): **sem brilho**.
- [ ] **Ligado + tudo concedido**: brilho **VERDE**.
- [ ] **Ligado + falta permissão recomendada**: brilho **LARANJA**.
- [ ] Em todos os casos, **tocar na engrenagem abre os Ajustes** normalmente (o brilho nunca bloqueia o toque).

### 5. Tela de Ajustes
- [ ] Está **agrupada e legível**: seções **ATIVIDADES AUTOMÁTICAS / PREFERÊNCIAS / AJUDA**.
- [ ] **Cada linha abre o destino certo** (Atividades Automáticas, Pausa Programada, Avisos, Alterar Senha,
      Suporte, Sobre).
- [ ] O rótulo é **"Avisos"** (não mais "Notificações") e **"Alterar Senha"** (não mais "Resetar Senha").
- [ ] **NÃO existe mais a entrada "Permissões"** no menu (ela foi fundida dentro de "Atividades Automáticas").
- [ ] A **troca de idioma** funciona (selecione outro idioma e veja a tela mudar).

### 6. Aviso de primeiro login ("nudge")  *(precisa de uma chave com auto-atividades DESLIGADAS)*
- [ ] Faça login com uma chave que **NUNCA** habilitou atividades automáticas: aparece **um card** sugerindo
      ativá-las (com "Ativar agora" e "Agora não").
- [ ] Toque **"Agora não"**: o card some **e não volta** mesmo após **fechar e reabrir** o app.
- [ ] (Em outra chave/igual reinstalada) toque **"Ativar agora"**: abre o diálogo de **Atividades Automáticas**
      e o card some.

### 7. Subsistemas que NÃO foram mexidos — confirmar que seguem funcionando
- [ ] **Modo Acidente:** banner, reportar situação, captura de **vídeo**.
- [ ] **Transporte:** a tela de Transporte abre e funciona.
- [ ] **Pausa Programada:** liga/desliga e respeita os horários.
- [ ] **Fila offline:** fique **sem internet**, faça um check-in/out, **volte a conexão** → ele é enviado.
- [ ] **Preferências de "Avisos"** (notificações push): os 3 interruptores funcionam.

### 8. ⭐ Idioma das NOTIFICAÇÕES  *(correção desta versão — confirmar com atenção)*
- [ ] Coloque o app em um idioma (ex.: Português) e gere notificações (serviço fixo, check-in/out
      automático, pausa, etc.): **todas devem aparecer no MESMO idioma do app** — **não** em inglês.
- [ ] Se possível, repita com o app em **inglês** e confirme que as notificações saem em inglês.
> Observação conhecida: em **chinês / malaio / indonésio / tagalo**, alguns textos de Atividades
> Automáticas/Permissões ainda caem para **português** (lacuna de tradução já mapeada — **não** é bug novo;
> só anote se notar).

---

## Como relatar

Para cada item, responda **OK / Problema / Não testei**. Em "Problema", inclua:
- o que você esperava, o que aconteceu, e **um print ou vídeo** se der;
- os **dados do aparelho** do topo.

Itens prioritários (não deixe de testar): **2 (check-in/out manual)**, **3 (atividades automáticas +
geofencing)** e **8 (idioma das notificações)**.
