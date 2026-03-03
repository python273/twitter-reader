<script>
let { article = {}, renderComment, tweets = [] } = $props()

const styleMap = {
  'Bold': 'font-weight:bold;',
  'Italic': 'font-style:italic;',
  'Code': 'font-family:monospace;background-color:#f0f0f0;padding:0.1em 0.3em;border-radius:3px;'
}

function getSegmentStyleString(segment) {
  return segment.styles.map(s => styleMap[s]).filter(Boolean).join('')
}

const headerMap = {
  'header-one': 'h1', 'header-two': 'h2', 'header-three': 'h3',
  'header-four': 'h4', 'header-five': 'h5', 'header-six': 'h6'
}

function preprocessBlock(block, entityMapArray) {
  if (block.type === 'atomic') {
    const entityRange = block.entityRanges?.[0]
    const entity = entityRange
      ? (entityMapArray.find(e => e.key === String(entityRange.key)))?.value
      : null
    return [{ type: 'atomic', entity }]
  }
  const text = block.text || ""
  const entityRanges = (block.entityRanges ?? []).filter(r => {
    const entity = (entityMapArray.find(e => e.key === String(r.key)))?.value
    return entity?.type !== 'TWEMOJI'
  })
  const allRangesPoints = [
    ...(block.inlineStyleRanges ?? []).flatMap(r => [r.offset, r.offset + r.length]),
    ...entityRanges.flatMap(r => [r.offset, r.offset + r.length]),
    ...(block.data?.mentions ?? []).flatMap(m => [m.fromIndex, m.toIndex])
  ]
  const sortedUniquePoints = [...new Set([0, text.length, ...allRangesPoints])]
    .filter(p => p >= 0 && p <= text.length)
    .sort((a, b) => a - b)

  const segments = []
  for (let i = 0; i < sortedUniquePoints.length - 1; i++) {
    const start = sortedUniquePoints[i]
    const end = sortedUniquePoints[i + 1]
    if (start >= end) continue

    const segmentText = text.substring(start, end)
    const activeStyles = (block.inlineStyleRanges ?? [])
      .filter(r => r.offset <= start && (r.offset + r.length) >= end)
      .map(r => r.style)

    const activeEntityRange = entityRanges.find(r => r.offset <= start && (r.offset + r.length) >= end)
    const entity = activeEntityRange
      ? (entityMapArray.find(e => e.key === String(activeEntityRange.key)))?.value
      : null

    const currentMention = (block.data?.mentions ?? []).find(m => m.fromIndex === start && m.toIndex === end && segmentText.startsWith('@') && m.text === segmentText.substring(1))
    const mentionData = currentMention ? currentMention.text : null

    segments.push({ text: segmentText, styles: activeStyles, entity, mention: mentionData })
  }
  return segments
}

function getMediaData(mediaId) {
  const media = article.media_entities?.find(m => m.media_id === mediaId)
  const info = media?.media_info
  if (!info) return null

  if (info.__typename === 'ApiImage' && info.original_img_url) {
    return {
      type: 'image',
      src: info.original_img_url,
      width: info.original_img_width,
      height: info.original_img_height,
    }
  }

  const preview = info.preview_image
  const variants = info.variants || []
  const mp4 = variants.find(v => v.content_type === 'video/mp4') || variants[0]
  if (mp4?.url) {
    return {
      type: 'video',
      src: mp4.url,
      poster: preview?.original_img_url,
      width: preview?.original_img_width,
      height: preview?.original_img_height,
    }
  }

  if (preview?.original_img_url) {
    return {
      type: 'image',
      src: preview.original_img_url,
      width: preview.original_img_width,
      height: preview.original_img_height,
    }
  }

  return null
}

const processedArticleBlocks = $derived((article.content_state?.blocks || []).map(block => ({
  key: block.key,
  type: block.type,
  segments: preprocessBlock(block, article.content_state.entityMap),
})))

const groupedBlocks = $derived.by(() => {
  const result = []
  let currentList = null
  for (const block of processedArticleBlocks) {
    const isListItem = block.type === 'ordered-list-item' || block.type === 'unordered-list-item'
    if (isListItem) {
      const listType = block.type === 'ordered-list-item' ? 'ol' : 'ul'
      if (currentList && currentList.listType === listType) {
        currentList.items.push(block)
      } else {
        if (currentList) result.push(currentList)
        currentList = { type: 'list', listType, items: [block], key: block.key + '-listwrapper' }
      }
    } else {
      if (currentList) {
        result.push(currentList)
        currentList = null
      }
      result.push(block)
    }
  }
  if (currentList) result.push(currentList)
  return result
})
</script>

