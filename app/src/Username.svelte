<script>
import { onMount } from 'svelte'
import { timeSince } from "./utils"
import Portal from './Portal.svelte'
import { getUserData, updateUserNote as updateUserNoteDb, updateUserRating as updateUserRatingDb } from './db'

let { data, color, bgColor } = $props()

const username = data.username

let ref = $state(null)

let popup = $state(false)
let popupStyle = $state('')

let note = $state('')
let userRating = $state(0)
const ratingColor = $derived(userRating === 0 ? '' : userRating < 0 ? 'rgb(238, 0, 0)' : 'rgb(0, 206, 90)')

async function loadUser() {
  const user = await getUserData(data.id)
  note = user?.note || ''
  userRating = user?.rating || 0
}

onMount(loadUser)

window.addEventListener('c-update-user-note', (e) => {
  if (e.detail?.userId !== data.id) return
  note = e.detail.note || ''
}, false)

async function onNoteChange() {
  await updateUserNoteDb(data.id, note)
}

function onNoteKeydown(event) {
  if (event.key === "Enter" || event.key === "Escape") {
    event.preventDefault()
    event.target.blur()
  }
}

window.addEventListener('c-update-user-rating', (e) => {
  if (e.detail?.userId !== data.id) return
  userRating = e.detail.rating || 0
}, false)

const updateRating = async (diff) => {
  const user = await updateUserRatingDb(data.id, diff)
  userRating = user?.rating || 0
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
    onclick={togglePopup}
    class="username"
    style="color: {color}; background: {bgColor};"
  >
    {username}
  </button>

  <div class='rating'>
    <button onclick={() => updateRating(+1)}>+</button>
    <span style="color: {ratingColor}; font-weight: {ratingColor ? 'bold': ''}">
      {(userRating + '').padStart(3, '\xa0')}
    </span>
    <button onclick={() => updateRating(-1)}>-</button>
    &nbsp;
    <button style='font-size: 12px;' onclick={() => updateRating(-11)}>✕</button>
  </div>

  {#if popup}
  <Portal>
    <div class="userPopup" style={popupStyle}>
      <input
        class="note"
        placeholder="Add a note..."
        bind:value={note}
        onchange={onNoteChange}
        onkeydown={onNoteKeydown}
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
  border-radius: 6px 0 6px 0;
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
  user-select: none;
}
</style>
