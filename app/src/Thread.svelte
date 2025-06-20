<script>
import { onDestroy, onMount, tick } from 'svelte'
import { rgbToCss, hashString, timeSince, HSVtoRGB } from './utils'
import { Narrator } from './narrator'
import Username from './Username.svelte'
import UserNote from './UserNote.svelte'
import Article from './Article.svelte'
import ThreadHotkeys from './ThreadHotkeys.svelte'


function getUsernameColor(username) {
  if (!username) return ["#000", "#fff"]
  const i = hashString(username)
  // eslint-disable-next-line no-unused-vars
  const [x, y, z] = [
    ((i >> 16) & 0xFFFF) / (0xFFFF + 0.1),
    ((i >> 8) & 0xFF) / 255.0,
    (i & 0xFF) / 256.0
  ]
  let [r, g, b] = HSVtoRGB(x, y * 0.7 + 0.3, 1.0,).map(i => i * 255.0)
  const byBgColor = rgbToCss(r, g, b)
  const byColor = ((r * 0.299 + g * 0.587 + b * 0.114) > 186) ? '#000' : '#fff'
  return [byBgColor, byColor]
}

let colorScroll = []
let totalScrollHeight = 0
async function updateColorScroll(data) {
  if (!data || data.length === 0) return
  await tick()

  const out = []

  // the first el is offset to the first comment
  const el = document.getElementById(`comment-${data[0].id}`)
  out.push({color: '', height: el.parentElement.offsetTop})

  for (let c of data) {
    const el = document.getElementById(`comment-${c.id}`)
    if (!el) {
      console.error(`Comment ${c.id} not found`)
      continue
    };
    const elHeight = el.parentElement.offsetHeight
    out.push({color: c.byBgColor, height: elHeight})
  }

  colorScroll = out
  totalScrollHeight = document.documentElement.scrollHeight
}
$: { updateColorScroll(data) }

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

let currentlyReading = null
let narrator = null
let narratorPlaying = false

onDestroy(() => {
  if (narrator) narrator.stop()
})

async function handlePlayComment(commentId=null) {
  // null - reuse current narrator (global controls)
  // same id as reading - pause/continue
  // new id - stop current, start new
  console.log('handlePlayComment', commentId, currentlyReading)
  if (narrator?.speaking) {
    narrator.stop()
    narratorPlaying = false
    if (commentId === null || currentlyReading === commentId) return
  }

  let currentNarrator
  if (commentId === null) {
    currentNarrator = narrator
  } else {
    const el = document.querySelector(`#comment-${commentId} .comment-content`)
    currentNarrator = new Narrator(
      window,
      el,
      new Promise((resolve) => {resolve("en-US")})
    )
    narrator = currentNarrator
    currentlyReading = commentId
  }
  const narratorRate = parseFloat(localStorage["cfg-narrator-rate"] || 1.2)
  narratorPlaying = true
  await currentNarrator.start({rate: narratorRate})
  if (narrator !== currentNarrator) return

  narratorPlaying = false

  if (!currentNarrator._stopped) {  // if stopped by itself, go to the next comment
    console.log('next comment')
    const currentCommentIndex = data.findIndex(c => c.id === currentlyReading)
    if (currentCommentIndex < data.length - 1) {
      handlePlayComment(data[currentCommentIndex + 1].id)
    }
  }
}


function handleNarratorPrev(e) {
  narrator.skipPrevious()
}

function handleNarratorNext(e) {
  narrator.skipNext()
}

// ###################################################################################

export let threadId
let usersById = {}
let opTweet = {}
let data = []
$: {
  window._data = data
  window._usersById = usersById
}

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
    // ...entities.symbols.map(i => ({...i, _type: 'symbol'})),
  ]

  // dummy entity to parse text after the last real entity
  allEntities.push({_type: 'end', indices: [displayB, displayB]})

  allEntities.sort((a, b) => a.indices[0] - b.indices[0])

  const paragraphs = []
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

  return paragraphs
}


