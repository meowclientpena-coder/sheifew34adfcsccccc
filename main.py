"""
Парсер VPN конфигов с публичных эндпоинтов.
Сервер раз в час скачивает текстовые файлы по URL и отдаёт их по защищённым маршрутам.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse

# Соответствие маршрут -> URL источника
ROUTE_TO_URL = {
    "/free": "https://raw.githubusercontent.com/zenithdlcc-cmd/freevpnShieldWalker/refs/heads/main/freeserver.txt",
    "/defaultrexdsubfsd32": "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_VLESS_RUS_mobile.txt",
    "/str032fngsub23fa": "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/BLACK_SS%2BAll_RUS.txt",
    "/white34gfsliteeeew": "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-SNI-RU-all.txt",
    "/whitwfewefeliteee123": "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-checked.txt",
}

# In-memory хранилище: маршрут -> содержимое (или None при ошибке)
store: dict[str, Optional[str]] = {route: None for route in ROUTE_TO_URL}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VPN Config Parser")


async def fetch_url(client: httpx.AsyncClient, route: str, url: str) -> tuple[str, bool, Optional[str]]:
    """Скачивает содержимое по URL. Возвращает (route, success, text или None)."""
    try:
        r = await client.get(url, timeout=30.0)
        r.raise_for_status()
        text = r.text
        return (route, True, text)
    except Exception as e:
        logger.warning("Парсинг %s (%s): ошибка — %s", route, url, e)
        return (route, False, None)


async def run_parser() -> None:
    """Скачивает данные со всех источников. При ошибке по одному URL — не трогаем значение в store."""
    logger.info("=== Запуск парсинга источников ===")
    start = datetime.now()
    async with httpx.AsyncClient() as client:
        tasks = [fetch_url(client, route, url) for route, url in ROUTE_TO_URL.items()]
        results = await asyncio.gather(*tasks)
    for route, success, text in results:
        if success and text is not None:
            store[route] = text
            logger.info("Парсинг %s: успех", route)
        else:
            # Оставляем старые данные; если не было — остаётся None
            if store.get(route) is None:
                logger.warning("Парсинг %s: ошибка, данных нет (будут 503 или синхронная подгрузка)", route)
            else:
                logger.warning("Парсинг %s: ошибка, оставлены старые данные", route)
    elapsed = (datetime.now() - start).total_seconds()
    logger.info("=== Парсинг завершён за %.2f с ===", elapsed)


async def fetch_single(route: str) -> Optional[str]:
    """Синхронная подгрузка одного источника при запросе (если в кеше пусто)."""
    url = ROUTE_TO_URL.get(route)
    if not url:
        return None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=30.0)
            r.raise_for_status()
            return r.text
    except Exception as e:
        logger.warning("Подгрузка по запросу %s: %s", route, e)
        return None


def get_endpoint(route: str):
    """Фабрика эндпоинтов: отдаёт text/plain или 503 / подгрузку."""

    async def handler():
        data = store.get(route)
        if data is None:
            data = await fetch_single(route)
        if data is None:
            return PlainTextResponse(content="Service Unavailable", status_code=503, media_type="text/plain")
        return PlainTextResponse(content=data, media_type="text/plain")

    return handler


# Регистрация маршрутов
for route in ROUTE_TO_URL:
    app.add_api_route(route, get_endpoint(route), methods=["GET"], name=route.lstrip("/").replace("/", "_") or "index")


@app.get("/")
async def index():
    """Главная страница: список ссылок на эндпоинты и описание."""
    html = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Config Parser</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
        h1 { font-size: 1.25rem; }
        p { color: #555; }
        ul { list-style: none; padding: 0; }
        li { margin: 0.5rem 0; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Парсер VPN конфигов</h1>
    <p>Данные обновляются автоматически раз в час. Ниже — ссылки на эндпоинты (сырой текст, text/plain).</p>
    <ul>
"""
    for route in ROUTE_TO_URL:
        html += f'        <li><a href="{route}">{route}</a></li>\n'
    html += """    </ul>
</body>
</html>
"""
    return HTMLResponse(html)


@app.on_event("startup")
async def startup():
    """Запуск планировщика и первый парсинг."""
    scheduler = AsyncIOScheduler()
    # Каждый час в 00 минут
    scheduler.add_job(run_parser, "cron", minute=0)
    scheduler.start()
    logger.info("Планировщик запущен: парсинг каждый час в :00")
    # Первый парсинг сразу после старта
    await run_parser()


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
