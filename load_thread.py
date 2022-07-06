import collections
import time
import json
import traceback
import requests
import sys


USERAGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0"


def ensure(fn):
    t = 3

    while True:
        try:
            return fn()
        except Exception as e:
            traceback.print_exc()
            time.sleep(t)
            t = min(10, t * 2)


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


def get_guest_id(session):
    headers = {
        'User-Agent': USERAGENT,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://twitter.com/',
        'authorization': AUTH_BEARER,
    }

    return session.post(
        f'https://api.twitter.com/1.1/guest/activate.json',
        headers=headers,
    ).json()['guest_token']


def load_tweet(session, tweet_id, cursor):
    headers = {
        'User-Agent': USERAGENT,
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

    return session.get(
        'https://twitter.com/i/api/graphql/u3N3Hp5UJq5QMCR2yDwzaw/TweetDetail',
        params=params,
        headers=headers
    ).json()


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


def load_tree(session, thread_id):
    total_count = 0

    to_fetch = [[thread_id, None]]
    already_fetched = set()  # (tweet_id, cursor)
    loaded_tweets = {}  # id -> tweet
    loaded_users = {}  # id -> user

    expected_replies_count = collections.Counter()  # tweet id -> count
    got_replies_count = collections.Counter()

    while True:
        while to_fetch:
            tweet_id, cursor = to_fetch.pop()
            total_count += 1

            print(f'Fetching {tweet_id} {bool(cursor)} ({len(to_fetch)} / {total_count})')
            print(cursor)

            while True:
                ok = False
                for _ in range(3):
                    try:
                        response = load_tweet(session, tweet_id, cursor)
                    except:
                        traceback.print_exc()
                        time.sleep(3)
                        continue

                    ok = True
                    break
                
                if ok:
                    break

                time.sleep(10)
                session.headers.pop('x-guest-token')
                session.headers['x-guest-token'] = get_guest_id(session)

            already_fetched.add((tweet_id, cursor))

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
                    # TODO: check if needed
                    continue

                print(c)
                print()

                f = (tweet_id, c['value'])
                if f not in already_fetched:
                    to_fetch.append(f)

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
                    to_fetch.append(f)
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


def main():
    thread_id = sys.argv[1]

    s = requests.Session()
    s.headers['x-guest-token'] = get_guest_id(s)

    thread = load_tree(s, thread_id)

    with open(f'thread_{thread_id}.json', 'w') as f:
        json.dump(thread, f)


if __name__ == '__main__':
    main()
