# Publicação no GitHub

## 1) Configurar identidade Git (se necessário)

```bash
git config --global user.name "Seu Nome"
git config --global user.email "tamer79@gmail.com"
```

## 2) Inicializar repositório local (se ainda não estiver inicializado)

```bash
git init
git add .
git commit -m "chore: initial checkcheck project"
```

## 3) Conectar ao repositório remoto

```bash
git remote add origin <URL_DO_REPOSITORIO_GITHUB>
git branch -M main
git push -u origin main
```

## 4) Autenticação recomendada

- Use Git Credential Manager (login no navegador) ou Personal Access Token.
- Evite compartilhar senha/e-mail em texto para automações.
