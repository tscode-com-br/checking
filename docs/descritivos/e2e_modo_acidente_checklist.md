# Checklist E2E — Modo Acidente

**Versão:** 1.0  
**Destinado a:** QA / Engenharia  
**Executar antes de:** qualquer deploy em produção do Modo Acidente  
**Ambiente alvo:** staging (Docker Compose completo com SMTP e DO Spaces reais ou mocks)

---

## Pré-requisitos globais

Antes de iniciar os cenários, confirme que:

- [ ] O servidor está em execução (`docker compose up` ou `uvicorn` local).
- [ ] Banco de dados limpo de acidentes anteriores (`accidents` sem `closed_at IS NULL`).
- [ ] Variáveis SMTP configuradas e servidor de e-mail acessível (ou MailHog rodando em `localhost:1025`).
- [ ] Storage configurado (DO Spaces ou bucket S3 equivalente com `OBJECT_STORAGE_*` vars).
- [ ] Pelo menos **3 usuários** cadastrados com `checkin=True` no projeto de teste.
- [ ] Pelo menos **1 usuário** cadastrado com `checkin=False` para o Cenário 9.
- [ ] Admin perfil 1 (`admin_p1`) e admin perfil 9 (`admin_p9`) com sessões disponíveis.
- [ ] Dispositivo móvel (ou emulador) com o app Checking Mobile apontando para o servidor.

---

## Convenção de registro

Para cada etapa de verificação:

| Símbolo | Significado |
|---------|-------------|
| `- [ ] PASS` | Marcar quando o comportamento esperado foi observado |
| `- [ ] FAIL` | Marcar quando o comportamento divergiu do esperado |

Anote detalhes em **Notas** ao final de cada cenário.

---

## Cenário 1 — Admin abre acidente; Checking Web reage em menos de 2 segundos

**Objetivo:** Validar que o broadcast SSE chega ao browser do usuário imediatamente após a abertura.

**Atores:** `admin_p1` (Admin painel) + `usuario_web` (Checking Web, browser diferente ou aba anônima).

### Passos

1. Abrir o Checking Web como `usuario_web`. Verificar que a página está no estado **normal** (sem banner de emergência).
2. Em outra aba/browser, logar como `admin_p1` no painel Admin.
3. No painel Admin, clicar no botão **Acionar Modo Acidente** (deve abrir o wizard).
4. No wizard: selecionar projeto → selecionar local (ou digitar nome personalizado) → clicar **Confirmar**.
5. Observar o Checking Web de `usuario_web` **sem recarregar a página**.

### Verificações

- [ ] PASS — O banner/tela de emergência aparece no Checking Web em **menos de 2 segundos** após o clique em Confirmar.
- [ ] PASS — O botão no painel Admin muda de rótulo para **"Encerrar Acidente"** (ou equivalente).
- [ ] PASS — A seção "Situação Pessoal" aparece no Admin com pelo menos 1 linha (a do usuário pré-registrado).
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Tempo observado de propagação SSE: ___s
Navegador/dispositivo do usuario_web: ___
```

---

## Cenário 2 — Usuário reporta zona Segurança; admin vê linha verde

**Objetivo:** Validar que `zone=safety, status=ok` se reflete em `row_color=light-green` na tabela do Admin.

**Atores:** `usuario_web` (Checking Web) + `admin_p1` (painel Admin, já com acidente aberto do Cenário 1).

### Passos

1. (Acidente já aberto.) Como `usuario_web`, na tela do Checking Web, selecionar **"Estou em Segurança"** e confirmar.
2. Observar a tabela "Situação Pessoal" no painel Admin.

### Verificações

- [ ] PASS — A linha de `usuario_web` muda de cor turquesa para **verde claro** (`light-green`).
- [ ] PASS — O campo "Zona" exibe **"Segurança"** e o campo "Status" exibe **"OK"**.
- [ ] PASS — A mudança de cor ocorre em menos de 3 segundos (SSE).
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Tempo de atualização da tabela no Admin: ___s
```

---

## Cenário 3 — Usuário reporta AJUDA; admin vê vermelho piscante; e-mail chega

**Objetivo:** Validar o fluxo crítico: `zone=accident, status=help` → `row_color=blinking-red` + envio de e-mail de alerta.

**Atores:** `usuario_help` (Checking Web, segundo usuário com e-mail cadastrado) + `admin_p1`.

### Passos

1. (Acidente aberto.) Como `usuario_help`, na tela do Checking Web, selecionar **"Estou no Local do Acidente"** + **"Preciso de Ajuda"** e confirmar.
2. Observar a tabela no Admin.
3. Verificar a caixa de e-mail do endereço cadastrado em `usuario_help` (ou MailHog em `http://localhost:8025`).

### Verificações

