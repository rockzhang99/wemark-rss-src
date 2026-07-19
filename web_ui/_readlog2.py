import os
base = r'd:\4Project\wemark-rss-src\web_ui'
p = os.path.join(base, '_probe.log')
out = os.path.join(base, '_p.txt')
if os.path.exists(p):
    c = open(p, encoding='utf-8', errors='ignore').read()
    lines = c.splitlines()
    match_lines = [l for l in lines if 'MATCH' in l]
    tail = lines[-20:]
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f"=== MATCH lines ({len(match_lines)}) ===\n")
        f.write('\n'.join(match_lines[:50]))
        f.write(f"\n\n=== TAIL ===\n")
        f.write('\n'.join(tail))
else:
    with open(out, 'w', encoding='utf-8') as f:
        f.write('NO _probe.log FILE')
