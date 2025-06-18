import sys
import json


def _find_thread_continuation(parent, candidates):
    """
    From a list of same-author replies, find the one that continues the thread.
    
    Twitter often marks thread continuations with a `self_thread` object.
    We prefer to use that if it's available. If not, we fall back to the
    first candidate in the list, which is pre-sorted by likes.
    """
    self_thread_id = parent['legacy'].get('self_thread', {}).get('id_str')
    if self_thread_id:
        for r in candidates:
            if self_thread_id == r['legacy'].get('self_thread', {}).get('id_str'):
                return r
    return candidates[0]


def partition_replies_deep(tweets, curr, _thread=None, _replies=None):
    """
    Recursively partitions replies to a tweet.

    It identifies a single chain of same-author replies to form a multi-part
    tweet (`_thread`). All other replies (from other authors, or forks from
    the same author) are collected into `_replies` to be processed as
    separate sub-threads.
    """
    is_first_call = _thread is None
    _thread = [] if is_first_call else _thread
    _replies = [] if is_first_call else _replies

    curr_id = curr['rest_id']
    direct_replies = [t for t in tweets if t['legacy'].get('in_reply_to_status_id_str') == curr_id]

    # Separate replies into those from the same author and those from others.
    same_author_replies = []
    other_author_replies = []
    for r in direct_replies:
        if r['legacy']['user_id_str'] == curr['legacy']['user_id_str']:
            same_author_replies.append(r)
        else:
            other_author_replies.append(r)

    # Process replies from other authors.
    for r in other_author_replies:
        # If this is a reply to a tweet deep in a chain (not the head),
        # we "quote" the tweet it replied to, as per the logic.
        reply_to_add = r
        if not is_first_call: # head quotes are implicit
            reply_to_add = {**r, '_quoted': curr}
        _replies.append(reply_to_add)

    # Process replies from the same author to find the thread continuation.
    if same_author_replies:
        continuation = _find_thread_continuation(curr, same_author_replies)
        _thread.append(continuation)

        # Any other same-author replies are "forks" and are treated as
        # regular replies to be processed into their own threads.
        for r in same_author_replies:
            if r is not continuation:
                _replies.append(r)
        
        # Recurse to continue building the same-author chain.
        partition_replies_deep(tweets, continuation, _thread, _replies)

    return _thread, _replies


def process_replies(tweets, curr, depth=0, tree=None):
    if tree is None:
        tree = [] # flat tree (each item has depth value)

    # This is the root of a new (potentially multi-part) thread entry.
    parts = [curr]
    tree.append({**curr, '_parts': parts, '_depth': depth})

    # Find the parts of the same-author thread and all other replies.
    same_author_thread_parts, other_replies = partition_replies_deep(tweets, curr)
    parts.extend(same_author_thread_parts)

    # Each of the "other" replies becomes the root of a new sub-tree.
    for r in other_replies:
        process_replies(tweets, r, depth + 1, tree)

    return tree


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_path> <output_path>", file=sys.stderr)
        exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, 'r') as f:
        thread = json.load(f)
        tweets = thread['tweets']
        users = thread['users']
        thread_id = thread['thread_tweet_id']
    
    users_by_id = {u['rest_id']: u for u in users}
    main_tweet = [i for i in tweets if i['rest_id'] == thread_id][0]
    author_id = main_tweet['legacy']['user_id_str']
    
    # Sort tweets to help with tie-breaking. The key sorts by:
    # 1. Main thread author first.
    # 2. Favorite count descending.
    # 3. Tweet ID ascending (as a stable fallback).
    tweets.sort(key=lambda t: (
        -int(t['legacy']['user_id_str'] == author_id),
        -t['legacy']['favorite_count'],
        t['rest_id']))

    tree = process_replies(tweets, main_tweet)

    with open(output_path, 'w') as f:
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
