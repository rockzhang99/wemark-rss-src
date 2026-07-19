import os
p = '_probe.log'
if os.path.exists(p):
    c = open(p, encoding='utf-8', errors='ignore').read()
    # 只保留 MATCH 行和末尾
    lines = c.splitlines()
    match_lines = [l for l in lines if 'MATCH' in l]
    tail = lines[-30:]
    with open('_p.txt', 'w', encoding='utf-8') as f:
        f.write(f"=== MATCH lines ({len(match_lines)}) ===\n")
        f.write('\n'.join(match_lines[:50]))
        f.write(f"\n\n=== TAIL ===\n")
        f.write('\n'.join(tail))
else:
    with open('_p.txt', 'w', encoding='utf-8') as f:
        f.write('NO _probe.log FILE')
