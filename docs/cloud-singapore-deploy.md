# Migrar servidor para nuvem barata (Singapura)

Sim, é possível migrar o servidor do CheckCheck para nuvem e reduzir custo inicial de hardware local.

## Recomendação prática (baixo custo)

### Opção A (mais barata): Oracle Cloud Always Free (Singapore)

- Custo: pode ser `US$0` (sujeito à disponibilidade da região).
- Prós: muito barato, bom para MVP.
- Contras: capacidade gratuita pode não estar sempre disponível.

### Opção B (previsível): VPS básica em SG (Vultr / Contabo / similares)

- Faixa comum: `US$5–8/mês`.
- Prós: custo previsível, setup simples.
- Contras: não é gratuito.

## O que muda no projeto

- O backend Node.js roda na nuvem (porta 3000 atrás de reverse proxy).
- O banco pode continuar SQLite (MVP), idealmente com backup diário.
- A ESP32 passa a enviar para URL pública HTTPS (`https://seu-dominio/api/scan`).
- Dashboard público em `https://seu-dominio`.

## Riscos e mitigação

- Dependência da internet local para registrar presença.
- Se cair internet do escritório, o registro para.
- Mitigação recomendada:
  - watchdog de conectividade na ESP32,
  - fila local de leituras pendentes (e envio quando reconectar),
  - monitoramento de uptime no servidor.

## Arquitetura sugerida em nuvem

1. VM Linux (Ubuntu 22.04 LTS) em região Singapore.
2. Node.js 20+.
3. Nginx (TLS com Let's Encrypt).
4. PM2 ou systemd para manter processo ativo.
5. Firewall liberando apenas 80/443.

## Passos rápidos de migração

1. Subir VM em SG.
2. Clonar repositório e executar:

```bash
cd apps/raspberry-server
cp .env.example .env
npm install
npm run start
```

3. Configurar Nginx + TLS.
4. Atualizar firmware ESP32 (`API_URL`) para domínio público HTTPS.
5. Validar:
  - `GET /api/status`
  - dashboard carregando
  - leitura RFID chegando em tempo real

## Quando manter Raspberry local ainda faz sentido

- Internet instável no escritório.
- Exigência de operar 100% offline localmente.
- Requisito de latência/localidade sem depender de WAN.
