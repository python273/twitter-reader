import collections
from datetime import datetime, timedelta, UTC
import json
from pprint import pprint
import time
import traceback
import httpx
import sys
import asyncio
import inspect
import random
try:
    import uvloop
    uvloop_installed = True
except ImportError:
    uvloop = None
    uvloop_installed = False

from aio_pool import AioPool

red_color = "\033[91m"
green_color = "\033[92m"
reset_color = "\033[0m"

USERAGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0'

async def sure(fn, max_sleep=32):
    t = 1
    while True:
        try:
            return await fn()
        except Exception:
            print(f'sure failed', inspect.getsource(fn).strip())
            traceback.print_exc()
            await asyncio.sleep(t)
            t = min(max_sleep, t * 2)


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
        data, lambda d: d.get('itemType') == 'TimelineTimelineCursor')


def find_all_tweets(data):
    return find_dicts_deep(data, lambda d: d.get('__typename') == 'Tweet')


def find_all_users(data):
    return find_dicts_deep(data, lambda d: d.get('__typename') == 'User')


async def load_tweet(session, tweet_id, cursor):
    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.5',
        'x-twitter-client-language': 'en',
        'x-twitter-active-user': 'yes',
    }

    cursor_str = ''
    if cursor:
        cursor_str = f'"cursor":"{cursor}","referrer":"tweet",'

    params = {
        'variables': f'{{"focalTweetId":"{tweet_id}",{cursor_str}"with_rux_injections":false,"rankingMode":"Relevance","includePromotedContent":true,"withCommunity":true,"withQuickPromoteEligibilityTweetFields":true,"withBirdwatchNotes":true,"withVoice":true}}',
        'features': '{"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}',
        'fieldToggles': '{"withArticleRichContentState":true,"withArticlePlainText":false,"withGrokAnalyze":false,"withDisallowedReplyControls":false}',
    }

    r = await session.get(
        'https://x.com/i/api/graphql/nBS-WpgA6ZG0CyNHD517JQ/TweetDetail',
        params=params,
        headers=headers,
        timeout=20.0,
    )
    if r.status_code == 429:  # ratelimit
        print(r.headers)
        try:
            print(r.json())
        except Exception:
            print('json decode error', r.content)

        if r.headers.get('x-rate-limit-remaining') == '0':
            raise RateLimitError(
                datetime.fromtimestamp(int(r.headers['x-rate-limit-reset']), tz=UTC)
            )
        else:
            # {'errors': [{'code': 88, 'message': 'Rate limit exceeded.'}]}
            raise RateLimitError(datetime.now(UTC) + timedelta(hours=24))

    try:
        j = r.json()
    except Exception:
        print('json decode error', r.status_code, r.content)
        raise

    if j == {'errors': [{'message': 'Invalid or expired token', 'code': 89}]}:
        raise InvalidTokenError

    return j


def get_tweet_ids_belonging_to_thread(tweets, thread_id):
    # should ignore quoted tweets in `tweets` list
    thread = set()
    thread.add(thread_id)

    while True:
        added = 0
        for t in tweets:
            should_add = (
                t['rest_id'] not in thread
                and t['legacy'].get('in_reply_to_status_id_str', -1) in thread
            )
            if not should_add:
                continue
            thread.add(t['rest_id'])
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
                f'Fetched {tweet_id!r} {"*" if cursor else ""} '
                f'({pool.responses_count} / {total_count})'
            )

            if 'errors' in response:
                print('Errors')
                print(response.get('errors'))
                # continue

            tweets = find_all_tweets(response)
            tweets.extend([i['tweet'] for i in find_dicts_deep(
                response,
                lambda d: d.get('__typename') == 'TweetWithVisibilityResults'
            )])
            users = find_all_users(response)
            cursors = find_all_cursors(response)

            for t in tweets:
                try:
                    tl = t['legacy']
                except KeyError:
                    print('#legacy', t)
                    traceback.print_exc()
                    continue
                tid = t['rest_id']
                expected_replies_count[tid] = max(
                    expected_replies_count[tid], tl['reply_count'])

                if tid in loaded_tweets:
                    continue

                loaded_tweets[tid] = t
                if tl.get('in_reply_to_status_id_str'):
                    got_replies_count[tl['in_reply_to_status_id_str']] += 1

            for u in users:
                if 'rest_id' not in u:
                    print('#rest_id', u)
                    continue
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


