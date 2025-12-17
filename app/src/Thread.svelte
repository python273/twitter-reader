<script>
import { onMount } from 'svelte'
import { timeSince, getUsernameColor } from './utils'
import { createTweetTree } from './tweet-tree.js'
import Username from './Username.svelte'
import UserNote from './UserNote.svelte'
import Article from './Article.svelte'
import ThreadHotkeys from './ThreadHotkeys.svelte'
import ThreadNarrator from './ThreadNarrator.svelte'
import ColorScroll from './ColorScroll.svelte'

let currentlyReading = $state(null)
let narratorPlaying = $state(false)
let threadNarrator = $state()

function collapse(event, comment) {
  let index = data.findIndex(item => item.id === comment.id)
  let newValue = !comment.collapsed
  comment.collapsed = newValue
  data = data
  if (index === -1) return  // quoted

  let depth = comment.depth
  for (index++; index < data.length; index++) {
    let comment = data[index]
    if (comment.depth <= depth) { break }
    comment.collapsed = newValue
  }
  data = data
}

let { threadId } = $props()
let usersById = $state({})
let tweets = $state([])
let opTweetUserId = $state(0)
let data = $state([])
$effect(() => {
  window._data = data
  window._usersById = usersById
})

window.addEventListener('c-update-user-rating', (e) => {
  if (!(e.prevRating >= -10 && e.newRating < -10)) return
  const uid = e.userId
  usersById[uid].rating = e.newRating
  usersById = usersById

  for (let t of data) {
    if (t.user.id !== uid) continue
    t.collapsed = true
  }
  data = data
}, false)

const htmlEntities = {amp: '&', lt: '<', gt: '>', quot: '"', '#039': "'"}
const reHtmlEntities = new RegExp(`&(${Object.keys(htmlEntities).join('|')});`, 'g')
function unescapeHtmlEntities(str) {
  return str.replace(reHtmlEntities, (m, c) => htmlEntities[c])
}

function convertRichtextTagIndices(originalString, tags) {
  // UTF-16 code units -> Unicode code point
  // "😊".length  == 2
  // Array.from("😊").length == 1
  const out = []
  for (const tag of tags) {
    out.push({...tag, indices: [
      Array.from(originalString.substring(0, tag.from_index)).length,
      Array.from(originalString.substring(0, tag.to_index)).length
    ]})
  }
  return out
}

