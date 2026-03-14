# Деплой на хостинг и подключение своего домена

Кратко: куда залить проект, как запустить и как подвязать домен с HTTPS.

---

## Вариант 1: PaaS (проще всего)

**Railway**, **Render**, **Fly.io** — загружаешь код (Git), они сами поднимают приложение и дают URL. Свой домен подключается в панели.

### Railway (рекомендуется для старта)

1. Зарегистрируйся на [railway.app](https://railway.app), подключи GitHub (или залей репозиторий).
2. **New Project** → **Deploy from GitHub** → выбери репозиторий с этим проектом.
3. В настройках сервиса:
   - **Root Directory**: оставь пустым или укажи папку с `main.py`.
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py` или `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Деплой запустится сам. Railway выдаст URL вида `https://твой-проект.up.railway.app`.

**Свой домен:**

- В проекте: **Settings** → **Domains** → **Custom Domain** → введи домен (например `vpn.example.com`).
- В панели у регистратора домена (Reg.ru, Cloudflare, и т.д.) создай запись:
  - Тип **CNAME**, имя `vpn` (или `@` если нужен корень), значение — тот хост, что показал Railway (часто `твой-проект.up.railway.app`).
- HTTPS Railway обычно выставляет сам.

### Render

1. [render.com](https://render.com) → **New** → **Web Service**, подключи репозиторий.
2. **Build**: `pip install -r requirements.txt`  
   **Start**: `python main.py` или `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. В **Settings** → **Custom Domain** добавь свой домен и по подсказкам Render настрой CNAME у регистратора.

---

## Вариант 2: VPS (свой сервер)

Подойдёт любой VPS (Timeweb, Selectel, DigitalOcean, etc.) с Ubuntu/Debian.

### 1. Подключение к серверу

```bash
ssh root@IP_ТВОЕГО_СЕРВЕРА
```

### 2. Установка Python и клонирование проекта

```bash
apt update && apt install -y python3 python3-pip python3-venv git
git clone https://github.com/ТВОЙ_ЛОГИН/твой-репо.git /opt/vpn-parser
cd /opt/vpn-parser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Если кода нет в Git — скопируй папку на сервер через `scp` или SFTP.

### 3. Запуск как сервис (systemd)

Создай файл сервиса:

```bash
nano /etc/systemd/system/vpn-parser.service
```

Содержимое:

```ini
[Unit]
Description=VPN Config Parser
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn-parser
Environment="PATH=/opt/vpn-parser/venv/bin"
ExecStart=/opt/vpn-parser/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Запуск и автозапуск:

```bash
systemctl daemon-reload
systemctl enable vpn-parser
systemctl start vpn-parser
systemctl status vpn-parser
```

Приложение будет слушать порт **8000**.

### 4. Nginx как обратный прокси (порт 80/443 и домен)

```bash
apt install -y nginx certbot python3-certbot-nginx
nano /etc/nginx/sites-available/vpn-parser
```

Конфиг (замени `vpn.example.com` на свой домен):

```nginx
server {
    listen 80;
    server_name vpn.example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Включи сайт и получи SSL:

```bash
ln -s /etc/nginx/sites-available/vpn-parser /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d vpn.example.com
```

Certbot сам настроит HTTPS и продление сертификата.

### 5. Подключение домена на стороне регистратора

- Если хостинг даёт тебе **IP** (VPS):
  - Создай запись **A**: имя `vpn` (или `@`), значение = IP сервера.
- Если дают **CNAME** (PaaS):
  - Создай запись **CNAME**: имя `vpn`, значение = хост из панели (например `твой-проект.up.railway.app`).

Подожди 5–30 минут пока обновится DNS, затем открой `https://vpn.example.com`.

---

## Чек-лист

| Шаг | PaaS (Railway/Render) | VPS |
|-----|------------------------|-----|
| Залить код | Git push / деплой из репо | Git clone или scp в `/opt/vpn-parser` |
| Запуск | Build + Start в панели | systemd сервис `vpn-parser` |
| Порт | Используется `PORT` из окружения | Внутри слушаем 8000, снаружи nginx 80/443 |
| Домен | Custom Domain в настройках + CNAME | A-запись на IP + nginx + certbot |
| HTTPS | Обычно из коробки | certbot --nginx |

После этого твой домен будет открывать главную страницу и эндпоинты с конфигами.
