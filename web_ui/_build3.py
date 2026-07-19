import subprocess, os

base = r'd:\4Project\wemark-rss-src\web_ui'
os.chdir(base)

npm = r'd:\4Project\wemark-rss-src\web_ui\node_modules\.bin\npm.cmd'
if not os.path.exists(npm):
    npm = 'npm.cmd'

# 运行构建，捕获所有输出
proc = subprocess.Popen(
    [npm, 'run', 'build'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

lines = []
for line in proc.stdout:
    lines.append(line.rstrip('\n'))

rc = proc.wait()

# 分析
match_lines = [l for l in lines if 'MATCH' in l]
vendor_lines = [l for l in lines if 'vendor-libs' in l or 'layout-vendor' in l]

out = []
out.append(f"exit: {rc}")
out.append(f"total output lines: {len(lines)}")
out.append(f"MATCH lines: {len(match_lines)}")
out.append('\n'.join(match_lines[:10]))
out.append(f"\nvendor-libs mentioned: {len(vendor_lines)}")

# 检查生成的 chunk
if os.path.exists('dist/assets'):
    js = os.listdir('dist/assets')
    out.append(f"\ndist JS count: {len([x for x in js if x.endswith('.js')])}")
    out.append(f"layout-vendor: {[x for x in js if 'layout-vendor' in x]}")
    out.append(f"vendor-libs: {[x for x in js if 'vendor-libs' in x]}")

with open('_b3.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
