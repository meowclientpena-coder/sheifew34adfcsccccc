# Парсер VPN конфигов

Веб-сервер раз в час скачивает текстовые файлы с указанных URL и отдаёт их по защищённым маршрутам в виде сырого текста (`text/plain`).

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

или

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Сервер будет доступен по адресу http://localhost:8000

## Маршруты

| Маршрут | Источник |
|--------|----------|
| `/free` | freeserver.txt |
| `/defaultrexdsubfsd32` | BLACK_VLESS_RUS_mobile.txt |
| `/str032fngsub23fa` | BLACK_SS+All_RUS.txt |
| `/white34gfsliteeeew` | WHITE-SNI-RU-all.txt |
| `/whitwfewefeliteee123` | WHITE-CIDR-RU-checked.txt |

Главная страница `/` — список ссылок на эти эндпоинты. Данные обновляются каждый час (в :00 минут). При отсутствии данных в кеше сервер попытается подгрузить их по запросу; при неудаче вернётся 503.
