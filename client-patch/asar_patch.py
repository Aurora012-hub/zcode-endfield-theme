"""ZCode 终末地皮肤补丁器 v3 — 幂等·外科手术式(针对 D:\\zcode)

可对原版或已打补丁的 app.asar 直接再手术(升级皮肤无需先恢复):
- 原版清单 JSON 字节原样保留,仅替换两个文件节点的值对象子串
- pickle 框架按原版格式:strlen=未填充长度,payload=4+strlen+零填充,headerSize=4+payload
- 数据区整体流式复制(未修改文件相对偏移自动保持),修改文件追加到末尾
- 校验:全量 sha256 + 头部语义对比(除两个目标节点外必须完全一致)
"""
import hashlib
import json
import os
import re
import struct
import sys
import time

RES = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else r'D:\zcode\resources'
ASAR = os.path.join(RES, 'app.asar')
OUT = os.path.join(RES, 'app.asar.endfield')
HERE = os.path.dirname(os.path.abspath(__file__))
SKIN = os.path.join(HERE, 'endfield_client_skin')
CHUNK = 16 * 1024 * 1024
u32 = lambda b, o: struct.unpack_from('<I', b, o)[0]


def make_integrity(data):
    return {
        'algorithm': 'SHA256',
        'hash': hashlib.sha256(data).hexdigest(),
        'blockSize': 4194304,
        'blocks': [hashlib.sha256(data[i:i + 4194304]).hexdigest()
                   for i in range(0, len(data), 4194304)],
    }


def locate_node(js: bytes, key: bytes):
    """定位一个文件节点的**值对象**(不含键名),返回 (start, end)"""
    cnt = js.count(key)
    assert cnt == 1, f'节点键出现 {cnt} 次,必须唯一: {key!r}'
    start = js.find(key)
    depth = 0
    i = start + key.index(b'{')
    val_start = i
    while i < len(js):
        c = js[i:i + 1]
        if c in b'{[':
            depth += 1
        elif c in b'}]':
            depth -= 1
            if depth == 0:
                return val_start, i + 1
        i += 1
    raise AssertionError('节点括号扫描失败')


def node_by_path(tree, path):
    node = tree
    for part in path.split('/'):
        node = node['files'][part]
    return node


t0 = time.time()

print('== 1) 解析当前 app.asar ==')
with open(ASAR, 'rb') as f:
    raw16 = f.read(16)
    old_header_size = u32(raw16, 4)
    js_len = u32(raw16, 12)
    js0 = f.read(js_len)
    old_base = 8 + old_header_size
old_size = os.path.getsize(ASAR)
data_len = old_size - old_base
print(f'headerSize={old_header_size} strlen={js_len} base={old_base} dataLen={data_len}')

header = json.loads(js0.decode('utf-8'))
renderer = header['files']['out']['files']['renderer']
node_html = renderer['files']['index.html']
css_name = next(k for k, v in renderer['files']['assets']['files'].items()
                if k.startswith('styles-') and k.endswith('.css') and v.get('size', 0) > 100000)
node_css = renderer['files']['assets']['files'][css_name]
CSS_PATH = 'out/renderer/assets/' + css_name
print(f'目标: out/renderer/index.html ({node_html["size"]}B) / {CSS_PATH} ({node_css["size"]}B)')


def extract_orig(node):
    with open(ASAR, 'rb') as g:
        g.seek(old_base + int(node['offset']))
        return g.read(node['size'])


print('== 2) 生成新文件内容 ==')
orig_html = extract_orig(node_html).decode('utf-8')
orig_css = extract_orig(node_css)

boot_style = open(os.path.join(SKIN, 'boot_style.css'), encoding='utf-8').read()
loading_tpl = open(os.path.join(SKIN, 'boot_loading.html'), encoding='utf-8').read()
override_css = open(os.path.join(SKIN, 'override.css'), 'rb').read()

# 抽取品牌 SVG:优先原版 startup-logo,兜底取 #loading 内第一个 svg(幂等:已打补丁也成立)
msvg = re.search(r'(<svg[^>]*class="startup-logo".*?</svg>)', orig_html, re.S)
if not msvg:
    ld = orig_html.find('<div id="loading"')
    msvg = re.search(r'(<svg.*?</svg>)', orig_html[ld:ld + 20000], re.S)
assert msvg, '未找到品牌 SVG'
svg = re.sub(r'\s+', ' ', msvg.group(1)).strip()
new_loading = loading_tpl.replace('{{SVG}}', svg)

# 替换内联 <style>(幂等:原版或已打补丁都只有一个 <style> 块)
a = orig_html.find('<style>')
b = orig_html.find('</style>') + len('</style>')
assert a >= 0 and b > a
new_html = orig_html[:a] + '<style>\n' + boot_style + '\n    </style>' + orig_html[b:]
# 替换 #loading / #efx-loading 区块(到 </body> 之前;页面脚本全部位于 head)
mstart = re.search(r'<div id="(?:efx-)?loading"', new_html)
assert mstart, '未找到 loading 区块起点'
a = mstart.start()
b = new_html.find('</body>', a)
assert a >= 0 and b > a
new_html = new_html[:a] + new_loading + '\n  ' + new_html[b:]

