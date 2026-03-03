<script>
let { scriptManager } = $props()

const DEFAULT_SCRIPT_CODE = `class TwitterThreadScript {
  async postprocessThread({ thread }) {
    
    return { thread }
  }
}

return TwitterThreadScript;`

let showDropdown = $state(false)
let editingScript = $state(null)
let newScriptName = $state('')
let newScriptCode = $state('')

function toggleScript(id) {
  const script = scriptManager.scripts.find(s => s.id === id)
  if (script) {
    scriptManager.updateScript(id, { enabled: !script.enabled })
  }
}

function startEdit(script) {
  editingScript = script
  newScriptName = script.name
  newScriptCode = script.code
}

function cancelEdit() {
  editingScript = null
  newScriptName = ''
  newScriptCode = ''
}

function saveEdit() {
  const id = editingScript?.id || Math.random().toString(36).substring(2)
  scriptManager.updateScript(id, { name: newScriptName, code: newScriptCode })
  cancelEdit()
}

function deleteScript(id) {
  if (confirm('Delete script?')) {
    scriptManager.deleteScript(id)
  }
}

function startNewScript() {
  editingScript = {}
  newScriptName = ''
  newScriptCode = DEFAULT_SCRIPT_CODE
}
</script>

<div class="scripts-wrapper">
  <button class="scripts-toggle" onclick={() => showDropdown = !showDropdown}>
    Scripts
  </button>

  {#if showDropdown}
    <div class="scripts-dropdown">
      <div class="scripts-header">
        Scripts:
        <button onclick={startNewScript}>create</button>
      </div>

      {#if editingScript !== null}
        <div class="script-edit">
          <input type="text" placeholder="Script name" bind:value={newScriptName} />
          <div class="script-edit-actions">
            <button onclick={saveEdit}>save</button>
            <button onclick={cancelEdit}>cancel</button>
          </div>
          <textarea
            bind:value={newScriptCode} rows="8"
            spellcheck="false"
            autocorrect="off"
            autocapitalize="off"
            autocomplete="off"
          ></textarea>
        </div>
      {:else}
        <div class="scripts-list">
          {#each scriptManager.scripts as script (script.id)}
            <div class="script-item">
              <label class="script-enable">
                <input type="checkbox" checked={script.enabled} onchange={() => toggleScript(script.id)} />
                <span class="script-name">{script.name}</span>
              </label>
              <div class="script-actions">
                <button onclick={() => startEdit(script)}>edit</button>
                <button onclick={() => deleteScript(script.id)} title="delete">x</button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
.scripts-wrapper {
  position: fixed;
  top: 2.5em;
  right: 1em;
  z-index: 1000;
}

.scripts-toggle {
  background: var(--panel-bg-color);
  border: 1px solid var(--meta-color);
  color: var(--brand-color);
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.scripts-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--panel-bg-color);
  border: 1px solid var(--meta-color);
  border-radius: 6px;
  padding: 0.5em;
  min-width: 40ch;
  max-width: 40ch;
  height: 85vh;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);

  display: flex;
  flex-direction: column;
}

.scripts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.script-item {
  display: flex;
}

.script-enable {
  cursor: pointer;
  flex: 1;
  margin-right: 8px;
}

.script-actions {
  display: flex;
  gap: 8px;
}

.script-edit {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.script-edit textarea {
  flex: 1;
  font-family: monospace;
  font-size: 0.9em;
  resize: none; 
}

.script-edit-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
