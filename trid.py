from urllib.parse import urlparse
import bs4
import httpx
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import generate_headers, get_ondemand_file_url
import asyncio

ct = None


async def init_trid(headers={}):
    global ct
    session = httpx.AsyncClient(headers={**generate_headers(), **headers})

    home_page = await session.get(url="https://x.com")
    home_page_response = bs4.BeautifulSoup(home_page.content, 'html.parser')

    ondemand_file_url = get_ondemand_file_url(response=home_page_response)
    ondemand_file = await session.get(url=ondemand_file_url)
    ondemand_file_response = bs4.BeautifulSoup(ondemand_file.content, 'html.parser')
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
