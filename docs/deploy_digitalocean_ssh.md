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
.\deploy\deploy_do_ssh.ps1 -ServerHost "SEU_IP" -User "root" -KeyPath "C:\caminho\sua-chave.pem"
```

Opcional: definir diretório remoto:

```powershell
.\deploy\deploy_do_ssh.ps1 -ServerHost "SEU_IP" -User "root" -KeyPath "C:\caminho\sua-chave.pem" -RemoteDir "/root/checkcheck"
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

## 6) Deploy automatico a cada push (GitHub Actions)
O workflow `deploy-oceandrive.yml` foi adicionado em `.github/workflows/`.

Para ativar:

1. Use o repositorio `git@github.com:tscode-com-br/checking.git` como `origin` local.
2. No repositorio GitHub, abra `Settings > Secrets and variables > Actions`.
3. Crie os secrets abaixo:
  - `OCEAN_HOST`: IP do droplet (ex.: `157.230.35.21`)
  - `OCEAN_USER`: usuario SSH (ex.: `root`)
  - `OCEAN_SSH_KEY`: chave privada SSH usada no acesso ao servidor
  - `OCEAN_APP_DIR`: diretorio do app no servidor (atual: `/root/checkcheck`)
  - `OCEAN_PORT`: porta SSH (normalmente `22`)
4. Garanta que o arquivo `.env` ja exista no servidor em `OCEAN_APP_DIR`.
5. Dê push na branch `main`.

Com isso, todo push na branch `main`:

1. Faz checkout do codigo mais recente no GitHub Actions.
2. Cria o diretorio remoto caso ele ainda nao exista.
3. Sincroniza o codigo no servidor por SSH, sem enviar `.env`, banco local nem chaves de deploy.
4. Sobe primeiro o servico `db` e depois executa `docker compose up -d --build --remove-orphans` para atualizar os servicos.
5. Valida `http://127.0.0.1:8000/api/health` no servidor, registra o commit implantado em `.deploy-release` e falha o workflow se a aplicacao nao subir.

## 7) Remoto Git recomendado
No clone local, padronize o remoto principal:

```powershell
git remote remove checkingapi
git remote set-url origin https://github.com/tscode-com-br/checking.git
git push -u origin main
```

Se a maquina local tiver chave SSH autorizada no GitHub, voce pode usar `git@github.com:tscode-com-br/checking.git` no lugar da URL HTTPS.
