# Deploy na VPS

Arquitetura: o GitHub Actions constrói a imagem e publica no GHCR. A VPS
só puxa a imagem e roda. A VPS **não** precisa de Python, nem de git, nem
do código-fonte.

```
push na main → Actions (test → docker → publicar) → ghcr.io
                                                       ↓ docker compose pull
                                               VPS: Caddy (443) → app (8000)
```

---

## Pré-requisito: DNS

Antes de qualquer coisa, aponte um registro **A** do seu domínio para o IP
da VPS. O Caddy só consegue emitir o certificado se o domínio já resolver
para o servidor — se o DNS não estiver propagado, ele falha e o Let's
Encrypt tem rate limit semanal, então não fique tentando em loop.

Confirme antes de prosseguir:

```bash
dig +short radar.seudominio.com    # deve devolver o IP da VPS
```

---

## 1. Docker na VPS

```bash
ssh usuario@IP_DA_VPS

# Script oficial da Docker. Instala engine + compose plugin.
curl -fsSL https://get.docker.com | sh

# Rodar docker sem sudo. Precisa relogar para valer.
sudo usermod -aG docker $USER
exit
```

Entre de novo e confirme:

```bash
ssh usuario@IP_DA_VPS
docker --version && docker compose version
```

---

## 2. Firewall

```bash
sudo ufw allow 22/tcp      # NÃO esqueça esta linha antes de habilitar
sudo ufw allow 80/tcp      # Let's Encrypt valida por aqui
sudo ufw allow 443/tcp
sudo ufw allow 443/udp     # HTTP/3
sudo ufw enable
sudo ufw status
```

> A porta 8000 fica fechada de propósito. A app não publica porta no host —
> só o Caddy a alcança pela rede interna do Docker.

---

## 3. Autenticar no GHCR

O repositório é privado, então a imagem também é. A VPS precisa de
credencial para puxar.

Crie um token em **GitHub → Settings → Developer settings → Personal access
tokens → Tokens (classic)**, com o escopo **`read:packages`** e nada mais.
Não use um token com permissão de escrita num servidor.

```bash
# Cole o token quando pedir a senha. O --password-stdin evita que ele
# fique no histórico do shell.
echo "COLE_O_TOKEN_AQUI" | docker login ghcr.io -u Leandrosmoreira --password-stdin
```

> Alternativa: tornar o *package* público em
> `github.com/users/Leandrosmoreira/packages/container/ai-jobs-radar/settings`.
> Aí a VPS puxa sem autenticação nenhuma, e o repo de código continua
> privado. Mais simples, mas a imagem fica aberta.

---

## 4. Arquivos na VPS

```bash
mkdir -p ~/ai-jobs-radar && cd ~/ai-jobs-radar
```

Copie os dois arquivos de [`deploy/`](../deploy) para cá. Da sua máquina:

```bash
scp deploy/compose.yaml deploy/Caddyfile usuario@IP_DA_VPS:~/ai-jobs-radar/
```

Crie o `.env` **na VPS** (ele não vai para o git):

```bash
cd ~/ai-jobs-radar
echo "DOMINIO=radar.seudominio.com" > .env
```

---

## 5. Subir

```bash
cd ~/ai-jobs-radar
docker compose pull
docker compose up -d
docker compose ps        # ambos devem estar "running"
```

Acompanhe o Caddy pegando o certificado (leva alguns segundos):

```bash
docker compose logs -f caddy
```

---

## 6. Verificar

```bash
curl -i https://radar.seudominio.com/health
```

Esperado: `HTTP/2 200` e corpo `{"status":"ok"}`.

Confirme também que a app **não** está exposta direto — isto deve dar
timeout ou connection refused:

```bash
curl --max-time 5 http://IP_DA_VPS:8000/health
```

---

## 7. Atualizar depois de um push

```bash
cd ~/ai-jobs-radar
docker compose pull && docker compose up -d
docker image prune -f     # remove as imagens antigas órfãs
```

---

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| `denied` no `docker compose pull` | token sem `read:packages`, ou expirado |
| `manifest unknown` | o job `publicar` ainda não rodou; confira o Actions |
| Caddy em loop pedindo certificado | DNS não resolve para a VPS, ou porta 80 fechada |
| `502 Bad Gateway` | a app caiu — veja `docker compose logs app` |
| Container reiniciando | `docker compose logs app`; cheque o HEALTHCHECK |

Logs e estado:

```bash
docker compose logs -f app       # só a aplicação
docker compose logs -f           # tudo
docker compose restart app
docker compose down              # derruba (preserva os volumes)
```