# 注入 HUD(十字准星 + 左下角 GPU/电量/时钟;哨兵注释保证幂等)
hud = open(os.path.join(SKIN, 'hud_block.html'), encoding='utf-8').read()
new_html = re.sub(r'<!-- EFX-HUD-START -->.*?<!-- EFX-HUD-END -->\n?', '', new_html, flags=re.S)
assert new_html.count('</body>') == 1, '</body> 应唯一'
new_html = new_html.replace('</body>', hud + '</body>')
print('HUD 已注入:', 'efx-hud' in new_html)
new_html_bytes = new_html.encode('utf-8')
print(f'index.html: {len(orig_html)} -> {len(new_html_bytes)} bytes')

# CSS:剥掉旧覆盖层(若有)再追加新版,保证幂等
marker = b'ZCODE ENDFIELD INDUSTRIAL SKIN'
mp = orig_css.find(marker)
if mp >= 0:
    cut = orig_css.rfind(b'/*', 0, mp)
    assert cut >= 0
    orig_css = orig_css[:cut].rstrip() + b'\n'
new_css_bytes = orig_css + b'\n' + override_css
print(f'{css_name}: {len(orig_css)} -> {len(new_css_bytes)} bytes')

# 追加偏移(数据布局与头部无关,可直接确定)
rel_end = data_len
off_html, off_css = str(rel_end), str(rel_end + len(new_html_bytes))
integrity_html = make_integrity(new_html_bytes)
integrity_css = make_integrity(new_css_bytes)

print('== 3) 头部手术 ==')
js1 = js0
for name, node, new_size, new_off, integ in [
    ('index.html', node_html, len(new_html_bytes), off_html, integrity_html),
    (css_name, node_css, len(new_css_bytes), off_css, integrity_css),
]:
    key = f'"{name}":{{"size":{node["size"]},'.encode('utf-8')
    s, e = locate_node(js1, key)
    new_text = json.dumps({'size': new_size, 'offset': new_off, 'integrity': integ},
                          ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    js1 = js1[:s] + new_text + js1[e:]
    print(f'  {name}: 值对象 {e - s} -> {len(new_text)} 字节 @ {s}')

strlen = len(js1)
pad = (-strlen) % 4
payload = 4 + strlen + pad
header_size = 4 + payload
new_base = 8 + header_size
print(f'new strlen={strlen} pad={pad} headerSize={header_size} (原 {old_header_size})')

print('== 4) 语义对比(除两个目标节点外必须一致) ==')
tree_new = json.loads(js1.decode('utf-8'))
diffs = []
stack = [('', header, tree_new)]
while stack:
    prefix, n1, n2 = stack.pop()
    if 'files' in n1:
        assert 'files' in n2, f'结构差异 @ {prefix}'
        assert set(n1['files']) == set(n2['files']), f'子项差异 @ {prefix}'
        for k in n1['files']:
            stack.append((prefix + '/' + k, n1['files'][k], n2['files'][k]))
    else:
        for field in ('size', 'offset', 'integrity'):
            if n1.get(field) != n2.get(field):
                diffs.append((prefix.lstrip('/'), field))
allowed = {'out/renderer/index.html', 'out/renderer/assets/' + css_name}
bad = [d for d in diffs if d[0] not in allowed]
print(f'  差异字段 {len(diffs)} 个: {sorted(set(d[0] for d in diffs))}')
assert not bad, f'出现意外差异: {bad}'
assert {d[0] for d in diffs} == allowed, '目标节点差异不完整'

print('== 5) 写入新包 ==')
with open(ASAR, 'rb') as src, open(OUT, 'wb') as dst:
    dst.write(struct.pack('<IIII', 4, header_size, payload, strlen))
    dst.write(js1)
    dst.write(b'\x00' * pad)
    assert dst.tell() == new_base, f'头部写入 {dst.tell()} != {new_base}'
    src.seek(old_base)
    copied = 0
    while True:
        chunk = src.read(CHUNK)
        if not chunk:
            break
        dst.write(chunk)
        copied += len(chunk)
    assert copied == data_len, f'数据区复制不完整 {copied} != {data_len}'
    dst.write(new_html_bytes)
    dst.write(new_css_bytes)
print(f'输出 {os.path.getsize(OUT)} bytes')

print('== 6) 全量校验(sha256 逐文件) ==')
with open(OUT, 'rb') as f:
    raw16 = f.read(16)
    hs = u32(raw16, 4)
    jl = u32(raw16, 12)
    tree_v = json.loads(f.read(jl).decode('utf-8'))
    base_v = 8 + hs
    bad = 0
    total = 0
    stack = [('', tree_v['files'])]
    while stack:
        prefix, files = stack.pop()
        for name, n in files.items():
            p = prefix + '/' + name if prefix else name
            if 'files' in n:
                stack.append((p, n['files']))
            else:
                if n.get('unpacked') or 'offset' not in n:
                    continue
                total += 1
                f.seek(base_v + int(n['offset']))
                data = f.read(n['size'])
                if hashlib.sha256(data).hexdigest() != n['integrity']['hash']:
                    bad += 1
                    if bad <= 5:
                        print('  MISMATCH:', p)
print(f'校验完成: {total} 个文件, 损坏 {bad} 个, 耗时 {time.time()-t0:.1f}s')
if bad:
    raise SystemExit(1)
print('[DONE] 补丁包已生成:', OUT)