- [ ] PASS — A linha de `usuario_help` exibe **vermelho piscante** (`blinking-red`).
- [ ] PASS — O campo "Zona" exibe **"Acidente"** e o campo "Status" exibe **"AJUDA"**.
- [ ] PASS — Um e-mail de alerta chega ao endereço de `usuario_help` com subject contendo "acidente" (ou equivalente configurado).
- [ ] PASS — O e-mail inclui o nome do usuário, projeto e número do acidente.
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Subject do e-mail recebido: ___
Tempo até recebimento do e-mail: ___s
```

---

## Cenário 4 — Usuário grava vídeo de ~5 segundos; admin vê link de download

**Objetivo:** Validar o upload de vídeo via multipart, armazenamento no object storage e exibição do link no Admin.

**Atores:** `usuario_web` (Checking Web) + `admin_p1`.

### Passos

1. (Acidente aberto.) Como `usuario_web`, acessar a funcionalidade de gravação de vídeo no Checking Web.
2. Gravar um vídeo de aproximadamente 5 segundos e fazer o upload.
3. No painel Admin, expandir (ou atualizar) a linha de `usuario_web` na tabela Situação Pessoal.

### Verificações

- [ ] PASS — O upload retorna HTTP 200 sem erro no browser.
- [ ] PASS — Na linha do Admin, aparece pelo menos **1 link de vídeo** associado ao usuário.
- [ ] PASS — Clicar no link abre/baixa o vídeo sem erro 403/404 (URL pré-assinada válida).
- [ ] PASS — O tamanho exibido é coerente com o arquivo gravado (> 0 bytes).
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Tamanho do arquivo gravado: ___ KB
URL do vídeo (primeiros 60 chars): ___
```

---

## Cenário 5 — Terceiro usuário faz check-in via mobile; admin vê linha turquesa

**Objetivo:** Validar que um check-in mobile durante um acidente aberto insere uma nova linha com `row_color=turquoise` (zona=aguardando).

**Atores:** `usuario_mobile` (app mobile, check-in=False antes do acidente) + `admin_p1`.

### Passos

1. (Acidente aberto.) No dispositivo móvel, logar como `usuario_mobile` (que estava com `checkin=False` quando o acidente foi aberto).
2. Realizar o **check-in** no app mobile.
3. Observar a tabela Situação Pessoal no Admin.

### Verificações

- [ ] PASS — Uma nova linha para `usuario_mobile` aparece na tabela do Admin.
- [ ] PASS — A linha exibe cor **turquesa** (`turquoise`) — zona "Aguardando".
- [ ] PASS — A linha aparece em menos de 5 segundos após o check-in (SSE ou polling).
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Tempo até aparecer no Admin: ___s
```

---

## Cenário 6 — Admin encerra acidente; tema de emergência some em ambos os clientes

**Objetivo:** Validar que o encerramento do acidente (perfil 9 ou via botão Admin) reverte a UI de ambos os clientes.

**Atores:** `admin_p9` (perfil 9, encerra o acidente) + `usuario_web` (Checking Web ainda aberto).

### Passos

1. (Acidente aberto, usuários reportados nos cenários anteriores.) Logar como `admin_p9`.
2. Clicar em **"Encerrar Acidente"** e confirmar no modal.
3. Observar o Checking Web de `usuario_web` sem recarregar.
4. Observar o painel Admin.

### Verificações

- [ ] PASS — O banner/tela de emergência **desaparece** no Checking Web em menos de 3 segundos.
- [ ] PASS — O painel Admin volta ao estado normal (sem tabela de situação, botão muda para "Acionar").
- [ ] PASS — O acidente aparece na seção **"Histórico de Acidentes"** do Admin.
- [ ] PASS — O campo `archive_ready` (ou link de download) está disponível dentro de 30 segundos (background task de geração do ZIP).
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Tempo de propagação SSE para encerramento: ___s
archive_ready ficou disponível após: ___s
```

---

## Cenário 7 — Admin perfil 1 vê tabela de histórico, mas sem botão "Remover"

**Objetivo:** Validar controle de acesso: perfil 1 pode visualizar mas não excluir.

**Atores:** `admin_p1` (perfil 1, sem poder de deleção).

### Passos

1. (Acidente encerrado e disponível no histórico.) Logar como `admin_p1`.
2. Acessar a seção **"Histórico de Acidentes"** no painel Admin.

### Verificações