{#if article.cover_media}
  {#if article.cover_media.media_info.__typename == "ApiImage"}
    {@const m = article.cover_media.media_info}
    <div>
      <img
        class="cover"
        alt=''
        src={m.original_img_url}
        width={m.original_img_width}
        height={m.original_img_height}
        loading="lazy"
      />
    </div>
  {:else}
    <div style="color: red;">unknown cover media</div>
  {/if}
{/if}
<h1>{article.title}</h1>

{#snippet renderSegmentList(segments, key)}
  {#each segments as segment, i (key + i)}
    {#if segment.mention}
      <a href="https://x.com/{segment.mention}" style={getSegmentStyleString(segment)} rel="noopener noreferrer">
        {segment.text}
      </a>
    {:else if segment.entity && segment.entity.type === 'LINK'}
      <a href={segment.entity.data.url} style={getSegmentStyleString(segment)} rel="noopener noreferrer">
        {segment.text}
      </a>
    {:else}
      <span style={'white-space-collapse: preserve;' + getSegmentStyleString(segment)}>
        {segment.text}
      </span>
    {/if}
  {/each}
{/snippet}

<div>
{#each groupedBlocks as group (group.key)}
  {#if group.type === 'list'}
    <svelte:element this={group.listType}>
      {#each group.items as block (block.key)}
        <li>{@render renderSegmentList(block.segments, block.key)}</li>
      {/each}
    </svelte:element>
  {:else if group.type === 'atomic'}
    {#if group.segments[0] && group.segments[0].entity}
      {@const entity = group.segments[0].entity}
      {#if entity.type === 'MARKDOWN'}
        <pre><code>{entity.data.markdown}</code></pre>
      {:else if entity.type === 'MEDIA' && entity.data.mediaItems && entity.data.mediaItems[0]}
        {@const mediaItem = entity.data.mediaItems[0]}
        {@const media = getMediaData(mediaItem.mediaId)}
        {#if media}
          <div>
            {#if media.type === 'image'}
              <img class="article-media" src={media.src} width={media.width} height={media.height} alt={entity.data.caption || ''} />
            {:else}
              <video class="article-media" src={media.src} poster={media.poster} width={media.width} height={media.height} muted autoplay loop playsinline preload="metadata"></video>
            {/if}
            {#if entity.data.caption}<p style="color: var(--meta-color); margin-top: 0;"><small>{entity.data.caption}</small></p>{/if}
          </div>
        {/if}
      {:else if entity.type === 'DIVIDER'}
        <hr/>
      {:else if entity.type === 'TWEET'}
        {@const tweet = tweets.find(t => t.id === entity.data.tweetId)}
        {#if tweet}
          {@const renderKey = entity.data.entityKey ?? entity.data.tweetId ?? group.key}
          {@render renderComment(tweet, `article-entity-${renderKey}`)}
        {:else}
          <div style="color: red;">Tweet not found: {entity.data.tweetId}</div>
        {/if}
      {:else}
        <div style="color: red;">unknown entity {entity.type}</div>
        <code><pre>{JSON.stringify(group, null, 2)}</pre></code>
      {/if}
    {/if}
  {:else if group.type === 'unstyled'}
    <p>{@render renderSegmentList(group.segments, group.key)}</p>
  {:else if group.type === 'blockquote'}
    <blockquote>{@render renderSegmentList(group.segments, group.key)}</blockquote>
  {:else if group.type && group.type.startsWith('header-')}
    <svelte:element this={headerMap[group.type] || 'div'}>
      {@render renderSegmentList(group.segments, group.key)}
    </svelte:element>
  {:else}
    <div style="color: red;">unknown group type</div>
  {/if}
{/each}
</div>

<style>
.cover {
  max-width: 100%;
  width: 100%;
  object-fit: contain;
  max-height: 400px;
  height: auto;
  border: 1.5px solid var(--brand-color);
}
div > *:first-child {
  margin-block-start: 0;
}
div > *:last-child {  
  margin-block-end: 0;
}
p, dl {
  display: block;
  margin-block-start: 1.188em;
  margin-block-end: 1.188em;
}
:not(pre) > code {
  white-space: pre-wrap;
  border-radius: 3px;
  background-color: var(--code-bg-color);
}
blockquote {
  margin: 0;
  background-color: rgba(0, 0, 0, 0.07);
  border-left: 4px solid var(--text-color);
  padding: 0.0em 0 0.0em 0.5em;
  border-radius: 2px;
}
pre {
  white-space: pre-wrap;
  border-radius: 3px;
  background-color: var(--code-bg-color);
  font-size: 0.95em;
  line-height: 1.15;
  padding: 1px;
}
pre, code {
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
}
ol, ul {
  padding-left: 1.5em;
}
li {
  word-break: break-word;
}
img {
  max-width: 100%;
}
video {
  max-width: 100%;
}
.article-media {
  max-width: 100%;
  height: auto;
}
h1, h2, h3, h4, h5, h6 {
  border-left: 3px solid var(--text-color);
  padding-left: 0.5em;
  font-weight: 500;
  margin: 0.5em 0;
}
</style>
