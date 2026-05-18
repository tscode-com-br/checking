# Compatibilidade de Navegadores — Modo Acidente

## Objetivo

Registrar os resultados dos testes de compatibilidade do Modo Acidente em diferentes plataformas e navegadores antes do deploy em produção.

> **Instrução:** Para cada cenário, preencha a coluna **Resultado** com ✅ Pass, ❌ Fail ou ⚠️ Parcial, e adicione observações se necessário.

---

## Tabela de Compatibilidade

### Desktop

| Browser | OS | Acidente Abre | SSE (<2s) | Reportar Safety/Help | Gravar Vídeo | Upload Vídeo | Encerrar Acidente | Resultado | Notas |
|---|---|---|---|---|---|---|---|---|---|
| Chrome 124+ | Windows 11 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | | |
| Chrome 124+ | macOS 14 (Sonoma) | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | | |
| Chrome 124+ | Ubuntu 22.04 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | | |
| Firefox 125+ | Windows 11 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | | |
| Firefox 125+ | macOS 14 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | | |
| Firefox 125+ | Ubuntu 22.04 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | | |
| Safari 17+ | macOS 14 (Sonoma) | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | | Safari grava `video/mp4` (não webm) — verificar accept no input |
| Edge 124+ | Windows 11 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | | |

### Mobile

| Browser | OS/Device | Acidente Notificado | Reportar Safety/Help | Câmera Traseira | Gravar Vídeo | Upload Vídeo | Resultado | Notas |
|---|---|---|---|---|---|---|---|---|
| Chrome Mobile | Android 13+ | [ ] | [ ] | [ ] | [ ] | [ ] | | |
| Chrome Mobile | Android 12 | [ ] | [ ] | [ ] | [ ] | [ ] | | |
| Safari | iOS 17+ (iPhone 15) | [ ] | [ ] | [ ] | [ ] | [ ] | | iOS MediaRecorder: verificar suporte a `video/mp4` |
| Safari | iOS 16 (iPhone 13) | [ ] | [ ] | [ ] | [ ] | [ ] | | Pode não suportar MediaRecorder em iOS 16 — testar fallback |
| Firefox Mobile | Android 13+ | [ ] | [ ] | [ ] | [ ] | [ ] | | |

---

## Testes de Conectividade Degradada

| Condição | SSE mantém conexão | Polling cobre atualizações | Upload funciona | Resultado | Notas |
|---|---|---|---|---|---|
| Slow 3G (Network throttle) | [ ] | [ ] | [ ] | | SSE reconecta; polling a cada 5s cobre gaps |
| Offline → Online | [ ] | [ ] | N/A | | Verificar reconexão automática do SSE |
| Latência alta (>500ms) | [ ] | [ ] | [ ] | | |

---

## Observações sobre MediaRecorder por Browser

| Browser | MIME type preferido | Fallback | Observação |
|---|---|---|---|
| Chrome (desktop/Android) | `video/webm;codecs=vp9` | `video/webm` | Suporte completo |
| Firefox | `video/webm;codecs=vp8` | `video/webm` | Suporte completo |
| Safari (macOS/iOS) | `video/mp4` | — | Não suporta `video/webm`; verificar que o frontend detecta e usa `video/mp4` |
| Edge (Chromium) | `video/webm;codecs=vp9` | `video/webm` | Igual Chrome |

> O frontend em `sistema/app/static/check/app.js` deve usar `MediaRecorder.isTypeSupported()` para selecionar o MIME type correto antes de iniciar a gravação.

---

## Checklist de Execução

Antes de marcar esta tabela como completa:

- [ ] Testar em pelo menos um dispositivo físico iOS (não apenas simulador)
- [ ] Testar em pelo menos um dispositivo físico Android
- [ ] Confirmar que vídeos enviados por Safari (mp4) aparecem corretamente na tabela admin
- [ ] Confirmar que o link de download no archive ZIP funciona para mp4 e webm
- [ ] Confirmar que SSE reconecta após perda de conexão em todos os browsers
- [ ] Confirmar que o polling (`/api/web/check/accident/state`) funciona quando SSE falha

---

## Status

**Preenchido por:** ___________________________  
**Data:** ___________________________  
**Versão do sistema testada:** ___________________________  

> Este documento deve ser preenchido **antes** de qualquer deploy em produção.
> Ver também: `docs/descritivos/e2e_modo_acidente_checklist.md` para o checklist funcional E2E.
