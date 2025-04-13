<script>
export let id

const userNoteKey = `ur-n-${id}`
let note = ''

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
</script>

<span class="user-note">{note}</span>

<style>
.user-note {
  font-weight: 500;
}
</style>