class InvalidTokenError(Exception): pass


class RateLimitError(Exception):
    def __init__(self, till, *args: object) -> None:
        super().__init__(*args)
        self.till = till


class SessionManager:
    def __init__(self, accounts) -> None:
        self.sessions = []
        for acc_data in accounts:
            csrf_handler = HttpxTwitterCsrf()
            session = httpx.AsyncClient(
                http2=True,
                event_hooks={'request': [csrf_handler]}
            )
            csrf_handler.session = session
            trid = 'ZTpUeXBlRXJyb3I6IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKC4uLikgaXMgbnVsbA=='
            session.headers = {
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'content-type': 'application/json',
                'x-twitter-auth-type': 'OAuth2Session',
                'x-twitter-client-language': 'en',
                'x-twitter-active-user': 'yes',
                'x-client-transaction-id': trid,
                'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            }
            session.cookies.update(acc_data['cookies'])
            session.headers['User-Agent'] = USERAGENT
            self.sessions.append({
                'invalid': False,
                'session': session,
                'ratelimit_till': datetime.now(UTC) - timedelta(minutes=1)
            })

    def get_session(self):
        for i in random.sample(self.sessions, k=len(self.sessions)):
            if i['invalid']:
                continue

            if i['ratelimit_till'] < datetime.now(UTC):
                return i['session']

    def ratelimit(self, session, till):
        for i in self.sessions:
            if i['session'] == session:
                i['ratelimit_till'] = till
                break

    def invalidate(self, session):
        raise Exception
        for i in self.sessions:
            if i['session'] == session:
                i['invalid'] = True
                break


async def worker_fn(worker_id: int, manager: SessionManager, tweet_id, cursor):
    while True:
        print(f'[{worker_id}] fetching {tweet_id!r} {"*" if cursor else ""}')

        while True:
            try:
                session = manager.get_session()
                if session:
                    r = await load_tweet(session, tweet_id, cursor)
                    await asyncio.sleep(0.5)
                    print(f'[{worker_id}] done')
                    return r
            except InvalidTokenError as e:
                print(f'[{worker_id}] invalid token')
                manager.invalidate(session)
                await asyncio.sleep(0.01)
                continue
            except RateLimitError as e:
                print(f'[{worker_id}] rate limited {e.till}')
                manager.ratelimit(session, e.till)
            except httpx.RequestError as e:
                print(f'could not load tweet (network error). Error: {e}')
            except asyncio.exceptions.CancelledError:
                raise
            except Exception:
                print('could not load tweet. Traceback:')
                traceback.print_exc()
                exit(1)
            await asyncio.sleep(5)


class HttpxTwitterCsrf:
    def __init__(self):
        self.session = None

    async def handle(self, request):
        request.headers['x-csrf-token'] = self.session.cookies.get('ct0')

    def __call__(self, *args, **kwargs):
        return self.handle(*args, **kwargs)


async def main():
    thread_id = sys.argv[1]

    num_workers = 2

    try:
        with open('accounts.json') as f:
            accounts_data = json.load(f)
    except FileNotFoundError:
        print('Create accounts.json with cookies from browser: {"accounts": [{"cookies": {...}}, ...]}')
        exit(1)

    manager = SessionManager(accounts_data['accounts'])
    worker_args = [(worker_id, manager) for worker_id in range(num_workers)]
    pool = AioPool(num_workers, worker_fn, worker_args)

    st = time.monotonic()
    thread = await load_tree(pool, thread_id)

    print()
    print('*' * 80)
    print('DONE', pool.requests_count, pool.responses_count)
    print('TOOK', time.monotonic() - st)
    print()

    await pool.shutdown()

    with open(f'threads/thread_{thread_id}.json', 'w') as f:
        json.dump(thread, f, ensure_ascii=False)


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
