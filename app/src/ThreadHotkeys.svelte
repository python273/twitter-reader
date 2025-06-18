<script>
import { onMount, onDestroy } from 'svelte'

export let data

function onKeyDown(event) {
  if (event.target.matches('input, textarea, video, [contenteditable]')) {
    return
  }

  if (event.key === 'j' || event.key === 'k') {
    event.preventDefault()

    const currentCommentEl = document.activeElement.closest('.comment')
    let currentIndex = -1
    if (currentCommentEl) {
      const commentId = currentCommentEl.id.replace('comment-', '')
      currentIndex = data.findIndex(c => c.id === commentId)
    }

    let nextIndex
    if (event.key === 'j') {
      nextIndex = currentIndex + 1
    } else if (event.key === 'k') {
      if (currentIndex <= 0) return
      nextIndex = currentIndex - 1
    }

    if (nextIndex >= 0 && nextIndex < data.length) {
      const nextComment = data[nextIndex]
      const nextEl = document.getElementById(`comment-${nextComment.id}`)
      if (nextEl) {
        nextEl.scrollIntoView({ block: 'start', behavior: 'auto' })
        nextEl.focus({ preventScroll: true, focusVisible: true })
      }
    }
  } else if (event.key === 'h') {
    event.preventDefault()
    const currentCommentEl = document.activeElement.closest('.comment')
    if (!currentCommentEl) return

    const commentId = currentCommentEl.id.replace('comment-', '')
    const comment = data.find(c => c.id === commentId)
    if (comment) {
      const url = `https://x.com/${comment.username}/status/${comment.id}`
      if (window._openTab) {  // userscript
        window._openTab(url)
      } else {
        window.open(url, '_blank', 'noopener,noreferrer')
      }
    }
  }
}

onMount(() => {
  document.addEventListener('keydown', onKeyDown)
})

onDestroy(() => {
  document.removeEventListener('keydown', onKeyDown)
})
</script>