- [ ] PASS — A tabela exibe a linha do acidente encerrado com colunas: número, projeto, local, data de abertura, data de encerramento.
- [ ] PASS — **Nenhum** botão "Remover" / "Excluir" / ícone de lixeira está visível para `admin_p1`.
- [ ] PASS — O link de download do arquivo ZIP está presente (se `archive_ready=true`).
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Campos visíveis na tabela: ___
```

---

## Cenário 8 — Admin perfil 9 remove acidente; linha desaparece da tabela

**Objetivo:** Validar que a deleção de acidente (perfil 9 exclusivo) remove o registro e os arquivos associados.

**Atores:** `admin_p9` (perfil 9).

### Passos

1. (Acidente encerrado visível no histórico.) Logar como `admin_p9`.
2. Localizar a linha do acidente na tabela de histórico.
3. Clicar em **"Remover"** e confirmar a exclusão.
4. Verificar a tabela.

### Verificações

- [ ] PASS — O botão "Remover" está visível para `admin_p9` (e somente para ele).
- [ ] PASS — Após confirmação, a linha do acidente **desaparece** da tabela de histórico.
- [ ] PASS — Uma segunda tentativa de acessar `GET /api/admin/accidents` retorna lista sem o acidente removido.
- [ ] PASS — (Opcional) O arquivo ZIP no object storage foi removido (verificar no console do storage).
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
ID do acidente removido: ___
```

---

## Cenário 9 — Checking Web inicia acidente; admin vê em menos de 2 segundos; primeiro registro é o autor

**Objetivo:** Validar o fluxo `origin=web` — abertura pelo próprio usuário web.

**Atores:** `usuario_opener` (Checking Web, `checkin=False` para não aparecer como pré-populado) + `admin_p1`.

### Passos

1. Garantir que não há acidente ativo.
2. Como `usuario_opener` no Checking Web, acionar **"Reportar Acidente"** (fluxo web: informa zona e status imediatamente).
3. Informar `zone=accident`, `status=help` e confirmar.
4. Observar o painel Admin.

### Verificações

- [ ] PASS — O painel Admin exibe o acidente ativo em **menos de 2 segundos** (SSE).
- [ ] PASS — Na tabela Situação Pessoal, a **primeira linha** (prioridade máxima) corresponde a `usuario_opener` com zona "Acidente" e status "AJUDA" (vermelho piscante).
- [ ] PASS — O campo `origin` do acidente exibe **"web"** (verificável via API ou histórico).
- [ ] PASS — E-mail de alerta é disparado para `usuario_opener` (status=help acionou envio).
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Tempo de propagação SSE: ___s
Chave do usuario_opener: ___
```

---

## Cenário 10 — Reload da página durante acidente preserva o estado

**Objetivo:** Validar que o estado do acidente é reenviado ao cliente ao reconectar o SSE (ou ao recarregar a página).

**Atores:** `usuario_web` (Checking Web, conectado durante um acidente ativo).

### Passos

1. (Acidente aberto, `usuario_web` vendo a tela de emergência.) Apertar **F5** (ou Ctrl+R) para recarregar a página do Checking Web.
2. Aguardar a página carregar completamente.
3. Fazer o mesmo no painel Admin com `admin_p1`.

### Verificações

- [ ] PASS — Após reload, o Checking Web de `usuario_web` volta a exibir a **tela de emergência** imediatamente (sem precisar esperar novo evento SSE).
- [ ] PASS — O status anterior do usuário (`zone` e `status` já reportados) é preservado e exibido corretamente.
- [ ] PASS — Após reload do painel Admin, a tabela Situação Pessoal exibe **todos os usuários** com os status corretos.
- [ ] PASS — O número do acidente e o nome do local são exibidos corretamente em ambos os clientes após o reload.
- [ ] FAIL — Descrever aqui se algo não funcionou.

**Notas:**  
```
Browser utilizado: ___
Estado do usuário após reload (zona/status): ___
```

---

## Resumo de execução

Preencher ao final de todos os cenários:

| Cenário | Resultado | Executor | Data/Hora |
|---------|-----------|----------|-----------|
| 1 — Admin abre; Web reage <2s | PASS / FAIL | | |
| 2 — Safety → linha verde | PASS / FAIL | | |
| 3 — Help → vermelho + e-mail | PASS / FAIL | | |
| 4 — Upload vídeo → link Admin | PASS / FAIL | | |
| 5 — Check-in mobile → turquesa | PASS / FAIL | | |
| 6 — Encerramento → UI normaliza | PASS / FAIL | | |
| 7 — Perfil 1 sem botão Remover | PASS / FAIL | | |
| 8 — Perfil 9 remove → linha some | PASS / FAIL | | |
| 9 — Web abre; Admin vê <2s | PASS / FAIL | | |
| 10 — Reload preserva estado | PASS / FAIL | | |

**Total PASS:** ___/10  
**Total FAIL:** ___/10  

**Decisão de deploy:**
- [ ] ✅ Todos PASS — aprovado para produção.
- [ ] ⚠️ Falhas não bloqueantes documentadas — aprovado com ressalvas.
- [ ] ❌ Falha bloqueante — **não fazer deploy** até resolução.

**Observações gerais:**  
```




```

---

*Documento gerado em 2026-05-18. Atualizar a cada release que modifique o Modo Acidente.*
