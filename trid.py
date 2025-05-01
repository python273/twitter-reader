import httpx
from urllib.parse import urlparse
from x_client_transaction.utils import handle_x_migration
from x_client_transaction import ClientTransaction

ct = None

def init_trid(headers={}):
    global ct
    headers = {
        "Authority": "x.com",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Referer": "https://x.com",
        "X-Twitter-Active-User": "yes",
        "X-Twitter-Client-Language": "en",
        **headers,
    }
    session = httpx.Client()
    session.headers = headers
    response = handle_x_migration(session)
    ct = ClientTransaction(response)


def gen_trid(method, url):
    path = urlparse(url=url).path
    return ct.generate_transaction_id(method=method, path=path)


if __name__ == "__main__":
    init_trid({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0'
    })
    print(gen_trid("POST", "https://x.com/i/api/1.1/jot/client_event.json"))
