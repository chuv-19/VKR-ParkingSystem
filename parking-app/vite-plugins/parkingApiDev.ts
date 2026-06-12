import type { ChildProcess } from 'node:child_process'
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Plugin } from 'vite'

/**
 * В dev поднимает parking-api рядом с parking-app (../parking-api),
 * чтобы один `npm run dev` (vite) и прокси /api работали без второго терминала.
 */
export function parkingApiDevPlugin(): Plugin {
  let proc: ChildProcess | null = null

  return {
    name: 'parking-api-dev',
    apply: 'serve',
    configureServer(server) {
      const pluginDir = path.dirname(fileURLToPath(import.meta.url))
      const appDir = path.resolve(pluginDir, '..')
      const apiCwd = path.resolve(appDir, '..', 'parking-api')
      const entry = path.join(apiCwd, 'src', 'index.js')

      if (!fs.existsSync(entry)) {
        console.warn(
          `[parking-api-dev] не найден ${entry}. Запустите API вручную: cd parking-api && npm run dev`,
        )
        return
      }

      console.log('[parking-api-dev] старт API:', apiCwd)
      proc = spawn(process.execPath, ['--watch', 'src/index.js'], {
        cwd: apiCwd,
        stdio: 'inherit',
        env: { ...process.env },
      })

      proc.on('error', err => {
        console.error('[parking-api-dev]', err)
      })

      const stop = () => {
        if (proc && !proc.killed) {
          proc.kill('SIGTERM')
          proc = null
        }
      }

      server.httpServer?.once('close', stop)
      process.once('exit', stop)
    },
  }
}
