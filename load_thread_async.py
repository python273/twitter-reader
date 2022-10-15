import collections
from concurrent.futures import thread
import json
import time
import traceback
import httpx
import sys
import asyncio
try:
    import uvloop
    uvloop_installed = True
except ImportError:
    uvloop = None
    uvloop_installed = False

from aio_pool import AioPool

USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0"


def find_dicts_deep(data, fn_match):
    l = []
    if isinstance(data, dict):
        if fn_match(data):
            l.append(data)
        else:
            for v in data.values():
                l.extend(find_dicts_deep(v, fn_match))
    elif isinstance(data, list):
        for i in data:
            l.extend(find_dicts_deep(i, fn_match))
    return l


def find_all_cursors(data):
    return find_dicts_deep(
        data,
        lambda d: d.get('itemType') == 'TimelineTimelineCursor'
    )


def find_all_tweets(data):
    return find_dicts_deep(
        data,
        lambda d: ('id_str' in d) and ('full_text' in d) and ('retweet_count' in d)
    )


def find_all_users(data):
    return find_dicts_deep(
        data,
        lambda d: d.get('__typename') == 'User'
    )


AUTH_BEARER = 'AnTpCjWWGA33AF4uJvTLhjHc61qUI18FL8kftt7vZ1D3%sTup4zZnx8I6E5HuOCRjeUzIwNnAAAAAAgLIRNAAAAAAAAAAAAAAAAAAAAA reraeB'[::-1]


async def get_guest_id(session):
    headers = {
        'User-Agent': USERAGENT,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://twitter.com/',
        'authorization': AUTH_BEARER,
    }

    return (await session.post(
        f'https://api.twitter.com/1.1/guest/activate.json',
        headers=headers,
    )).json()['guest_token']


async def check_guest_id(guest_id):
    async with httpx.AsyncClient(http2=True) as session:
        session.headers['User-Agent'] = USERAGENT
        session.headers['x-guest-token'] = guest_id
        response = await session.post(
            'https://twitter.com/i/api/1.1/branch/init.json',
            headers={
                'x-guest-token': guest_id,
                'authorization': AUTH_BEARER,
            },
            json={},
        )
        if response.status_code == 200:
            return guest_id


async def load_tweet(session, tweet_id, cursor):
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'content-type': 'application/json',
        'authorization': AUTH_BEARER,
    }

    variables = {
        'focalTweetId': tweet_id,
        'includePromotedContent': True,
        'withBirdwatchNotes': False,
        'withCommunity': True,
        'withDownvotePerspective': False,
        'withQuickPromoteEligibilityTweetFields': True,
        'withReactionsMetadata': False,
        'withReactionsPerspective': False,
        'withSuperFollowsTweetFields': True,
        'withSuperFollowsUserFields': True,
        'withV2Timeline': True,
        'withVoice': True,
        'with_rux_injections': False
    }

    if cursor:
        variables.update({
            'cursor': cursor,
            'referrer': 'tweet'
        })

    params = {
        'variables': json.dumps(variables),
        'features': json.dumps({
            'dont_mention_me_view_api_enabled': True,
            'interactive_text_enabled': True,
            'responsive_web_edit_tweet_api_enabled': False,
            'responsive_web_like_by_author_enabled': False,
            'responsive_web_uc_gql_enabled': False
        }),
    }

    return (await session.get(
        'https://twitter.com/i/api/graphql/u3N3Hp5UJq5QMCR2yDwzaw/TweetDetail',
        params=params,
        headers=headers
    )).json()


def get_tweet_ids_belonging_to_thread(tweets, thread_id):
    # should ignore quoted tweets in `tweets` list
    thread = set()
    thread.add(thread_id)

    while True:
        added = 0
        for t in tweets:
            should_add = (
                t['id_str'] not in thread
                and t.get('in_reply_to_status_id_str', -1) in thread
            )
            if not should_add:
                continue
            thread.add(t['id_str'])
            added += 1

        if added == 0:
            break

    return thread


