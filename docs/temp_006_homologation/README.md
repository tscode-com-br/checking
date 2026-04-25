# Homologacao Visual da Fase 6 de temp_006

Data: 2026-04-25

Este diretório reúne artefatos locais da homologação da Fase 6 de `docs/temp_006.md`, gerados a partir da própria SPA do workspace com dados mockados e viewports direcionados aos cenários pedidos.

Observações importantes:

- nenhuma captura desta pasta depende da URL pública nem de deploy;
- os cenários usam HTML, CSS e JavaScript reais de `sistema/app/static/check`;
- o cenário de teclado aberto em paisagem foi validado como proxy de viewport reduzido em headless com foco no campo de senha, porque o navegador headless não exibe o teclado virtual do sistema operacional.

## Cenários capturados

| Arquivo | Estado | Viewport | Observação |
| --- | --- | --- | --- |
| `docs/temp_006_homologation/screenshots/01-portrait-mobile-main.png` | Retrato mobile com shell principal preenchida | 412x915 | - |
| `docs/temp_006_homologation/screenshots/02-landscape-mobile-main.png` | Paisagem mobile com shell principal preenchida | 915x412 | - |
| `docs/temp_006_homologation/screenshots/03-landscape-mobile-auth-focus-proxy-keyboard.png` | Paisagem mobile com foco em autenticacao e viewport reduzido como proxy de teclado aberto | 915x300 | Proxy de teclado aberto: viewport reduzido em headless com foco no campo de senha. |
| `docs/temp_006_homologation/screenshots/04-tablet-landscape-main.png` | Viewport intermediaria em paisagem | 1024x768 | - |
| `docs/temp_006_homologation/screenshots/05-notebook-main.png` | Notebook comum com shell principal preenchida | 1366x768 | - |
| `docs/temp_006_homologation/screenshots/06-desktop-wide-main.png` | Desktop amplo com shell principal preenchida | 1600x900 | - |
| `docs/temp_006_homologation/screenshots/07-notebook-password-dialog.png` | Dialog de senha em notebook | 1366x768 | - |
| `docs/temp_006_homologation/screenshots/08-notebook-registration-dialog.png` | Dialog de cadastro em notebook | 1366x768 | - |
| `docs/temp_006_homologation/screenshots/09-notebook-transport-screen.png` | Tela de transporte em notebook | 1366x768 | - |
| `docs/temp_006_homologation/screenshots/10-notebook-transport-detail.png` | Detalhe de solicitacao de transporte em notebook | 1366x768 | - |

## Comando usado

```powershell
node scripts/capture_temp_006_homologation.mjs
```

