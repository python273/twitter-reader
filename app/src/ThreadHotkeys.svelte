<script>
import { onMount, onDestroy } from 'svelte'

export let data

function isPressed(e, combo) {
  const parts = combo.toLowerCase().split('+')
  const key = parts.pop()
  
  let code
  switch (key) {
  case '?': code = 'Slash'; break
  case 'esc':
  case 'escape': code = 'Escape'; break
  case 'enter': code = 'Enter'; break
  default: code = key.length === 1 ? `Key${key.toUpperCase()}` : key
  }
  
  const wants = {
    shift: parts.includes('shift'),
    ctrl: parts.includes('ctrl'),
    alt: parts.includes('alt'),
    meta: parts.includes('meta'),
  }
  
  return e.code === code &&
    e.shiftKey === wants.shift &&
    e.ctrlKey === wants.ctrl &&
    e.altKey === wants.alt &&
    e.metaKey === wants.meta
}

function focusComment(index) {
  if (index >= 0 && index < data.length) {
    const comment = data[index]
    const el = document.getElementById(`comment-${comment.id}`)
    if (el) {
      el.scrollIntoView({ block: 'start', behavior: 'auto' })
      el.focus({ preventScroll: true, focusVisible: true })
    }
  }
}

function onKeyDown(e) {
  if (e.target.matches('input, textarea, video, [contenteditable]')) {
    return
  }
  const hot = (combo) => isPressed(e, combo)

  if (hot('j') || hot('k')) {
    e.preventDefault()

    const currentCommentEl = document.activeElement.closest('.comment')
    let currentIndex = -1
    if (currentCommentEl) {
      const commentId = currentCommentEl.id.replace('comment-', '')
      currentIndex = data.findIndex(c => c.id === commentId)
    }

    let nextIndex
    if (hot('j')) {
      nextIndex = currentIndex + 1
    } else if (hot('k')) {
      if (currentIndex <= 0) return
      nextIndex = currentIndex - 1
    }

    focusComment(nextIndex)
  } else if (hot('h')) {
    e.preventDefault()
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
  } else if (hot('n')) {
    e.preventDefault()
    const currentCommentEl = document.activeElement.closest('.comment')
    if (!currentCommentEl) return

    const commentId = currentCommentEl.id.replace('comment-', '')
    const currentIndex = data.findIndex(c => c.id === commentId)
    if (currentIndex === -1) return

    const currentComment = data[currentIndex]
    const currentDepth = currentComment.depth

    let nextIndex = -1
    for (let i = currentIndex + 1; i < data.length; i++) {
      if (data[i].depth <= currentDepth) {
        nextIndex = i
        break
      }
    }

    if (nextIndex !== -1) {
      focusComment(nextIndex)
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