const convertScrapedTo = (origT, usersById) => {
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
  const text = parseTextEntities(origT)
  const date = new Date(t.created_at)

  // TODO: convert format
  const media = t?.extended_entities?.media || t?.entities?.media

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

    _t: origT,
    id: t.id_str,

    user: u,
    username,
    byColor,
    byBgColor,

    isOP: t.user_id_str === opTweet.legacy.user_id_str,

    favoriteCount: t.favorite_count,
    quoteCount: t.quote_count,
    retweetCount: t.retweet_count,
    replyCount: t.reply_count,

    formattedTime: date.toLocaleString("en-US"),
    timeAgo: timeSince(date),

    quotedId: t.quoted_status_id_str,

    collapsed,
    text,
    visibleRawText: visibleText,

    media,
    parts: [],
    quotedTweet: null,
    repliedTweet: null,
  }

  if (origT.article) {
    obj.article = origT.article.article_results.result
  }

  if (origT._parts) {  // thread tweets group
    obj.parts = origT._parts.map(i => convertScrapedTo(i, usersById))
  } else {
    obj.parts = []
  }

  if (origT?.quoted_status_result?.result) {
    let quotedTweet = origT?.quoted_status_result?.result
    if (quotedTweet['__typename'] === 'TweetWithVisibilityResults') quotedTweet = quotedTweet.tweet
    quotedTweet._parts = [{...quotedTweet}]
    obj.quotedTweet = convertScrapedTo(quotedTweet, usersById)
    obj.quotedTweet._isQuoted = obj.id
  }

  if (origT._quoted) {  // as in replied to
    obj.repliedTweet = convertScrapedTo(origT._quoted, usersById)
  }

  return obj
}

