# CheckCheck

Projeto para controle de presença em escritório com ESP32 + RFID + Raspberry Pi 4.

## Arquitetura recomendada

- **ESP32 + RFID(s) -> Raspberry Pi por Wi-Fi (HTTP local)**
- Motivo: implementação simples, baixa latência local, manutenção fácil e sem broker adicional.
- Endereço sugerido da API na Raspberry: `http://<ip-da-raspberry>:3000/api/scan`.

> Alternativa robusta: MQTT local. Para começar rápido e com menos pontos de falha operacionais, HTTP direto atende muito bem.

## Estrutura

- `apps/raspberry-server/`: servidor Node.js + SQLite + dashboard realtime
- `firmware/esp32-rfid/`: firmware Arduino para ESP32
- `docs/materials-singapore.md`: lista completa de materiais (BOM)
- `docs/development-setup-windows.md`: setup local de desenvolvimento
- `docs/github-publish.md`: publicação no GitHub

## Requisitos

- Raspberry Pi 4 com Node.js 20+
- ESP32
- Leitor RFID MFRC522 (1 ou 2 unidades)
- LEDs: amarelo, verde, vermelho
- Buzzer ativo/passivo

---

## 1) Servidor na Raspberry

### Instalação

```bash
cd apps/raspberry-server
cp .env.example .env
npm install
npm run start
```

Servidor disponível em:

- Dashboard: `http://<ip-da-raspberry>:3000`
- API de leitura RFID: `POST /api/scan`

### Banco de dados

O SQLite é criado em `apps/raspberry-server/data/checkcheck.db` com:

- Tabela `checkcheck` (registros de entrada/saída)
- Tabela `users` (cadastro e vínculo RFID -> usuário)

Campos exigidos em `checkcheck`:

- `nome_completo`
- `matricula` (7 dígitos)
- `chave_usuario` (4 caracteres alfanuméricos)
- `data_hora_entrada_singapura`
- `entrada` (0/1)

## 2) Cadastrar usuários

Use a API para cadastrar cada funcionário e o UID do cartão RFID:

```bash
curl -X POST http://<ip-da-raspberry>:3000/api/users \
  -H "Content-Type: application/json" \
  -H "x-admin-key: troque-esta-chave-admin" \
  -d '{
    "nomeCompleto":"Ana Paula Lima",
    "matricula":"1234567",
    "chaveUsuario":"A1B2",
    "rfidUid":"DE AD BE EF"
  }'
```

## 3) Fluxo do equipamento (ESP32)

Implementado no firmware:

1. LED amarelo aceso = pronto para leitura.
2. Ao encostar o cartão, LED amarelo apaga.
3. ESP32 lê UID RFID.
4. Envia para Raspberry (`/api/scan`) com `x-device-key`.
5. Se sucesso: LED verde 1s + buzzer com 2 beeps.
6. Se falha: LED vermelho 1s + beep grave único.
7. Volta para estado pronto (LED amarelo aceso).

## 4) Entrada e saída com 2 leitores

No firmware há suporte para dois leitores:

- Leitor 1 -> `ENTRY`
- Leitor 2 -> `EXIT`

Se usar apenas 1 leitor, o backend alterna entrada/saída com base no último estado do usuário.

## 5) Visualização em tempo real

O dashboard mostra:

- Total de pessoas no escritório (presença atual)
- Lista de presentes no momento
- Tabela com registros completos (`checkcheck`) em tempo real

---

## Próximos passos recomendados

- Fixar IP da Raspberry no roteador local
- Proteger rede Wi-Fi local
- Colocar serviço da Raspberry em `systemd` para iniciar automaticamente
- (Opcional) usar Nginx reverse proxy para expor em porta 80

## Documentação complementar

- BOM completo para Singapura: `docs/materials-singapore.md`
- Setup de desenvolvimento/testes: `docs/development-setup-windows.md`
- Publicação no GitHub: `docs/github-publish.md`