function parseTextEntities(origT) {
  // Parse tweet entities and split text to paragraphs
  const t = origT.legacy

  let text
  let entities
  let richtextTags
  let [displayA, displayB] = [0, 0]

  const noteTweet = origT?.note_tweet?.note_tweet_results?.result
  if (noteTweet) {
    text = Array.from(noteTweet['text'])
    entities = noteTweet['entity_set']
    ;[displayA, displayB] = [0, text.length]
    // Seems like `richtext_tags` uses string.slice indexing,
    // and entities Array.from(string).slice indexing
    richtextTags = convertRichtextTagIndices(
      noteTweet['text'],
      noteTweet?.richtext?.richtext_tags || []
    )
  } else {
    text = Array.from(t['full_text'])
    entities = t.entities
    ;[displayA, displayB] = t['display_text_range']
    richtextTags = []
  }

  const allEntities = [
    ...entities.user_mentions.map(i => ({...i, _type: 'user_mention'})),
    ...entities.urls.map(i => ({...i, _type: 'url'})),
    ...entities.hashtags.map(i => ({...i, _type: 'hashtag'})),
    ...richtextTags.map(i => ({...i, _type: 'rich'})),
    ...(noteTweet?.media?.inline_media || []).map(m => ({
      _type: 'media',
      media_id: m.media_id,
      indices: [m.index, m.index]
    })),
    // ...entities.symbols.map(i => ({...i, _type: 'symbol'})),
  ]

  // dummy entity to parse text after the last real entity
  allEntities.push({_type: 'end', indices: [displayB, displayB]})

  allEntities.sort((a, b) => a.indices[0] - b.indices[0])

  const paragraphs = []
  const usedMediaIds = []
  let lastIndex = 0
  let currentParagraph = []

  for (let entity of allEntities) {
    const [a, b] = entity.indices

    if (lastIndex < a) {
      const textParagraphs = text.slice(lastIndex, a).join('').split(/\n{2,}/g)

      for (let i = 0; i < textParagraphs.length; i++) {
        if (i > 0) {
          paragraphs.push(currentParagraph)
          currentParagraph = []
        }
        if (textParagraphs[i]) {
          currentParagraph.push({
            _type: 'text',
            text: unescapeHtmlEntities(textParagraphs[i]).split('\n')
          })
        }
      }
    }

    if (entity._type !== 'end') {
      const e = {
        _type: entity._type,
        indices: [a, b],
        text: text.slice(a, b).join(''),
      }
      if (e._type === 'user_mention') {
        e.username = entity.screen_name
      } else if (e._type === 'url') {
        e.url = entity.expanded_url
        e.urldecoded = decodeURI(entity.expanded_url)
      } else if (e._type === 'hashtag') {
        e.hashtag = entity.text
      } else if (e._type === 'rich') {
        e.richtext_types = entity.richtext_types
      } else if (e._type === 'media') {
        e.media = t.extended_entities.media.find(media => media.id_str === entity.media_id)
        usedMediaIds.push(entity.media_id)
      }

      currentParagraph.push(e)
    }

    lastIndex = b
  }

  paragraphs.push(currentParagraph)

  // remove parts out of visible range
  for (let i in paragraphs) {
    const p = paragraphs[i]
    paragraphs[i] = p.filter(part => {
      if (part._type === 'text') return true
      const [a, b] = part.indices
      return a >= displayA && b <= displayB
    })
  }

  return { paragraphs, usedMediaIds }
}

function parsePoll(card) {
  if (!card || !card.legacy || !/^poll\d+choice_text_only$/.test(card.legacy.name)) {
    return null
  }
  const bindingValues = {}
  for (const bv of card.legacy.binding_values) {
    bindingValues[bv.key] = bv.value
  }
  const choices = []
  let total = 0
  let maxChoices = 4
  const match = card.legacy.name.match(/poll(\d+)choice/)
  if (match) {
    maxChoices = parseInt(match[1], 10)
  }
  for (let i = 1; i <= maxChoices; i++) {
    const label = bindingValues[`choice${i}_label`]?.string_value
    if (label === undefined) break
    const count = parseInt(bindingValues[`choice${i}_count`]?.string_value || '0')
    choices.push({ label, count })
    total += count
  }
  if (choices.length === 0) return null
  choices.forEach(choice => {
    choice.percent = total > 0 ? Math.round(choice.count / total * 100) : 0
  })
  return {
    choices,
    total,
    endDatetime: bindingValues.end_datetime_utc?.string_value,
    durationMinutes: bindingValues.duration_minutes?.string_value,
    countsAreFinal: bindingValues.counts_are_final?.boolean_value,
    lastUpdated: bindingValues.last_updated_datetime_utc?.string_value,
  }
}

function parseCard(card) {
  if (!card || !card.legacy) return null
  if (!['player', 'summary', 'summary_large_image'].includes(card.legacy.name)) return null

  const bindingValues = {}
  for (const bv of card.legacy.binding_values) {
    bindingValues[bv.key] = bv.value
  }

  let image
  for (const key of ['player_image_x_large', 'player_image_large', 'player_image_original', 'player_image', 'player_image_small']) {
    const imgVal = bindingValues[key]?.image_value
    if (imgVal?.url) {
      image = imgVal.url
      break
    }
  }
  return {
    title: bindingValues.title?.string_value,
    description: bindingValues.description?.string_value,
    domain: bindingValues.domain?.string_value,
    url: bindingValues.card_url?.string_value || bindingValues.player_url?.string_value,
    image,
  }
}

