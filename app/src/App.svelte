<script>
import Thread from './Thread.svelte'
import { themeStore } from './themeStore.js'

let page = $state('thread')
let props = $state({ threadId: undefined })

const parseHash = () => {
  const h = location.hash.slice(1)
  let threadId = h

  if (threadId.match(/^[0-9]+$/)) {
    page = 'thread'
    props = {threadId}
  }
}

parseHash()
window.addEventListener("hashchange", () => {
  parseHash()
}, false)
</script>

{#if !$themeStore.isDark}
<style>
  :root {
    --bg-color: #ecedee;
    --text-color: #000;
    --comment-bg-color: #fff;
    --panel-bg-color: #f7f7f7;
    --meta-color: rgb(94, 126, 142);
    --code-bg-color: #eceef0;
  }

  html {
    scrollbar-color: #000 transparent;
  }
</style>
{:else}
<style>
  :root {
    --bg-color: rgb(24, 20, 18);
    --text-color: rgb(233, 225, 204);
    --comment-bg-color: rgb(55, 45, 40);
    --panel-bg-color: #241e1b;
    --meta-color: rgb(179, 172, 152);
    --code-bg-color: rgb(70, 56, 50);
  }

  html {
    scrollbar-color: #fff transparent;
  }
</style>
{/if}

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
    <Thread {...props}/>
  {/key}
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
