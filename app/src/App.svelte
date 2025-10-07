<script>
import Theme from './Theme.svelte'
import Thread from './Thread.svelte'
import Settings from './Settings.svelte'
import { themeStore } from './themeStore.js'

let page = $state('thread')
let props = $state({})

const parseHash = () => {
  const h = location.hash.slice(1)
  
  if (h === 'settings') {
    page = 'settings'
    props = {}
  } else if (h.match(/^[0-9]+$/)) {
    page = 'thread'
    props = {threadId: h}
  } else {
    page = 'thread'
    props = {threadId: undefined}
  }
}

parseHash()
window.addEventListener("hashchange", () => {
  parseHash()
}, false)
</script>

<Theme/>

<div class="header">
  <!-- svelte-ignore a11y_invalid_attribute -->
  <div class="home"><a href="#" class="no-vs">Twitter Reader</a></div>

  <div class='ml-auto'></div>
  <div class="settings">
    <a
      class="settings-link no-vs"
      href="#settings"
      title="settings"
    >settings</a>
    <button onclick={themeStore.toggle}>
      {#if $themeStore.theme === 'system'}
        light/dark
      {:else}
        {$themeStore.theme}
      {/if}
    </button>
  </div>
</div>

<div class="page">
{#if page === "thread"}
  {#key props.threadId}
    <Thread threadId={props.threadId}/>
  {/key}
{/if}
{#if page === "settings"}
  <Settings/>
{/if}
</div>

<style>
:global(html, body) {
  background-color: var(--bg-color);
  color: var(--text-color);
}
.home {
  font-size: 1.4em;
  font-family: monospace;
}
.header {
  width: 100%;
  height: 32px;
  padding: 0 16px;
  display: flex;
  align-items: center;
}
.page {
  width: 100%;
  overflow-x: hidden;
}
@media only screen and (min-width: 900px) {
  .settings {
    position: fixed;
    right: 16px;
  }
}
</style>
