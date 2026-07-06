import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { cpSync, mkdirSync, readdirSync, statSync } from 'node:fs'
import { basename, dirname, join } from 'node:path'

function copyPublicNoTree() {
  const srcDir = 'public'

  return {
    name: 'copy-public-no-tree',
    apply: 'build',
    writeBundle(options) {
      if (!options.dir) return

      function walk(src, dest) {
        const stat = statSync(src)
        if (stat.isDirectory()) {
          for (const name of readdirSync(src)) {
            walk(join(src, name), join(dest, name))
          }
        } else if (!basename(src).startsWith('tree_')) {
          mkdirSync(dirname(dest), { recursive: true })
          cpSync(src, dest)
        }
      }

      walk(srcDir, options.dir)
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  build: {
    copyPublicDir: false
  },
  plugins: [svelte(), copyPublicNoTree()]
})
