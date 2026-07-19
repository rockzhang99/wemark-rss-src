import subprocess, os, sys

os.chdir(r'd:\4Project\wemark-rss-src\web_ui')
log = open('_full_build.log', 'w', encoding='utf-8')

print('Starting build...', file=log, flush=True)
proc = subprocess.Popen(
    ['npm', 'run', 'build'],
    stdout=log,
    stderr=subprocess.STDOUT,
)
rc = proc.wait()
print(f'Build exit code: {rc}', file=log, flush=True)
log.close()

# 检查 layout-vendor 是否生成
vendor = [f for f in os.listdir('dist/assets') if 'layout-vendor' in f]
with open('_build_result.txt', 'w', encoding='utf-8') as f:
    f.write(f'exit: {rc}\n')
    f.write(f'layout-vendor in dist: {vendor}\n')
    f.write(f'dist JS count: {len([x for x in os.listdir("dist/assets") if x.endswith(".js")])}\n')
