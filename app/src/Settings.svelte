<script>
import { notifyThemeChange } from './utils.js'

$effect(() => {
  document.title = `Settings | Twitter Reader`
})

let lightTheme = $state(localStorage.getItem('cfg-theme-light') || 'light')
let darkTheme = $state(localStorage.getItem('cfg-theme-dark') || 'dark')

$effect(() => {
  localStorage.setItem('cfg-theme-light', lightTheme)
  notifyThemeChange()
})

$effect(() => {
  localStorage.setItem('cfg-theme-dark', darkTheme)
  notifyThemeChange()
})
</script>

<main>
  <div><h1>Settings</h1></div>
  <div>
    <h2>Theme</h2>
    <div>
      <label for="light-theme">Light Mode Theme:</label>
      <select id="light-theme" bind:value={lightTheme}>
        <option value="light">Light</option>
        <option value="lavender">Lavender</option>
      </select>
    </div>
    <div>
      <label for="dark-theme">Dark Mode Theme:</label>
      <select id="dark-theme" bind:value={darkTheme}>
        <option value="dark">Dark</option>
        <option value="smolder">Smolder</option>
      </select>
    </div>
  </div>
  <hr/>
  <div>
    <a href="https://github.com/python273/twitter-reader">https://github.com/python273/twitter-reader</a>
  </div>
</main>

<style>
main {
  display: flex;
  justify-content: center;
  flex-direction: column;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}
h1 {
  margin-bottom: 1em;
}
hr {
  width: 100%;
}
</style>
