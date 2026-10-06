# Deploy na VPS

Arquitetura: o GitHub Actions constrói a imagem e publica no GHCR. A VPS
só puxa a imagem e roda. A VPS **não** precisa de Python, nem de git, nem
do código-fonte.

```
push na main → Actions (test → docker → publicar) → ghcr.io
                                                       ↓ docker compose pull
                                               VPS: Caddy (443) → app (8000)
```

Há dois caminhos:

- **VPS dedicada ao radar** → seções 1 a 7 abaixo (Caddy no compose).
- **VPS compartilhada (Contabo, o caminho em uso hoje)** → seção
  [VPS compartilhada com nginx](#vps-compartilhada-com-nginx-contabo), no fim.

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

> **Estado atual: o package é público** (decidido em 06/10/2026), então este
> passo não é mais necessário — a VPS puxa sem autenticação e o repo de
> código continua privado. Para mudar: logado como `Leandrosmoreira`, abra
> `github.com/users/Leandrosmoreira/packages/container/package/ai-jobs-radar`
> → *Package settings → Danger Zone → Change visibility*.
>
> Por que público: é projeto de portfólio, e assim não fica token guardado
> na VPS (o `read:packages` classic lê **todos** os seus pacotes) nem token
> para renovar. A regra que isso impõe: **nenhum segredo dentro da imagem** —
> chaves de API entram por variável de ambiente no compose, via `.env` na VPS.

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

## VPS compartilhada com nginx (Contabo)

É o deploy em uso hoje: **https://radar.13-140-42-86.sslip.io/health**.

Na Contabo (`13.140.42.86`) o nginx já ocupa as portas 80/443 atendendo o
painel do uso e o yldlab-mcp, então o Caddy do compose não pode subir ali.
Em vez dele:

```
internet → nginx (443, TLS do certbot) → 127.0.0.1:8083 → container (8000)
```

Arquivos: [`deploy/compose.vps.yaml`](../deploy/compose.vps.yaml) (só a app,
sem Caddy) e [`deploy/nginx-radar.conf`](../deploy/nginx-radar.conf) (o
site). O domínio é do [sslip.io](https://sslip.io): `radar.13-140-42-86.sslip.io`
resolve sozinho para o IP, sem comprar domínio nem configurar DNS.

Portas já usadas na VPS: 8000 (yldlab-mcp), 8081/8082 (iracingeng), 8090
(mapa). O radar usa a **8083**, publicada só em `127.0.0.1` — sem isso o
Docker abriria a porta para a internet passando por cima do `ufw`.

### Usuário e permissões

- Entra-se como `uso` (`ssh contabo`, chave `id_ed25519_contabo`). Não existe
  usuário `deploy`.
- O `uso` foi criado **sem senha** (`adduser --disabled-password`). Para o
  `sudo` funcionar foi preciso definir uma, como root, pelo console VNC da
  Contabo — o SSH do root só aceita chave (`PasswordAuthentication no`).
- O `uso` está no grupo `docker` (`usermod -aG docker uso`), então
  `docker compose` roda sem `sudo`. Atenção: grupo `docker` equivale a root.
- nginx e certbot continuam exigindo `sudo`.

### Primeira instalação

Da sua máquina:

```bash
ssh contabo 'mkdir -p ~/ai-jobs-radar'
scp deploy/compose.vps.yaml deploy/nginx-radar.conf contabo:~/ai-jobs-radar/
```

Na VPS (`ssh -t contabo`):

```bash
cd ~/ai-jobs-radar
docker compose -f compose.vps.yaml pull
docker compose -f compose.vps.yaml up -d
curl -fsS http://127.0.0.1:8083/health      # {"status":"ok"}

sudo cp nginx-radar.conf /etc/nginx/sites-available/ai-jobs-radar
sudo ln -s /etc/nginx/sites-available/ai-jobs-radar /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d radar.13-140-42-86.sslip.io   # aceite o redirect p/ HTTPS
```

O certbot **edita** o arquivo em `/etc/nginx/sites-enabled/` (bloco 443 +
redirect). Por isso a cópia do repositório não tem HTTPS — não sobrescreva o
arquivo da VPS com ela sem rodar o certbot de novo. A renovação é automática
(timer do systemd); o certificado atual vence em 04/01/2027.

### Atualizar depois de um push

```bash
ssh contabo 'cd ~/ai-jobs-radar && docker compose -f compose.vps.yaml pull && docker compose -f compose.vps.yaml up -d && docker image prune -f'
```

### Verificar

```bash
curl -i https://radar.13-140-42-86.sslip.io/health    # 200, {"status":"ok"}
curl -I http://radar.13-140-42-86.sslip.io/health     # 301 → https
curl --max-time 5 http://13.140.42.86:8083/health     # deve dar timeout
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