async def load_tree(pool: AioPool, thread_id):
    total_count = 0

    already_fetched = set()  # (tweet_id, cursor)
    already_fetched.add((thread_id, None))

    loaded_tweets = {}  # id -> tweet
    loaded_users = {}  # id -> user

    expected_replies_count = collections.Counter()  # tweet id -> count
    got_replies_count = collections.Counter()

    pool.put_task(thread_id, None)

    while True:
        async for (args, kwargs, response) in pool.results_iter():
            tweet_id, cursor = args
            total_count += 1

            print(
                f'Fetched {tweet_id} {bool(cursor)} ({pool.responses_count} / {total_count})'
            )

            if 'errors' in response:
                print('Errors')
                print(response)
                continue

            tweets = find_all_tweets(response)
            users = find_all_users(response)
            cursors = find_all_cursors(response)

            for t in tweets:
                expected_replies_count[t['id_str']] = max(
                    expected_replies_count[t['id_str']],
                    t['reply_count']
                )

                if t['id_str'] in loaded_tweets:
                    continue

                loaded_tweets[t['id_str']] = t
                if t.get('in_reply_to_status_id_str'):
                    got_replies_count[t['in_reply_to_status_id_str']] += 1

            for u in users:
                loaded_users[u['rest_id']] = u

            for c in cursors:
                if c['cursorType'] == 'Top':
                    continue

                f = (tweet_id, c['value'])
                if f not in already_fetched:
                    already_fetched.add(f)
                    pool.put_task(*f)

        # when no cursors are left to fetch,
        # check which tweets don't have all replies loaded

        thread = get_tweet_ids_belonging_to_thread(
            loaded_tweets.values(),
            thread_id
        )

        added = 0

        for tweet_id, expected in expected_replies_count.items():
            got = got_replies_count[tweet_id]
            if expected > got and tweet_id in thread:
                f = (tweet_id, None)
                if f not in already_fetched:
                    already_fetched.add(f)
                    pool.put_task(*f)
                    added += 1

        print()
        print('ADDED', added)
        print()

        if added == 0:
            break

    return {
        'thread_tweet_id': thread_id,
        'tweets': list(loaded_tweets.values()),
        'users': list(loaded_users.values()),
    }


async def worker_fn(worker_id, token, tweet_id, cursor):
    async with httpx.AsyncClient(http2=True) as session:
        session.headers['User-Agent'] = USERAGENT
        session.headers['x-guest-token'] = token

        while True:
            print(f'[{worker_id}] fetching {tweet_id} {bool(cursor)}')

            failed_requests = 0  # non-transport errors
            while failed_requests < 5:
                try:
                    r = await load_tweet(session, tweet_id, cursor)
                    print(f'[{worker_id}] done')
                    return r
                except httpx.RequestError:
                    print('could not load tweet (network error). Traceback:')
                    traceback.print_exc()
                    await asyncio.sleep(3)
                    continue
                except:
                    failed_requests += 1
                    print('could not load tweet. Traceback:')
                    traceback.print_exc()
                    await asyncio.sleep(3)
                    continue
            
            while True:
                await asyncio.sleep(10)
                try:
                    session.headers.pop('x-guest-token')
                    session.headers['x-guest-token'] = await get_guest_id(session)
                    break
                except:
                    print('could not refetch token. Traceback:')
                    traceback.print_exc()


async def main():
    thread_id = sys.argv[1]

    num_workers = 8

    try:
        with open('saved_tokens.txt') as f:
            tokens = [i.strip() for i in f.readlines()]
    except FileNotFoundError:
        tokens = []

    tokens = await asyncio.gather(*[check_guest_id(t) for t in tokens])
    tokens = [i for i in tokens if i]

    need_tokens = num_workers - len(tokens)
    if need_tokens > 0:
        print(f'Getting {need_tokens} tokens')
        new_tokens = await asyncio.gather(*[
            get_guest_id(httpx.AsyncClient(http2=True))
            for _ in range(need_tokens)
        ])
        tokens.extend(new_tokens)

    with open('saved_tokens.txt', 'w') as f:
        for i in tokens:
            f.write(f'{i}\n')

    worker_args = [(worker_id, t) for worker_id, t in enumerate(tokens)]
    pool = AioPool(num_workers, worker_fn, worker_args)

    st = time.monotonic()
    thread = await load_tree(pool, thread_id)

    print()
    print('*' * 80)
    print('DONE', pool.requests_count, pool.responses_count)
    print('TOOK', time.monotonic() - st)
    print()

    await pool.shutdown()

    with open(f'thread_{thread_id}.json', 'w') as f:
        json.dump(thread, f)


if __name__ == '__main__':
    # asyncio.run(main(), debug=True)
    # exit(0)
    if uvloop_installed:
        if sys.version_info >= (3, 11):
            with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
                runner.run(main())
        else:
            uvloop.install()
            asyncio.run(main())
    else:
        asyncio.run(main())
