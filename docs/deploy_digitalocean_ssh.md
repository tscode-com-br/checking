# Deploy da API na DigitalOcean via SSH

## 1) Preparar o Droplet (Ubuntu)
Conecte no servidor:

```bash
ssh -i /caminho/sua-chave user@SEU_IP
```

Instale Docker + Compose:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Saia e entre novamente no SSH para aplicar o grupo docker.

## 2) Preparar variaveis de producao no projeto local
No Windows, no projeto:

1. Copie `deploy/.env.production.example` para `.env`.
2. Preencha os valores reais: `POSTGRES_PASSWORD`, `FORMS_URL`, `DEVICE_SHARED_KEY`, `ADMIN_API_KEY`.

## 3) Executar deploy por SSH (Windows PowerShell)
No root do projeto:

```powershell
.\deploy\deploy_do_ssh.ps1 -Host "SEU_IP" -User "root" -KeyPath "C:\caminho\sua-chave.pem"
```

Opcional: definir diretório remoto:

```powershell
.\deploy\deploy_do_ssh.ps1 -Host "SEU_IP" -User "root" -KeyPath "C:\caminho\sua-chave.pem" -RemoteDir "~/apps/checkcheck"
```

## 4) Validar no servidor

```bash
docker ps
curl http://127.0.0.1:8000/api/health
```

Resposta esperada:

```json
{"status":"ok","app":"checking-sistema"}
```

## 5) Expor API publicamente (opcional)
Recomendado usar Nginx + HTTPS (Let's Encrypt) na frente da API em `:8000`.
