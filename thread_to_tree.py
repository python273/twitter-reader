import sys
from datetime import datetime
import html
import json


def process_replies(tweets, curr, depth=0, tree=None, author_id=None):
    if tree is None:
        tree = [] # flat tree (each item has depth value)

    tree.append({**curr, '_depth': depth})
    curr_id = curr['id_str']

    new_depth = depth + 1

    replies = []
    for tweet in tweets:
        if tweet.get('in_reply_to_status_id_str') == curr_id:
            replies.append(tweet)

    def _sort(t):
        # sort author first, TODO: other people in the branch, then by id
        return (-int(t['user_id_str'] == author_id), t['id_str'])
    replies.sort(key=_sort)

    for r in replies:
        process_replies(tweets, r, new_depth, tree, author_id)

    return tree

def split_string_by_words(s, max_line_len):
    lines = []
    line = []
    line_len = 0
    for word in s.split(' '):
        if line_len + len(word) > max_line_len:
            lines.append(' '.join(line))
            line = []
            line_len = 0
        line.append(word)
        line_len += len(word)
    lines.append(' '.join(line))
    return lines


RED = '\033[91m'
YELLOW = '\033[33m'
RESET = '\033[0m'


def main():
    thread_id = sys.argv[1]

    with open(f'thread_{thread_id}.json', 'r') as f:
        thread = json.load(f)
        tweets = thread['tweets']
        users = thread['users']
    
    users_by_id = {u['rest_id']: u for u in users}

    main_tweet = [i for i in tweets if i['id_str'] == thread_id][0]

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

    LINE_LEN = 60

    print()

    for i in tree:
        pad = '-*' * i['_depth']
        pad_clear = ' |' * i['_depth']

        user = users_by_id[i['user_id_str']]
        user_login = user['legacy']['screen_name']
        user_name = user['legacy']['name'].strip()
        created_at = datetime.strptime(
            user['legacy']['created_at'],
            '%a %b %d %H:%M:%S %z %Y'
        )
        created_at_str = created_at.strftime('%Y %b %d')

        a, b = i['display_text_range']
        text = i['full_text'][a:b].strip()

        entities_urls = i['entities']['urls']
        # replace t.co links with their expanded version
        for e in entities_urls:
            if e['expanded_url']:
                text = text.replace(e['url'], e['expanded_url'])
        
        media = (
            i.get('extended_entities', {}).get('media', [])
            or i.get('entities', {}).get('media', [])
        )
        for e in media:
            if e["type"] == "photo":
                text += f'\nAttch {e["type"]}:\n{e["media_url_https"]}'
            # elif e["type"] == "video":
            else:
                max_bitrate_variant = max(
                    e["video_info"]["variants"],
                    key=lambda x: x.get("bitrate", -1)
                )
                text += f'\nAttch {e["type"]}:\n{max_bitrate_variant["url"]}'

        text = html.unescape(text)

        lines = text.strip().split('\n')
        new_lines = []
        for line in lines:
            if len(line) > LINE_LEN:
                parts = split_string_by_words(line, LINE_LEN)
                new_lines.extend(parts)
            else:
                new_lines.append(line)
        lines = new_lines

        lines = [
            (
                ''
                + pad_clear
                + ' '
                + l
            )
            for x, l in enumerate(lines)
        ]
        text = '\n'.join(lines)

        print(''.join([
            pad, RED, ' ', user_name, f' (@{user_login})', ' ', created_at_str, RESET, '\n',
            text, '\n',
            pad_clear
        ]))


if __name__ == '__main__':
    main()
