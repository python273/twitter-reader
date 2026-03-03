

export function createScriptManager() {
  const STORAGE_KEY = 'twitter-thread-scripts'

  let scripts = $state([])

  function loadScripts() {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        scripts = JSON.parse(stored)
      } catch (e) {
        console.error('Failed to parse stored scripts', e)
      }
    }
  }

  function saveScripts() {
    console.log('saveScripts', scripts)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(scripts))
  }

  loadScripts()

  function createScriptInstance(code) {
    try {
      const returnedClass = new Function(code)()
      return new returnedClass()
    } catch (e) {
      console.error('Script compilation error:', e)
      return null
    }
  }

  async function applyPostprocessThread(thread) {
    let currentThread = thread
    for (const script of scripts) {
      if (!script.enabled) continue
      const instance = createScriptInstance(script.code)
      if (instance && typeof instance.postprocessThread === 'function') {
        try {
          const result = await instance.postprocessThread({ thread: currentThread })
          if (result && result.thread) {
            currentThread = result.thread
          }
        } catch (e) {
          console.error(`Script "${script.name}" error:`, e)
        }
      }
    }
    return currentThread
  }

  function updateScript(id, updates) {
    const existingIndex = scripts.findIndex(s => s.id === id)
    if (existingIndex >= 0) {
      // Update existing script
      scripts = scripts.map(s => s.id === id ? { ...s, ...updates } : s)
    } else {
      // Add new script with this id (or generate id if undefined)
      const newId = id || Math.random().toString(36).substring(2)
      scripts.push({ id: newId, enabled: true, ...updates })
    }
    saveScripts()
  }

  function deleteScript(id) {
    scripts = scripts.filter(s => s.id !== id)
    saveScripts()
  }

  function moveScript(id, direction) {
    const index = scripts.findIndex(s => s.id === id)
    if (index === -1) return
    const newIndex = index + direction
    if (newIndex < 0 || newIndex >= scripts.length) return
    const newScripts = [...scripts]
    const [removed] = newScripts.splice(index, 1)
    newScripts.splice(newIndex, 0, removed)
    scripts = newScripts
    saveScripts()
  }

  return {
    get scripts() { return scripts },
    updateScript,
    deleteScript,
    moveScript,
    applyPostprocessThread,
  }
}
