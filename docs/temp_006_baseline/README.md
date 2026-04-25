# Baseline Visual da Fase 0 de temp_006

Data: 2026-04-25

Este diretório reúne os artefatos visuais registrados na execução da Fase 0 de `docs/temp_006.md`.

Objetivo desta baseline:

- congelar o estado atual do webapp antes das mudanças de paisagem, desktop e microcopy do botão de transporte;
- evidenciar o comportamento atual em retrato, paisagem e desktop;
- apoiar comparação visual e revisão posterior das fases de implementação.

Origem capturada:

- URL pública atual: `https://tscode.com.br/checking/user`
- motivo: registrar o estado atualmente servido sem alterar os arquivos da SPA durante a fase de baseline

Arquivos:

- `01-portrait-current.png`: estado atual em retrato
- `02-landscape-current.png`: estado atual em paisagem, ainda bloqueado pelo overlay
- `03-desktop-current.png`: estado atual em desktop, também bloqueado pelo overlay de orientação

Comando usado:

```powershell
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
& $chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=412,915 --virtual-time-budget=5000 --screenshot="C:\dev\projetos\checkcheck\docs\temp_006_baseline\01-portrait-current.png" 'https://tscode.com.br/checking/user'
& $chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=915,412 --virtual-time-budget=5000 --screenshot="C:\dev\projetos\checkcheck\docs\temp_006_baseline\02-landscape-current.png" 'https://tscode.com.br/checking/user'
& $chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=1366,768 --virtual-time-budget=5000 --screenshot="C:\dev\projetos\checkcheck\docs\temp_006_baseline\03-desktop-current.png" 'https://tscode.com.br/checking/user'
```

Observações:

- a baseline existente em `checking_kotlin_new/docs/baseline-visual/screenshots/2026-04-25-spa-pixel7/` continua válida como pacote amplo de referência da SPA;
- esta pasta foi criada apenas para o recorte específico da demanda de paisagem/desktop de `temp_006`.
