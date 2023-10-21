import collections
from datetime import datetime, timedelta
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
from twitter_hmac import get_oauth_authorization

red_color = "\033[91m"
green_color = "\033[92m"
reset_color = "\033[0m"

USERAGENT = 'TwitterAndroid/9.95.0-release.0 (29950000-r-0) ONEPLUS+A3010/9 (OnePlus;ONEPLUS+A3010;OnePlus;OnePlus3;0;;1;2016)'

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
        data,
        lambda d: d.get('itemType') == 'TimelineTimelineCursor'
    )


def find_all_tweets(data):
    return find_dicts_deep(
        data,
        lambda d: d.get('__typename') == 'Tweet'
    )


def find_all_users(data):
    return find_dicts_deep(
        data,
        lambda d: d.get('__typename') == 'User'
    )


AUTH_BEARER = 'Bearer AAAAAAAAAAAAAAAAAAAAAFXzAwAAAAAAMHCxpeSDG1gLNLghVe8d74hl6k4%3DRUMF4xAQLsbeBhTSRrCiQpJtxoGWeyHrDb5te2jpGskWDFW82F'


async def get_guest_id(session):
    headers = {
        'User-Agent': USERAGENT,
        'Authorization': AUTH_BEARER,
    }

    r_guest_token = (await session.post(
        f'https://api.twitter.com/1.1/guest/activate.json',
        headers=headers,
    )).json()
    print(f'{r_guest_token=}')
    guest_token = r_guest_token['guest_token']

    r_flow_token = (await session.post(
        'https://api.twitter.com/1.1/onboarding/task.json?flow_name=welcome&api_version=1&known_device_token=&sim_country_code=us',
        headers={
            'Authorization': AUTH_BEARER,
            'Content-Type': 'application/json',
            'User-Agent': USERAGENT,
            'X-Twitter-API-Version': '5',
            'X-Twitter-Client': 'TwitterAndroid',
            'X-Twitter-Client-Version': '9.95.0-release.0',
            'OS-Version': '28',
            'System-User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ONEPLUS A3010 Build/PKQ1.181203.001)',
            'X-Twitter-Active-User': 'yes',
            'X-Guest-Token': guest_token
        },
        data='{"flow_token":null,"input_flow_data":{"country_code":null,"flow_context":{"start_location":{"location":"splash_screen"}},"requested_variant":null,"target_user_id":0},"subtask_versions":{"generic_urt":3,"standard":1,"open_home_timeline":1,"app_locale_update":1,"enter_date":1,"email_verification":3,"enter_password":5,"enter_text":5,"one_tap":2,"cta":7,"single_sign_on":1,"fetch_persisted_data":1,"enter_username":3,"web_modal":2,"fetch_temporary_password":1,"menu_dialog":1,"sign_up_review":5,"interest_picker":4,"user_recommendations_urt":3,"in_app_notification":1,"sign_up":2,"typeahead_search":1,"user_recommendations_list":4,"cta_inline":1,"contacts_live_sync_permission_prompt":3,"choice_selection":5,"js_instrumentation":1,"alert_dialog_suppress_client_events":1,"privacy_options":1,"topics_selector":1,"wait_spinner":3,"tweet_selection_urt":1,"end_flow":1,"settings_list":7,"open_external_link":1,"phone_verification":5,"security_key":3,"select_banner":2,"upload_media":1,"web":2,"alert_dialog":1,"open_account":2,"action_list":2,"enter_phone":2,"open_link":1,"show_code":1,"update_users":1,"check_logged_in_account":1,"enter_email":2,"select_avatar":4,"location_permission_prompt":2,"notifications_permission_prompt":4}}'
    )).json()

    print(f'{r_flow_token=}')
    flow_token = r_flow_token['flow_token']

    r_subtasks = (await session.post(
        'https://api.twitter.com/1.1/onboarding/task.json',
        headers={
            'Authorization': AUTH_BEARER,
            'Content-Type': 'application/json',
            'User-Agent': USERAGENT,
            'X-Twitter-API-Version': '5',
            'X-Twitter-Client': 'TwitterAndroid',
            'X-Twitter-Client-Version': '9.95.0-release.0',
            'OS-Version': '28',
            'System-User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ONEPLUS A3010 Build/PKQ1.181203.001)',
            'X-Twitter-Active-User': 'yes',
            'X-Guest-Token': guest_token
        },
        data='{"flow_token":"' + flow_token + '","subtask_inputs":[{"open_link":{"link":"next_link"},"subtask_id":"NextTaskOpenLink"}],"subtask_versions":{"generic_urt":3,"standard":1,"open_home_timeline":1,"app_locale_update":1,"enter_date":1,"email_verification":3,"enter_password":5,"enter_text":5,"one_tap":2,"cta":7,"single_sign_on":1,"fetch_persisted_data":1,"enter_username":3,"web_modal":2,"fetch_temporary_password":1,"menu_dialog":1,"sign_up_review":5,"interest_picker":4,"user_recommendations_urt":3,"in_app_notification":1,"sign_up":2,"typeahead_search":1,"user_recommendations_list":4,"cta_inline":1,"contacts_live_sync_permission_prompt":3,"choice_selection":5,"js_instrumentation":1,"alert_dialog_suppress_client_events":1,"privacy_options":1,"topics_selector":1,"wait_spinner":3,"tweet_selection_urt":1,"end_flow":1,"settings_list":7,"open_external_link":1,"phone_verification":5,"security_key":3,"select_banner":2,"upload_media":1,"web":2,"alert_dialog":1,"open_account":2,"action_list":2,"enter_phone":2,"open_link":1,"show_code":1,"update_users":1,"check_logged_in_account":1,"enter_email":2,"select_avatar":4,"location_permission_prompt":2,"notifications_permission_prompt":4}}'
    )).json()
    print(f'{r_subtasks=}')
    subtasks = r_subtasks['subtasks']
    open_account = None
    for task in subtasks:
        if task['subtask_id'] == 'OpenAccount':
            open_account = task['open_account']
            break
    print(f'{open_account=}')

    if not open_account:
        raise Exception

    return {'guest_token': guest_token, 'account': open_account}


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
        'variables': f'{{"focalTweetId":"{tweet_id}",{cursor_str}"with_rux_injections":false,"includePromotedContent":true,"withCommunity":true,"withQuickPromoteEligibilityTweetFields":true,"withBirdwatchNotes":true,"withVoice":true,"withV2Timeline":true}}',

        'features': '{"rweb_lists_timeline_redesign_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":false,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_media_download_video_enabled":false,"responsive_web_enhance_cards_enabled":false}',
        'fieldToggles': '{"withArticleRichContentState":false}',
    }

    r = await session.get(
        'https://api.twitter.com/graphql/q94uRCEn65LZThakYcPT6g/TweetDetail',
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
                datetime.utcfromtimestamp(int(r.headers['x-rate-limit-reset']))
            )
        else:
            # {'errors': [{'code': 88, 'message': 'Rate limit exceeded.'}]}
            raise RateLimitError(datetime.utcnow() + timedelta(hours=24))

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
            users = find_all_users(response)
            cursors = find_all_cursors(response)

            for t in tweets:
                tl = t['legacy']
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
                    print(u)
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
        for i in accounts:
            session = httpx.AsyncClient(
                http2=True,
                event_hooks={'request': [HttpxTwitterSigner(i)]}
            )
            session.headers['User-Agent'] = USERAGENT
            self.sessions.append({
                'account': i,
                'session': session,
                'ratelimit_till': datetime.utcnow() - timedelta(minutes=1)
            })

    def get_accounts(self):
        return [i['account'] for i in self.sessions]

    def get_session(self):
        for i in random.sample(self.sessions, k=len(self.sessions)):
            if i['account'].get('_invalid'):
                continue

            if i['ratelimit_till'] < datetime.utcnow():
                return i['session']

    def ratelimit(self, session, till):
        for i in self.sessions:
            if i['session'] == session:
                i['ratelimit_till'] = till
                break

    def invalidate(self, session):
        for i in self.sessions:
            if i['session'] == session:
                i['account']['_invalid'] = True
                break


