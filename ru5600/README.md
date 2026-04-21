# Leitor RFID USB semelhante ao RU5600

O Windows detectou um dispositivo USB com VID/PID `1A86:E010`. Esse leitor expõe pelo menos duas interfaces: uma de teclado HID e outra HID proprietaria `SWUSB_HID`.

No teste pratico, a interface de teclado nao entregou o UID do cartao de forma utilizavel. Para este modelo, o caminho principal agora e ler a interface HID proprietaria.

## Como testar no terminal

Se o PowerShell estiver na raiz do projeto (`C:\dev\projetos\checkcheck`), rode:

```powershell
pwsh -ExecutionPolicy Bypass -File .\ru5600\monitor_rfid_hid.ps1
```

Se o PowerShell ja estiver dentro da pasta `C:\dev\projetos\checkcheck\ru5600`, rode:

```powershell
pwsh -ExecutionPolicy Bypass -File .\monitor_rfid_hid.ps1
```

Com o monitor em execucao, aproxime o cartao. Se a interface HID proprietaria estiver entregando os bytes do cartao, o script imprime o relatorio bruto e tenta sugerir candidatos para o UID:

```text
[2026-04-21 14:35:10] report_id=0x00
	raw_hex=45 32 30 30 30 31 37 32 32 31 31 30 31 34 34 31 38 39 30 41 42 43 44 0D
	candidato=ASCII=E200017221101441890ABCD
```

## Se nao aparecer nada

Liste primeiro os dispositivos HID detectados para esse VID/PID:

```powershell
pwsh -ExecutionPolicy Bypass -File .\monitor_rfid_hid.ps1 --list-only
```

Se aparecer mais de um dispositivo, selecione outro indice manualmente:

```powershell
pwsh -ExecutionPolicy Bypass -File .\monitor_rfid_hid.ps1 --index 1
```

Se estiver na raiz do projeto, mantenha o prefixo ` .\ru5600\ ` no caminho do script.

## Fallback teclado HID

O script [ru5600/monitor_rfid_wedge.ps1](ru5600/monitor_rfid_wedge.ps1) continua disponivel para leitores que realmente enviam o UID como teclas normais. Neste dispositivo `1A86:E010`, ele registrou apenas `ESC`, entao nao e o caminho principal.

Se o monitor HID mostrar `raw_hex`, mas nao acertar o `candidato=...`, cole a saida aqui que eu ajusto o parser para o formato exato do seu leitor.

## Observacao importante

A porta `COM5` vista no projeto continua parecendo ser o adaptador serial CH343 da ESP32. O leitor USB novo nao apareceu como porta serial utilizavel neste computador.