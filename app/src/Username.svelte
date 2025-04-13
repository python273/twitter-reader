<script>
import { timeSince, trySetLSValue } from "./utils"
import Portal from './Portal.svelte'

export let data
export let color
export let bgColor

const username = data.username

let ref = null

let popup = false
let popupStyle = {}

const userKey = `ur-${data.id}`
const userNoteKey = `ur-n-${data.id}`
let note = ''
let userRating = 9999
let ratingColor = ''

function updateNote() {
  note = localStorage[userNoteKey] || ''
}
updateNote()

window.addEventListener('storage', (e) => {
  if (e.key === userNoteKey) updateNote()
})
window.addEventListener('c-update-user-note', (e) => {
  if (e.key === userNoteKey) updateNote()
}, false)

function onNoteChange() {
  localStorage[userNoteKey] = note

  const event = new Event('c-update-user-note')
  event.key = userNoteKey
  window.dispatchEvent(event)
}

function onNoteKeydown(event) {
  if (event.key === "Enter" || event.key === "Escape") {
    event.preventDefault()
    event.target.blur()
  }
}

function updateDisplayedRating() {
  userRating = (parseInt(localStorage[userKey], 10) || 0)
  if (userRating === 0) {
    ratingColor = ''
  } else if (userRating < 0) {
    ratingColor = 'rgb(238, 0, 0)'
  } else {
    ratingColor = 'rgb(0, 206, 90)'
  }
}
updateDisplayedRating()

window.addEventListener('storage', (e) => {
  if (e.key === userKey) updateDisplayedRating()
})
window.addEventListener('c-update-user-rating', (e) => {
  if (e.key === userKey) updateDisplayedRating()
}, false)

const updateRating = (diff) => {
  const current = (parseInt(localStorage[userKey], 10) || 0)
  trySetLSValue(userKey, current + diff)

  const event = new Event('c-update-user-rating')
  event.key = userKey
  event.userId = data.id
  event.prevRating = current
  event.newRating = current + diff
  window.dispatchEvent(event)
}

const togglePopup = () => {
  if (!popup) {
    const pos = ref.getBoundingClientRect()
    const posTop = pos.top + pos.height + window.scrollY
    const posLeft = pos.left + window.scrollX

    popupStyle = `position: absolute; top: ${posTop}px; left: ${posLeft}px;`
  }
  popup = !popup
}
</script>

<div class="username-container" bind:this={ref}>
  <button
    on:click={togglePopup}
    class="username"
    style="color: {color}; background: {bgColor};"
  >
    {username}
  </button>

  <div class='rating'>
    <button on:click={() => updateRating(+1)}>+</button>
    <span style="color: {ratingColor}; font-weight: {ratingColor ? 'bold': ''}">
      {(userRating + '').padStart(3, '\xa0')}
    </span>
    <button on:click={() => updateRating(-1)}>-</button>
    &nbsp;
    <button style='font-size: 12px;' on:click={() => updateRating(-11)}>✕</button>
  </div>

  {#if popup}
  <Portal>
    <div class="userPopup" style={popupStyle}>
      <input
        class="note"
        placeholder="Add a note..."
        bind:value={note}
        on:change={onNoteChange}
        on:keydown={onNoteKeydown}
      />

      <div class="meta">
        <div>
          <a href="https://x.com/{username}">
            {data.name}
          </a>
          |
          {#if data.location}
            location: {data.location} |
          {/if}
          following: {data.followingCount} |
          followers: {data.followersCount} |
          <span title="{data.createdAt.toLocaleString("en-US")}">
            joined: {timeSince(data.createdAt)}
          </span>
        </div>
      </div>

      <div class="userAbout">{data.description}</div>
    </div>
  </Portal>
  {/if}
</div>

<style>
.username-container {
  position: relative;
}

.meta {
  color: var(--meta-color);
}

.meta {
  font-size: 0.9em;
  font-family: monospace;
}

.username {
  text-decoration: none;
  font-weight: 600;
  border-radius: 4px 0 4px 0;
  padding: 1px 4px 1px 4px;
  line-height: 1.1;

  user-select: text;
}

.userAbout {
  margin: 8px 0;
}

.userPopup {
  z-index: 1000;

  top: calc(1em + 8px);
  width: min(50ch, 100vw);
  box-shadow: rgba(0, 0, 0, 0.3) 0 10px 10px;

  position: absolute;

  background-color: var(--comment-bg-color);
  border: 1px solid var(--brand-color);

  border-radius: 8px;
  padding: 5px;
}

.note {
  display: block;
  width: 100%;
  margin-bottom: 1em;
}

.rating {
  color: var(--meta-color);
  display: inline-block;
  font-family: monospace;
  font-weight: 500;
}
</style>