async def worker_fn(worker_id: int, manager: SessionManager, tweet_id, cursor):
    while True:
        print(f'[{worker_id}] fetching {tweet_id!r} {"*" if cursor else ""}')

        while True:
            try:
                session = manager.get_session()
                if session:
                    r = await load_tweet(session, tweet_id, cursor)
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
            await asyncio.sleep(10)


class HttpxTwitterSigner:
    def __init__(self, account) -> None:
        self.account = account

    async def handle(self, request):
        # print(f"{green_color}{request.method} {request.url}{reset_color}")
        request.headers['x-guest-token'] = self.account['guest_token']
        sign_data, authorization = get_oauth_authorization(
            self.account['account']['oauth_token'],
            self.account['account']['oauth_token_secret'],
            request.method, str(request.url)
        )
        request.headers['authorization'] = authorization

    def __call__(self, *args, **kwargs):
        return self.handle(*args, **kwargs)


async def main():
    thread_id = sys.argv[1]

    num_workers = 8

    try:
        with open('guest_accounts.json') as f:
            guest_accounts = json.load(f)
    except FileNotFoundError:
        guest_accounts = []

    print(f'Have {len(guest_accounts)} guest accounts')

    while True:
        try:
            a = await get_guest_id(httpx.AsyncClient(http2=True))
            guest_accounts.append(a)
        except:
            break
    
    print(f'Now have {len(guest_accounts)} guest accounts')

    with open('guest_accounts.json', 'w') as f:
        json.dump(guest_accounts, f)
    
    if not guest_accounts:
        print('No guest accounts, try different IP')
        return

    manager = SessionManager(guest_accounts)
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

    with open(f'thread_{thread_id}.json', 'w') as f:
        json.dump(thread, f)

    with open('guest_accounts.json', 'w') as f:
        json.dump(manager.get_accounts(), f)


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
