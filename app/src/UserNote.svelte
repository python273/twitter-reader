<script>
import { onMount } from 'svelte'
import { getUserData } from './db'

let { id } = $props()

let note = $state('')

async function updateNote() {
  note = (await getUserData(id))?.note || ''
}

onMount(updateNote)

window.addEventListener('c-update-user-note', (e) => {
  if (e.detail?.userId === id) note = e.detail.note || ''
}, false)
</script>

<span class="user-note">{note}</span>

<style>
.user-note {
  font-weight: 500;
}
</style>
