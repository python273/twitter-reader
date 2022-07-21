import sys
import json
from pprint import pprint


def partition_replies_deep(tweets, curr, _same=None, _others=None):
    is_first_level = _same is None

    if _same is None:
        _same = []
    if _others is None:
        _others = []

    curr_id = curr['id_str']

    replies = [
        t for t in tweets
        if t.get('in_reply_to_status_id_str') == curr_id
    ]

    replies_same_author = []

    for r in replies:
        if r['user_id_str'] == curr['user_id_str']:
            replies_same_author.append(r)
        else:
            if is_first_level:
                _others.append(r)
            else:
                _others.append({**r, '_quoted': curr})

    if replies_same_author:
        q = None

        self_thread = curr.get('self_thread', {}).get('id_str')
        if self_thread:
            for i in replies_same_author:
                if self_thread == i.get('self_thread', {}).get('id_str'):
                    q = i
                    break

        if not q:
            q = replies_same_author[0]

        _same.append(q)
        _others.extend(i for i in replies_same_author if i['id_str'] != q['id_str'])

    # _same.extend(replies_same_author)
    
    for i in replies_same_author:
        partition_replies_deep(tweets, i, _same, _others)

    return _same, _others


def process_replies(tweets, curr, depth=0, tree=None, author_id=None):
    if tree is None:
        tree = [] # flat tree (each item has depth value)

    parts = [curr]
    tree.append({**curr, '_parts': parts, '_depth': depth})

    replies_same_author, replies_others = partition_replies_deep(tweets, curr)
    parts.extend(replies_same_author)

    for r in replies_others:
        process_replies(tweets, r, depth + 1, tree, author_id)

    return tree


def main():
    thread_id = sys.argv[1]

    with open(f'thread_{thread_id}.json', 'r') as f:
        thread = json.load(f)
        tweets = thread['tweets']
        users = thread['users']
    
    users_by_id = {u['rest_id']: u for u in users}
    main_tweet = [i for i in tweets if i['id_str'] == thread_id][0]
    tweets.sort(key=lambda t: t['id_str'])

    tree = process_replies(tweets, main_tweet, author_id=main_tweet['user_id_str'])

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
