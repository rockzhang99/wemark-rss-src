import subprocess, os, sys

base = r'd:\4Project\wemark-rss-src\web_ui'
os.chdir(base)

print(f"cwd: {os.getcwd()}")
npm = r'd:\4Project\wemark-rss-src\web_ui\node_modules\.bin\npm.cmd'
if not os.path.exists(npm):
    npm = 'npm.cmd'

print(f"using npm: {npm}")
rc = subprocess.run([npm, 'run', 'build'], capture_output=True, text=True, timeout=600)
print(f"exit: {rc.returncode}")

# 检查 layout-vendor
vendor = [f for f in os.listdir('dist/assets') if 'layout-vendor' in f]
with open('_b2.txt', 'w', encoding='utf-8') as f:
    f.write(f"exit: {rc.returncode}\n")
    f.write(f"layout-vendor: {vendor}\n")
    # 捕获 MATCH 日志
    match_lines = [l for l in rc.stdout.splitlines() if 'MATCH' in l]
    f.write(f"MATCH lines: {len(match_lines)}\n")
    f.write('\n'.join(match_lines[:20]))
    f.write(f"\n\nSTDOUT TAIL:\n")
    f.write('\n'.join(rc.stdout.splitlines()[-15:]))
    f.write(f"\n\nSTDERR TAIL:\n")
    f.write('\n'.join(rc.stderr.splitlines()[-15:]))
print("done")
