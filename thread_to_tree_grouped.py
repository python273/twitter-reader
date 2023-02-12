import sys
import json
from pprint import pprint


def partition_replies_deep(tweets, curr, _thread=None, _replies=None):
    is_first_level = _thread is None

    if _thread is None:
        _thread = []
    if _replies is None:
        _replies = []

    curr_id = curr['rest_id']

    replies = [
        t for t in tweets
        if t['legacy'].get('in_reply_to_status_id_str') == curr_id
    ]

    replies_same_author = []

    for r in replies:
        if r['legacy']['user_id_str'] == curr['legacy']['user_id_str']:
            replies_same_author.append(r)
        else:
            if is_first_level:
                _replies.append(r)
            else:
                _replies.append({**r, '_quoted': curr})

    if replies_same_author:
        q = None

        self_thread = curr['legacy'].get('self_thread', {}).get('id_str')
        if self_thread:
            for i in replies_same_author:
                if self_thread == i['legacy'].get('self_thread', {}).get('id_str'):
                    q = i
                    break

        if not q:
            q = replies_same_author[0]

        _thread.append(q)
        for i in replies_same_author:
            if i['rest_id'] == q['rest_id']:
                continue  # skip thread
            
            if not any(1 for t in _replies if t['rest_id'] == i['rest_id']):
                _replies.append(i)

    for i in replies_same_author:
        partition_replies_deep(tweets, i, _thread, _replies)

    return _thread, _replies


def process_replies(tweets, curr, depth=0, tree=None):
    if tree is None:
        tree = [] # flat tree (each item has depth value)

    parts = [curr]
    tree.append({**curr, '_parts': parts, '_depth': depth})

    replies_same_author, replies_others = partition_replies_deep(tweets, curr)
    parts.extend(replies_same_author)

    for r in replies_others:
        process_replies(tweets, r, depth + 1, tree)

    return tree


def main():
    thread_id = sys.argv[1]

    with open(f'thread_{thread_id}.json', 'r') as f:
        thread = json.load(f)
        tweets = thread['tweets']
        users = thread['users']
    
    users_by_id = {u['rest_id']: u for u in users}
    main_tweet = [i for i in tweets if i['rest_id'] == thread_id][0]
    tweets.sort(key=lambda t: (-t['legacy']['favorite_count'], t['rest_id']))

    tree = process_replies(tweets, main_tweet)

    with open(f'tree_{thread_id}.json', 'w') as f:
        json.dump(
            {
                'tweets': tweets,
                'users_by_id': users_by_id,
                'tree': tree,
            },
            f,
            ensure_ascii=False
        )


if __name__ == '__main__':
    main()
