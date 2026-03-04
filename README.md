# CheckCheck

Projeto para controle de presença em escritório com ESP32 + RFID + servidor em computador local (sempre ligado).

## Arquitetura recomendada

- **ESP32 + RFID(s) -> servidor no PC do escritório (LAN/Wi-Fi local)**
- Motivo: elimina custo mensal de nuvem e mantém baixa latência local.
- Endereço sugerido da API: `http://<ip-do-pc>:3000/api/scan`.

> A internet pode continuar ativa para acesso externo opcional, mas o registro principal funciona na rede local.

## Estrutura

- `apps/raspberry-server/`: servidor Node.js + SQLite + dashboard realtime
- `firmware/esp32-rfid/`: firmware Arduino para ESP32
- `docs/materials-singapore.md`: lista completa de materiais (BOM)
- `docs/development-setup-windows.md`: setup local de desenvolvimento
- `docs/github-publish.md`: publicação no GitHub

## Requisitos

- PC Windows/Linux sempre ligado com Node.js 20+
- ESP32-S3 N16R8
- Leitor RFID/NFC PN532 V3 (2 unidades)
- LEDs: amarelo, verde, vermelho
- Buzzer ativo/passivo

---

## 1) Servidor no PC local

### Instalação

```bash
cd apps/raspberry-server
cp .env.example .env
npm install
npm run start
```

Servidor disponível em:

- Dashboard: `http://<ip-do-pc>:3000`
- API de consulta de cartão: `POST /api/cards/check`
- API de registro de leitura: `POST /api/scan`

### Banco de dados

O SQLite é criado em `apps/raspberry-server/data/checkcheck.db` com:

- Tabela `checkcheck` (eventos de leitura)
- Tabela `users` (vínculo RFID -> matrícula + dados opcionais)

Campos obrigatórios por leitura:

- `rfid_uid` (alfanumérico)
- `entrada` (`true`/`false`)

Quando cartão ainda não está cadastrado:

- `matricula` (numérico, de 7 a 10 dígitos)

Campos opcionais para preencher depois:

- `nome_completo`
- `matricula` (até 10 dígitos)
- `projeto` (`P80`, `P82`, `P83`)

## 2) Cadastrar/atualizar usuários (opcional)

Use a API admin para enriquecer cadastro depois (nome, matrícula e projeto):

```bash
curl -X POST http://<ip-do-pc>:3000/api/users \
  -H "Content-Type: application/json" \
  -H "x-admin-key: troque-esta-chave-admin" \
  -d '{
    "nomeCompleto":"Ana Paula Lima",
    "matricula":"1234567890",
    "projeto":"P80",
    "rfidUid":"DE AD BE EF"
  }'
```

## 3) Consulta de cartão (ESP32)

```bash
curl -X POST http://<ip-do-pc>:3000/api/cards/check \
  -H "Content-Type: application/json" \
  -H "x-device-key: troque-esta-chave-dispositivo" \
  -d '{
    "rfidUid":"A1B2C3D4"
  }'
```

## 4) Registro de leitura (ESP32)

```bash
curl -X POST http://<ip-do-pc>:3000/api/scan \
  -H "Content-Type: application/json" \
  -H "x-device-key: troque-esta-chave-dispositivo" \
  -d '{
    "rfidUid":"A1B2C3D4",
    "entrada":true,
    "readerId":"ENTRY",
    "deviceId":"ESP32-01",
    "matricula":"1234567"
  }'
```

- `matricula` só precisa ser enviada quando o cartão ainda não estiver cadastrado.

## 5) Fluxo do equipamento (ESP32)

Implementado no firmware:

1. LED amarelo aceso = pronto para leitura.
2. Ao encostar o cartão, LED amarelo apaga.
3. ESP32 lê UID RFID.
4. ESP32 consulta `/api/cards/check` para saber se o cartão já existe.
5. Se o cartão não existir, solicita matrícula numérica (7 a 10 dígitos).
6. Usuário confirma matrícula no keypad 4x3 digitando `#` ou `*`.
7. ESP32 envia leitura para `/api/scan` com:
  - `rfidUid`
  - `entrada` (`true` para leitor ENTRY, `false` para leitor EXIT)
  - `matricula` (somente quando cartão ainda não cadastrado)
8. Os caracteres `#` e `*` são somente confirmação local e não são enviados ao servidor.
9. Se sucesso: LED verde 1s + buzzer com 2 beeps.
10. Se falha: LED vermelho 1s + beep grave único.
11. Volta para estado pronto (LED amarelo aceso).

Configuração do equipamento:

- Arquivo local: `firmware/esp32-rfid/secrets.h`
- Template versionado: `firmware/esp32-rfid/secrets.example.h`
- Firmware principal: `firmware/esp32-rfid/esp32s3_n16r8_checkcheck.ino`
- Defina `SECRET_API_SCAN_URL` e `SECRET_API_CHECK_URL` com o IP/domínio do servidor.
- Entrada de matrícula no firmware atual: via teclado numérico 4x3 (confirmação com `#` ou `*`).

## 6) Entrada e saída com 2 leitores

No firmware há suporte para dois leitores:

- Leitor 1 -> `ENTRY`
- Leitor 2 -> `EXIT`

Se usar apenas 1 leitor, o backend alterna entrada/saída com base no último estado do usuário.

## 7) Visualização em tempo real

O dashboard mostra:

- Total de pessoas no escritório (presença atual)
- Lista de presentes no momento
- Tabela com registros completos (`checkcheck`) em tempo real

---

## Próximos passos recomendados

- Fixar IP do PC no roteador (DHCP reservation)
- Configurar inicialização automática do servidor no boot do PC
- Ajustar `ALLOWED_ORIGIN` no `.env` e manter backup do SQLite

## Documentação complementar

- BOM completo para Singapura: `docs/materials-singapore.md`
- Esquema de montagem elétrica: `docs/wiring-esp32-rfid.md`
- Setup de desenvolvimento/testes: `docs/development-setup-windows.md`
- Publicação no GitHub: `docs/github-publish.md`
- Migração para nuvem barata em SG (opcional): `docs/cloud-singapore-deploy.md`