const fetchData = async () => {
  const thread = await (await fetch(`/tree_${threadId}.json`)).json()
  opTweet = thread['tree'][0]

  usersById = {}
  for (let u of Object.values(thread['users_by_id'])) {
    usersById[u.rest_id] = {
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

  const tempTree = thread['tree'].map(t => convertScrapedTo(t, usersById))
  window.document.title = `${tempTree[0].visibleRawText} | Twitter Reader`

  let tweetStack = []
  let prevDepth = 0

  for(let t of tempTree) {
    t.pad = []
    for(let i = 1; i < t.depth; i++) {
      t.pad.push({
        byBgColor: tweetStack[i].byBgColor,
        sameUser: tweetStack[i].username === t.username,
      })
    }

    if (t.depth == prevDepth) {
      tweetStack[t.depth] = t  // replace if at the same level
    } else if (t.depth > prevDepth) {
      tweetStack.push(t)  // push if deeper
    } else if (t.depth < prevDepth) {
      tweetStack.length = t.depth  // truncate to depth
      tweetStack.push(t) // push
    }

    prevDepth = t.depth

    t.depth = Math.max(0, t.depth - 1)  // remove main tweet's pad
  }

  data = tempTree
}

onMount(fetchData)
</script>

{#if data.length}
<div class="thread-page">
  {#if narrator}
    <div class="global-narrator-controls">
      <button class="btn-text" on:click={() => handlePlayComment()} title="play/pause">
        {#if narratorPlaying}⏸︎&#xFE0E;{:else}▶&#xFE0E;{/if}
      </button>
      <button class="btn-text" on:click={handleNarratorPrev} title="previous">⭠</button>
      <button class="btn-text" on:click={handleNarratorNext} title="next">⭢</button>
    </div>
  {/if}

  <div class="colors-scroll">
    {#each colorScroll as c, i}
      <div style="background: {c.color}; height: {c.height / totalScrollHeight * 100}%; width: 100%;"></div>
    {/each}
  </div>

<div class="thread-container">
<div class="comments">

<ThreadHotkeys {data}/>

{#snippet renderComment(c)}
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div id="comment-{c.id}{c._isQuoted ? `-quoted-${c._isQuoted}` : ''}"
    class='comment'
    class:comment-top-level={c.depth === 0}
    class:comment-blocked={c.collapsed && c.user.rating < -10}
    class:comment-quoted={c._isQuoted}
    tabindex={!c._isQuoted ? 0 : undefined}
  >
    <div class="comment-header narrator-skip">
      <Username data={c.user} color={c.byColor} bgColor={c.byBgColor}/>
      {#if c.isOP}<div class="op">OP</div>{/if}
      <span class="date meta-gray" title={c.formattedTime}>{c.timeAgo}</span>

      <button class="btn-text" on:click={(e) => collapse(e, c)} title="collapse">
        {#if c.collapsed}[+]{:else}[-]{/if}
      </button>
      <button class="btn-text" on:click={() => handlePlayComment(c.id)} title="text-to-speech">
        {#if currentlyReading === c.id}■&#xFE0E;{:else}▶&#xFE0E;{/if}
      </button>

      <div class="meta-gray"><UserNote id={c.user.id} /></div>

      <div class="ml-auto"></div>

      <div class="meta-gray">
        {#if c.favoriteCount}♥{c.favoriteCount}{/if}
        {#if c.retweetCount} <span style="font-weight: 800;">↻</span>{c.retweetCount}{/if}
        {#if c.quoteCount} ❝{c.quoteCount}{/if}
        {#if c.replyCount} &#10149;&#xFE0E;{c.replyCount}{/if}
      </div>

      <a href={`https://x.com/${c.username}/status/${c.id}`} title="reply">
        &#10149;&#xFE0E;
      </a>
    </div>

    <div class="comment-content" class:d-none={c.collapsed} class:narrator-skip={c.collapsed}>
      {#if c.article}
        <Article article={c.article} />
      {/if}
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

        {#each p.text as paragraph, paragraph_index}
          <p
            class="narrator-paragraph"
            class:quote={paragraph.type === 'quote'}
            class:p-last-line={paragraph_index == (p.text.length-1)}
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
              {/if}
            {/each}
          </p>
        {/each}

        {#if p.quotedTweet}
          <div class="">
            {@render renderComment(p.quotedTweet)}
          </div>
        {/if}

        {#if p.media}
        <div>
          {#each p.media as m, mi (m.id_str)}
            {#if m.type === "photo"}
              <a href={m['media_url_https']}>
                <img
                  class="attach"
                  alt=''
                  src={m['media_url_https']}
                  width={m['original_info']['width']}
                  height={m['original_info']['height']}
                  loading="lazy"
                />
              </a>
            {:else if m.type === "video"}
              <!-- svelte-ignore a11y-media-has-caption -->
              <video
                class="attach"
                controls
                preload="metadata"
                width={m['original_info']['width']}
                height={m['original_info']['height']}
              >
                {#each m.video_info.variants.reverse() as v}
                  <source src={v.url} type={v.content_type}>
                {/each}
              </video>
            {:else if m.type === "animated_gif"}
              <!-- svelte-ignore a11y-media-has-caption -->
              <video
                class="attach-gif"
                controls
                loop
                preload="metadata"
                width={m['original_info']['width']}
                height={m['original_info']['height']}
              >
                {#each m.video_info.variants.reverse() as v}
                  <source src={v.url} type={v.content_type}>
                {/each}
              </video>
            {:else}
              <pre>{JSON.stringify(m)}</pre>
            {/if}
          {/each}
        </div>
        {/if}
      {/each}
    </div>
  </div>
{/snippet}

{#each data as c, i}
  <div class='comment-with-pad'>
    {#if c.user.avatarUrl}
      <img class="avatar" src={c.user.avatarUrl} loading="lazy" alt=""/>
    {:else}
      <div class="avatar"></div>
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
@media only screen and (max-width: 899px) {
  .colors-scroll {
    display: none !important;
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
  margin: 0 0 4px 0;

  width: 100%;
  max-width: min(62ch, 100vw);
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
  border: 2px solid var(--brand-color);
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
  margin: 0 5px 5px 5px;
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
  border: 2px solid var(--brand-color);
}

.attach-gif {
  max-width: 100%;
  max-height: 150px;
}
.colors-scroll {
  z-index: 100;

  position: fixed;
  top: 0;
  right: 0;

  width: 8px;
  height: 100%;

  display: flex;
  flex-direction: column;
  contain: strict;
}
.rich-italic {
  font-style: italic;
}
.rich-bold {
  font-weight: bold;
}
.global-narrator-controls {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: fixed;
  top: 50vh;
  right: 2rem;
  background: #fff;
  padding: 0.5rem;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 100;
}
</style>