const convertTweet = (origT, usersById) => {
  if (origT['__typename'] !== 'Tweet') {
    console.log(origT)
    //throw Error('not tweet?')
  }
  const t = origT.legacy
  const u = usersById[t.user_id_str] || {}
  const username = u.username
  const [byBgColor, byColor] = getUsernameColor(username)

  const [a, b] = t['display_text_range']
  // some unicode madness, String.substr works too, but deprecated?
  // String.slice and String.substring split unicode chars
  const visibleText = unescapeHtmlEntities(
    Array.from(t['full_text']).slice(a, b).join('')
  )
  const { paragraphs, usedMediaIds } = parseTextEntities(origT)
  const date = new Date(t.created_at)

  // TODO: convert format
  let media = t?.extended_entities?.media || []  // || t?.entities?.media
  media = media.filter(m => !usedMediaIds.includes(m.id_str))

  const collapsed = (
    u.rating < -10
    || username == 'threadreaderapp'
    || username == 'UnrollHelper'
    || username == 'readwise'
    || username == 'NotionAddon'
    || username == 'SaveToNotion'
    || username == 'sendvidbot'
    || username == 'memdotai'
    || username == 'pikaso_me'
    || visibleText.match(/@threadreaderapp/)
    || visibleText.match(/@readwise/)
    || visibleText.match(/@NotionAddon/)
    || visibleText.match(/@SaveToNotion/)
    || visibleText.match(/@sendvidbot/)
    || visibleText.match(/@memdotai/)
    || visibleText.match(/@pikaso_me/)
    || visibleText.match(/@grok/)
  )

  const obj = {
    // pad: [],
    depth: origT._depth,
    info: origT._info,

    _t: origT,
    id: t.id_str,

    user: u,
    username,
    byColor,
    byBgColor,

    favoriteCount: t.favorite_count,
    quoteCount: t.quote_count,
    retweetCount: t.retweet_count,
    replyCount: t.reply_count,

    formattedTime: date.toLocaleString("en-US"),
    timeAgo: timeSince(date),

    quotedId: t.quoted_status_id_str,

    collapsed,
    paragraphs,
    visibleRawText: visibleText,

    media,
    poll: parsePoll(origT.card),
    card: parseCard(origT.card),
    parts: [],
    quotedTweet: null,
    repliedTweet: origT._quoted ? convertTweet(origT._quoted, usersById) : null,

    article: origT.article ? origT.article.article_results.result : null,
  }

  if (origT._parts) {  // thread tweets group
    obj.parts = origT._parts.map(i => convertTweet(i, usersById))
  } else {
    obj.parts = [obj]
  }

  if (origT?.quoted_status_result?.result) {
    let quotedTweet = origT?.quoted_status_result?.result
    if (quotedTweet['__typename'] === 'TweetWithVisibilityResults') quotedTweet = quotedTweet.tweet
    if (quotedTweet['__typename'] === 'Tweet') {  // vs TweetTombstone
      obj.quotedTweet = convertTweet(quotedTweet, usersById)
    }
  }

  return obj
}

const convertUser = (u) => {
  return {
    id: u.rest_id,
    rating: parseInt(localStorage[`ur-${u.rest_id}`], 10),
    createdAt: new Date(u.legacy.created_at || u.core.created_at),
    username: u.legacy.screen_name || u.core.screen_name,
    name: u.legacy.name || u.core.name,
    avatarUrl: u.legacy?.profile_image_url_https || u.avatar?.image_url,

    description: u.legacy.description,
    location: u.legacy.location,

    followingCount: u.legacy.friends_count,
    followersCount: u.legacy.followers_count,
  }
}

