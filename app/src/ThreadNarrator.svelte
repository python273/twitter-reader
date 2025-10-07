<script>
import { onDestroy } from 'svelte'
import { Narrator } from './narrator'

let { data = [], currentlyReading = $bindable(null), narratorPlaying = $bindable(false) } = $props()

let narrator = $state(null)

onDestroy(() => {
  if (narrator) narrator.stop()
})

export async function playComment(commentId=null) {
  // null - reuse current narrator (global controls)
  // same id as reading - pause/continue
  // new id - stop current, start new
  console.log('playComment', commentId, currentlyReading)
  if (narrator?.speaking) {
    narrator.stop()
    narratorPlaying = false
    if (commentId === null || currentlyReading === commentId) return
  }

  let currentNarrator
  if (commentId === null) {
    if (!narrator) return
    currentNarrator = narrator
  } else {
    const el = document.querySelector(`#comment-${commentId} .comment-content`)
    if (!el) return

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
    if (currentCommentIndex > -1 && currentCommentIndex < data.length - 1) {
      let nextCommentIndex = currentCommentIndex + 1
      while(nextCommentIndex < data.length && data[nextCommentIndex].collapsed) {
        nextCommentIndex++
      }
      if (nextCommentIndex < data.length) {
        playComment(data[nextCommentIndex].id)
      } else {
        currentlyReading = null
      }
    } else {
      currentlyReading = null
    }
  }
}

export function skipPrevious() {
  narrator?.skipPrevious()
}

export function skipNext() {
  narrator?.skipNext()
}
</script>

{#if narrator}
  <div class="global-narrator-controls">
    <button class="btn-text" onclick={() => playComment()} title="play/pause">
      {#if narratorPlaying}⏸︎&#xFE0E;{:else}▶&#xFE0E;{/if}
    </button>
    <button class="btn-text" onclick={skipPrevious} title="previous">⭠</button>
    <button class="btn-text" onclick={skipNext} title="next">⭢</button>
  </div>
{/if}

<style>
.btn-text {
  display: inline-block;
  border: 0;
  background: none;
  margin: 0;
  padding: 0;

  cursor: pointer;
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
