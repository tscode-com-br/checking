# Setup de Desenvolvimento e Teste (Windows)

## 1) Pré-requisitos

- Node.js LTS (inclui npm)
- VS Code
- Arduino IDE 2.x (ou PlatformIO)

## 2) Instalação do Node.js

Com winget:

```powershell
winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements --silent
```

Se o terminal não reconhecer `node`/`npm` imediatamente, feche e abra um novo terminal.

## 3) Instalar dependências do backend

```powershell
cd apps/raspberry-server
copy .env.example .env
npm install
npm run start
```

Servidor esperado em:

- `http://localhost:3000`

## 4) Teste rápido da API

Em outro terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:3000/api/status | ConvertTo-Json -Depth 4
```

Resposta esperada inicial:

- `totalPresentes = 0`
- `presentes = []`
- `registros = []`

## 5) Extensões e libs do firmware (Arduino)

No Arduino IDE, instalar:

- Board package: **esp32 by Espressif Systems**
- Library: **Adafruit PN532**
- Library: **Keypad** (Mark Stanley / Alexander Brevig)
- Selecionar placa: **ESP32S3 Dev Module** (compatível com ESP32-S3 N16R8)

Arquivo do firmware:

- `firmware/esp32-rfid/esp32s3_n16r8_checkcheck.ino`

Cadastro de matrícula no primeiro uso:

- No firmware atual, quando o cartão não está cadastrado, a ESP32 pede a matrícula no **teclado numérico 4x3**.
- Digitar matrícula numérica de 7 a 10 dígitos (ex.: `1234567`) e confirmar com `#` ou `*`.

## 6) Variáveis de ambiente importantes

Arquivo:

- `apps/raspberry-server/.env`

Campos:

- `PORT=3000`
- `DEVICE_API_KEY=<chave para ESP32>`
- `ADMIN_API_KEY=<chave para cadastro de usuários>`