const fetchData = async () => {
  const thread = await (await fetch(`/tree_${threadId}.json`)).json()

  usersById = {}
  const users = thread.users_by_id ? Object.values(thread.users_by_id) : thread.users
  for (let u of users) {
    usersById[u.rest_id] = convertUser(u)
  }

  let threadTree
  if (thread.tweets) {
    opTweetUserId = thread.tweets.find(i => i.rest_id === threadId).legacy.user_id_str
    threadTree = createTweetTree(thread.tweets, threadId)
    tweets = thread.tweets.map(t => convertTweet(t, usersById))
  } else {
    threadTree = thread.tree  // hmm, fallback for feed
    tweets = thread.tree.map(t => convertTweet(t, usersById))
  }
  threadTree = threadTree.map(t => convertTweet(t, usersById))

  window.document.title = `${threadTree[0].visibleRawText} | @${threadTree[0].username} | Twitter Reader`

  // This stack holds information about the ancestors of the current tweet.
  // It's indexed by the original depth (1-based), so we can think of
  // ancestorStack[d] as the info for the tweet at depth d in the current path.
  const ancestorStack = []

  for(const t of threadTree) {
    const originalDepth = t.depth
    ancestorStack.length = originalDepth
    t.pad = ancestorStack.slice(1).map(ancestor => ({
      byBgColor: ancestor.byBgColor,
      sameUser: ancestor.username === t.username,
    }))

    ancestorStack[originalDepth] = { byBgColor: t.byBgColor, username: t.username }

    // The rendered depth is 0-based (top-level tweets have no indent).
    t.depth = Math.max(0, originalDepth - 1)
  }

  data = threadTree
}

onMount(fetchData)
</script>

