from urllib.parse import urlparse
import bs4
import httpx
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers, get_ondemand_file_url
import asyncio
import time
import os
import json

ct = None
CACHE_FILE = 'trid_cache.json'
CACHE_TTL = 60 * 60


def read_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        data = json.loads(open(CACHE_FILE, 'r', encoding='utf-8').read())
        if time.time() - data.get('ts', 0) > CACHE_TTL:
            return None
        return data
    except Exception:
        return None


def write_cache(items):
    try:
        data = {'ts': int(time.time()), **items}
        open(CACHE_FILE, 'w', encoding='utf-8').write(json.dumps(data))
    except Exception:
        pass


async def init_trid(headers={}):
    global ct
    cached = read_cache()
    if cached and 'home_page' in cached and 'ondemand_file' in cached:
        home_page_response = bs4.BeautifulSoup(cached['home_page'], 'html.parser')
        class Bla(bs4.BeautifulSoup):
            text = cached['ondemand_file']
        ondemand_file_response = Bla()
        ct = ClientTransaction(
            home_page_response=home_page_response,
            ondemand_file_response=ondemand_file_response
        )
        return
    session = httpx.AsyncClient(headers={**generate_headers(), **headers})

    home_page = await session.get(url="https://x.com")
    home_page_response = bs4.BeautifulSoup(home_page.content, 'html.parser')

    ondemand_file_url = get_ondemand_file_url(response=home_page_response)
    ondemand_file = await session.get(url=ondemand_file_url)
    class Bla(bs4.BeautifulSoup):
        text = ondemand_file.text
    ondemand_file_response = Bla()
    write_cache({
        'home_page': home_page.text,
        'ondemand_file': ondemand_file.text
    })
    # ondemand_file_response = bs4.BeautifulSoup(ondemand_file.content, 'html.parser')
    ct = ClientTransaction(
        home_page_response=home_page_response,
        ondemand_file_response=ondemand_file_response
    )


def gen_trid(method, url):
    return ct.generate_transaction_id(method=method, path=urlparse(url=url).path)


async def main():
    await init_trid({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0'
    })
    print(gen_trid("POST", "https://x.com/i/api/1.1/jot/client_event.json"))

if __name__ == "__main__":
    asyncio.run(main())
