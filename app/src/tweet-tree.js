function tweetComparator(authorId) {
  return (a, b) => {
    const aIsAuthor = Number(a.legacy.user_id_str === authorId)
    const bIsAuthor = Number(b.legacy.user_id_str === authorId)
    if (aIsAuthor !== bIsAuthor) return bIsAuthor - aIsAuthor

    const af = a.legacy.favorite_count | 0
    const bf = b.legacy.favorite_count | 0
    if (bf !== af) return bf - af

    return a.rest_id.localeCompare(b.rest_id)
  }
}

function _findThreadContinuation(parent, candidates) {
  const selfThreadId = parent.legacy.self_thread?.id_str
  if (selfThreadId) {
    for (const r of candidates) {
      if (selfThreadId === r.legacy.self_thread?.id_str) {
        return r
      }
    }
  }
  return candidates[0]
}

function partitionRepliesDeep(tweets, curr, _thread = null, _replies = null) {
  const is_first_call = _thread === null
  _thread = is_first_call ? [] : _thread
  _replies = is_first_call ? [] : _replies

  const currId = curr.rest_id
  const directReplies = tweets.filter(t => t.legacy.in_reply_to_status_id_str === currId)

  const sameAuthorReplies = []
  const otherAuthorReplies = []
  for (const r of directReplies) {
    if (r.legacy.user_id_str === curr.legacy.user_id_str) {
      sameAuthorReplies.push(r)
    } else {
      otherAuthorReplies.push(r)
    }
  }

  for (const r of otherAuthorReplies) {
    let replyToAdd = r
    if (!is_first_call) {
      replyToAdd = { ...r, _quoted: curr }
    }
    _replies.push(replyToAdd)
  }

  if (sameAuthorReplies.length > 0) {
    const continuation = _findThreadContinuation(curr, sameAuthorReplies)
    _thread.push(continuation)

    for (const r of sameAuthorReplies) {
      if (r !== continuation) {
        _replies.push(r)
      }
    }

    partitionRepliesDeep(tweets, continuation, _thread, _replies)
  }

  return [_thread, _replies]
}

function processReplies(tweets, curr, authorId, depth = 0, tree = null) {
  if (tree === null) {
    tree = []
  }

  const parts = [curr]
  tree.push({ ...curr, _parts: parts, _depth: depth })

  const [sameAuthorThreadParts, otherReplies] = partitionRepliesDeep(tweets, curr)
  parts.push(...sameAuthorThreadParts)

  otherReplies.sort(tweetComparator(authorId))

  for (const r of otherReplies) {
    processReplies(tweets, r, authorId, depth + 1, tree)
  }

  return tree
}

export function createTweetTree(tweets, threadTweetId) {
  const mainTweet = tweets.find(t => t.rest_id === threadTweetId)
  if (!mainTweet) {
    throw new Error(`Main tweet with id ${threadTweetId} not found`)
  }

  const authorId = mainTweet.legacy.user_id_str

  tweets.sort(tweetComparator(authorId))

  return processReplies(tweets, mainTweet, authorId)
}