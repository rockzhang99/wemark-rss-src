// 构建后自动同步 web_ui/dist -> static/
// 确保后端（web.py 从 static/ 提供前端）拿到最新构建产物
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const distDir = path.resolve(__dirname, 'dist')
const staticDir = path.resolve(__dirname, '../static')

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true })
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name)
    const d = path.join(dest, entry.name)
    if (entry.isDirectory()) {
      copyDir(s, d)
    } else {
      fs.copyFileSync(s, d)
    }
  }
}

// 清空 static/assets（移除旧的构建产物，避免孤儿文件）
const staticAssets = path.join(staticDir, 'assets')
if (fs.existsSync(staticAssets)) {
  fs.rmSync(staticAssets, { recursive: true, force: true })
}

copyDir(distDir, staticDir)
console.log('已同步 web_ui/dist -> static/')
