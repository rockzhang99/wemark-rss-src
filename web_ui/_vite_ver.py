import json, os
base = r'd:\4Project\wemark-rss-src\web_ui'
v = json.load(open(os.path.join(base, 'node_modules/vite/package.json')))
with open(os.path.join(base, '_vite_ver.txt'), 'w') as f:
    f.write('vite: ' + v.get('version', '?') + '\n')