{#if data.length}
<div class="thread-page">
<ThreadNarrator bind:this={threadNarrator} {data} bind:currentlyReading bind:narratorPlaying />

<ColorScroll {data} />

<div class="thread-container">
<div class="comments">

<ThreadHotkeys {data}/>

{#snippet renderMedia(m)}
  {#if m.type === "photo"}
    <a href={m['media_url_https'] + '?name=large'}>
      <img
        class="attach"
        alt=''
        src={m['media_url_https'] + '?name=large'}
        width={m['original_info']['width']}
        height={m['original_info']['height']}
        loading="lazy"
      />
    </a>
  {:else if m.type === "video"}
    <!-- svelte-ignore a11y_media_has_caption -->
    <video
      class="attach"
      controls
      preload="none"
      width={m['original_info']['width']}
      height={m['original_info']['height']}
      poster={m['media_url_https']}
    >
      {#each [...m.video_info.variants].reverse() as v}
        <source src={v.url} type={v.content_type}>
      {/each}
    </video>
  {:else if m.type === "animated_gif"}
    <!-- svelte-ignore a11y_media_has_caption -->
    <video
      class="attach-gif"
      controls
      loop
      preload="metadata"
      width={m['original_info']['width']}
      height={m['original_info']['height']}
    >
      {#each [...m.video_info.variants].reverse() as v}
        <source src={v.url} type={v.content_type}>
      {/each}
    </video>
  {:else}
    <pre>{JSON.stringify(m)}</pre>
  {/if}
{/snippet}

{#snippet renderComment(c, quotedId)}
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div id="comment-{c.id}{quotedId ? `-quoted-${quotedId}` : ''}"
    class='comment'
    class:comment-top-level={c.depth === 0}
    class:comment-blocked={c.collapsed && c.user.rating < -10}
    class:comment-quoted={quotedId}
    tabindex={!quotedId ? 0 : undefined}
  >
    <div class="comment-header narrator-skip">
      <Username data={c.user} color={c.byColor} bgColor={c.byBgColor}/>
      {#if c.user.id === opTweetUserId}<div class="op">OP</div>{/if}
      <span class="date meta-gray" title={c.formattedTime}>{c.timeAgo}</span>

      <button class="btn-text" onclick={(e) => collapse(e, c)} title="collapse">
        {#if c.collapsed}[+]{:else}[-]{/if}
      </button>
      <button class="btn-text" onclick={() => threadNarrator.playComment(c.id)} title="text-to-speech">
        {#if currentlyReading === c.id && narratorPlaying}■&#xFE0E;{:else}▶&#xFE0E;{/if}
      </button>

      <div class="meta-gray"><UserNote id={c.user.id} /></div>

      <div class="ml-auto"></div>

      {#if c.info}<div class='narrator-skip meta-gray' style='line-height: 1;'>[{c.info}]</div>{/if}

      <div class="meta-gray user-select-none">
        {#if c.favoriteCount}♥{c.favoriteCount}{/if}
        {#if c.retweetCount} <span style="font-weight: 800;">↻</span>{c.retweetCount}{/if}
        {#if c.quoteCount} ❝{c.quoteCount}{/if}
        {#if c.replyCount} &#10149;&#xFE0E;{c.replyCount}{/if}
      </div>

      <a href={`https://x.com/${c.username}/status/${c.id}`} title="reply" class="user-select-none">
        &#10149;&#xFE0E;
      </a>
    </div>

    <div class="comment-content" class:d-none={c.collapsed} class:narrator-skip={c.collapsed}>
      {#each c.parts as p, pi (p.id)}
        {#if pi > 0}
          <div class="comment-header tweet-splitter narrator-skip">
            <div style="flex-grow: 1;"><hr></div>
            <span class="date meta-gray" title={p.formattedTime}>{p.timeAgo}</span>
            <div class="meta-gray">
              {#if p.favoriteCount}♥{p.favoriteCount}{/if}
              {#if p.retweetCount} <span style="font-weight: 800;">↻</span>{p.retweetCount}{/if}
              {#if p.quoteCount} ❝{p.quoteCount}{/if}
              {#if p.replyCount} &#10149;&#xFE0E;{p.replyCount}{/if}
            </div>
            <div>
              <a href={`https://x.com/${p.username}/status/${p.id}`} title="reply">
                &#10149;&#xFE0E;
              </a>
            </div>
          </div>
        {/if}

        {#if p.repliedTweet}
          <div class="quote narrator-skip">
            <p
              class="quote-single-line"
              title={p.repliedTweet.visibleRawText}
            >
              {p.repliedTweet.visibleRawText}
            </p>
          </div>
        {/if}

        {#each p.paragraphs as paragraph, paragraph_index}
          <p
            class="narrator-paragraph"
            class:quote={paragraph.type === 'quote'}
            class:p-last-line={paragraph_index == (p.paragraphs.length-1)}
          >
            {#each paragraph as part}
              {#if part._type === 'text'}
                {#each part.text as line, line_i}
                  {line}{#if line_i < (part.text.length-1)}<span style="display: none;" data-narrator-pause>&nbsp;.&nbsp;</span><br/>{/if}
                {/each}
              {:else if part._type === 'user_mention'}
                <a href={`https://x.com/${part.username}`}>{part.text}</a>
              {:else if part._type === 'url'}
                <a href={part.url}>{part.urldecoded}</a>
              {:else if part._type === 'hashtag'}
                <a href={`https://x.com/hashtag/${part.hashtag}`}>{part.text}</a>
              {:else if part._type === 'rich'}
                <span class={part.richtext_types.map(t => 'rich-' + t.toLowerCase()).join(' ')}>
                  {part.text}
                </span>
              {:else if part._type === 'media' && part.media}
                {@render renderMedia(part.media)}
              {/if}
            {/each}
          </p>
        {/each}

        {#if p.poll}
          <div class="poll">
            {#each p.poll.choices as choice, i}
              <div class="poll-choice">
                <div class="poll-choice-top">
                  <span class="poll-choice-label">{choice.label}</span>
                  <span class="poll-choice-count">{choice.count} ({choice.percent}%)</span>
                </div>
                <div class="poll-choice-bar-container">
                  <div class="poll-choice-bar" style="width: {choice.percent}%"></div>
                </div>
              </div>
            {/each}
            <div class="poll-total">Total votes: {p.poll.total}</div>
            {#if p.poll.endDatetime}
              <div class="poll-end">Poll ended at {new Date(p.poll.endDatetime).toLocaleString()}</div>
            {/if}
          </div>
        {/if}

        {#if p.card}
          <a class="card-preview narrator-skip" href={p.card.url}>
            <div class="card-content">
              {#if p.card.domain}
                <div class="card-domain">{p.card.domain}</div>
              {/if}
              {#if p.card.title}
                <div class="card-title">{p.card.title}</div>
              {/if}
              {#if p.card.description}
                <div class="card-description">{p.card.description}</div>
              {/if}
            </div>
            {#if p.card.image}
              <img class="card-image" src={p.card.image} alt="" loading="lazy" />
            {/if}
          </a>
        {/if}

        {#if p.quotedTweet}
          <div class="">
            {@render renderComment(p.quotedTweet, c.id)}
          </div>
        {/if}

        {#if p.media}
          <div>
            {#each p.media as m (m.id_str)}
              {@render renderMedia(m)}
            {/each}
          </div>
        {/if}
      {/each}

      {#if c.article}
        <Article article={c.article} {renderComment} {tweets} />
      {/if}
    </div>
  </div>
{/snippet}

{#each data as c, i}
  <div class='comment-with-pad'>
    {#if !c.collapsed}
      {#if c.user.avatarUrl}
        <img class="avatar" src={c.user.avatarUrl} loading="lazy" alt=""/>
      {:else}
        <div class="avatar"></div>
      {/if}
    {:else}
      <div style="margin-left: calc(1.8em + 6px)"></div>
    {/if}
    {#each {length: c.depth} as _, i}
      <div class='pad' style="background: {c.pad[i].byBgColor};">
        {#if c.pad[i].sameUser}
          <div
            class='pad-same-user'
            style="background-color: {c.byColor}; border-color: {c.byBgColor};"
          ></div>
        {/if}
      </div>
    {/each}
    {@render renderComment(c)}
  </div>
{/each}
</div>
<div style="height: 50vh;"></div>
</div>
</div>
{/if}

<style>
.thread-page {
  display: flex;
  flex-direction: column;
}

p {
  margin: 0.5em 0;

  line-height: 1.2;
  font-size: 1em;
}

p.p-last-line {
  margin: 0.5em 0 1px 0;
}

/* p {
  background: repeating-linear-gradient(
    #0000,
    #0000 1.2em,
    #0000000f 1.2em,
    #0000000f 2.4em
  );
} */

.btn-text {
  display: inline-block;
  border: 0;
  background: none;
  margin: 0;
  padding: 0;

  cursor: pointer;
}

.colors-bar {
  display: flex;
  height: 10px;
  justify-content: center;
  margin: 5px 0;
  contain: content;
}
.comments {
  display: flex;
  flex-direction: column;
}
.thread-container {
  display: flex;
  flex-direction: column;

  z-index: 200;

  margin-left: 0.3em;
  margin-right: 0.3em;
}

@media only screen and (min-width: 900px) {
  .thread-container {
    min-width: 800px;
    margin-left: auto;
    margin-right: auto;
    width: max-content;
  }

  .comments .comment-with-pad:first-child > .comment {
    width: 100%;
  }

  :global(html) {
    scrollbar-width: thin;
    scrollbar-color: #000 transparent !important;
  }
}

.avatar {
  width: 1.8em;
  height: 1.8em;
  border-radius: 50%;
  margin: 7px 6px 0 0;
  background-color: var(--meta-color);
}

.pad {
  margin-right: 3px;
  width: 5px;
  max-width: 5px;
  min-width: 5px;
}

.pad-same-user {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-top: 4.5px;
  border: 2px solid;
  left: -2px;
  position: relative;
}

.comment-with-pad {
  padding: 0 6px;
}
.comment-with-pad:first-child {
  padding-top: 6px;
}
.comment-with-pad:last-child {
  padding-bottom: 6px;
}

.comment {
  display: flex;
  flex-direction: column;

  border-radius: 6px;
  margin: 3px 0 3px 0;

  width: 100%;
  max-width: min(64ch, 100vw);
  background-color: var(--comment-bg-color);
  overflow-wrap: anywhere;

  box-shadow: 0px 1px 6px #00000047;

  /* overflow: hidden; */
}

.comment:focus, .comment:focus-visible {
  outline: 1px auto;
}

.comment-top-level {
  margin-top: 0.4em;
}

.comment-with-pad {
  display: flex;
  contain: content;
}

.comment-blocked {
  filter: opacity(30%)
}

.comment-quoted {
  margin: 0.5em 0 0 0;
  border: 1.5px solid var(--brand-color);
}

.comment-header * {
  text-decoration: none;
  white-space: nowrap;
}

.comment-header {
  margin: 0 5px 3px 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  font-size: 0.8125em;
}

.comment-header > * {
  display: block;
}

.comment-header > *:first-child {
  margin-left: 0;
}

.comment-header .ml-auto {
  margin-left: auto;
}

.meta-gray {
  font-size: 0.929em;
  color: var(--meta-color);
  font-weight: 300;
}

.op {
  font-size: 0.9em;
  font-weight: bolder;
}

.comment-content {
  display: flex;
  flex-direction: column;
  margin: 0 0.5em 0.3em 0.5em;
  overflow: auto hidden;
}

hr {
  border: none;
  border-top: 0.5px solid var(--meta-color);
}

.tweet-splitter {
  display: flex;
  margin: 0;
  font-size: 0.75em;
  opacity: 0.6;
  user-select: none;
}

.comment-content pre {
  white-space: pre-wrap;
  margin: 0;
  line-height: 1.2rem;
}

.comment-content a {
  overflow-wrap: break-word;
  word-wrap: break-word;
  word-break: break-all;
  word-break: break-word;
}

.comment-content > p:first-child {
  margin-top: 0;
}

.comment-content > p:last-child {
  margin-bottom: 0;
}

.quote {
  background-color: rgba(0, 0, 0, 0.07);
  border-left: 4px solid var(--text-color);
  /* padding: 0.3em 0 0.3em 0.5em; */
  padding: 0.0em 0 0.0em 0.5em;
  border-radius: 2px;
  min-height: 1em;
}

.quote-single-line {
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
  margin: 0;
}

.attach {
  max-width: 100%;
  width: 100%;
  object-fit: contain;
  max-height: 400px;
  height: auto;
  border: 1.5px solid var(--brand-color);
}

.attach-gif {
  max-width: 100%;
  max-height: 150px;
}

.rich-italic {
  font-style: italic;
}
.rich-bold {
  font-weight: bold;
}

.poll {
  margin: 1em 0;
  padding: 0.5em;
  border: 1px solid var(--meta-color);
  border-radius: 6px;
}
.poll-choice {
  margin-bottom: 0.3em;
}
.poll-choice-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.2em;
}
.poll-choice-bar-container {
  height: 8px;
  border: 1px solid var(--brand-color);
  border-radius: 4px;
  overflow: hidden;
}
.poll-choice-bar {
  height: 100%;
  background-color: var(--brand-color);
  border-radius: 4px;
  transition: width 0.3s ease;
}
.poll-choice-count {
  font-size: 0.9em;
  color: var(--meta-color);
}
.poll-total {
  margin-top: 0.5em;
  font-size: 0.9em;
  color: var(--meta-color);
}
.poll-end {
  margin-top: 0.3em;
  font-size: 0.8em;
  color: var(--meta-color);
  font-style: italic;
}

.card-preview {
  border: 1.5px solid var(--brand-color);
  border-radius: 6px;
  display: block;
}
.card-image {
  width: 100%;
  max-height: 200px;
  object-fit: contain;
}
.card-content {
  padding: 0.5em;
  display: flex;
  flex-direction: column;
  gap: 0.2em;
}
.card-domain {
  font-size: 0.8em;
  color: var(--meta-color);
}
.card-description {
  font-size: 0.8em;
  color: var(--meta-color);
}
</style>
