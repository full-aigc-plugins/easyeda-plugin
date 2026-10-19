"""同步独立技能包的自包含快照；不会覆盖无法追溯的本地修改。"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sync(source, check=False, root=ROOT):
    source = Path(source).resolve()
    files = {}
    for path in sorted((source / 'skills').rglob('*')):
        if path.is_symlink():
            raise ValueError('来源技能含符号链接：' + str(path))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            files[path.relative_to(source).as_posix()] = path.read_bytes()
    for name in ['catalog.json', 'source-lock.json', 'official-assets.json', 'scripts/validate_official.py',
                 'docs/upstream-repositories.json', 'NOTICE', 'LICENSE']:
        files[name] = (source / name).read_bytes()
    files['scripts/validate_skills.py'] = (source / 'scripts/validate_package.py').read_bytes()
    if not files:
        raise ValueError('来源技能包为空')
    index = root / 'skill-snapshot.json'
    previous = json.loads(index.read_text()) if index.exists() else {'files': []}
    known = {x['path']: x['sha256'] for x in previous['files']}
    removed = set(known) - set(files)
    if removed:
        raise ValueError('来源移除了快照文件，请显式处理：' + ','.join(sorted(removed)))
    changes = []
    # 先检查全部文件，再写入，避免冲突时同步一半。
    for name, raw in files.items():
        target = root / name
        if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
            raise ValueError('目标含符号链接或父目录越界：' + name)
        if target.exists() and target.read_bytes() == raw:
            continue
        changes.append(name)
        if target.exists() and digest(target.read_bytes()) != known.get(name):
            raise ValueError('目标含未同步的人工修改：' + name)
    if check and changes:
        raise ValueError('快照与源包不一致：' + ','.join(changes))
    snapshot = {'schemaVersion': 1, 'source': 'full-aigc-skills/easyeda-skills',
                'sourceVersion': json.loads(files['catalog.json'])['version'],
                'published': False, 'files': [{'path': n, 'sha256': digest(raw)} for n, raw in sorted(files.items())]}
    if check:
        if not index.exists() or json.loads(index.read_text()) != snapshot:
            raise ValueError('快照索引不一致')
    else:
        for name, raw in files.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        index.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    return {'ok': True, 'files': len(files), 'changed': len(changes), 'checkOnly': check}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(sync(args.source, args.check), ensure_ascii=False))
