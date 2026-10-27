"""Read-only package integrity and local prerequisites check. No network calls."""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', action='store_true')
    args = parser.parse_args()
    errors = []
    hashes = json.loads((ROOT / 'SHA256SUMS.json').read_text(encoding='utf-8'))
    for name, expected in hashes.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            errors.append(f'Missing/invalid path: {name}')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            errors.append(f'Changed file: {name}')
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.json' and '.git' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if actual != set(hashes):
        errors.append('File inventory differs from SHA256SUMS.json')
    for path in ROOT.rglob('*.json'):
        if '.git' in path.relative_to(ROOT).parts:
            continue
        json.loads(path.read_text(encoding='utf-8'))
    for path in (ROOT / 'restore').glob('*.toml'):
        tomllib.loads(path.read_text(encoding='utf-8'))
    plugin = ROOT / 'plugins/edy-workbench'
    manifest = json.loads((plugin / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    for key in ['skills', 'mcpServers', 'hooks']:
        target = (plugin / manifest[key]).resolve()
        if not target.is_relative_to(plugin) or not target.exists():
            errors.append('Invalid manifest path: ' + key)
    skills = sorted((plugin / 'skills').iterdir())
    for skill in skills:
        content = (skill / 'SKILL.md').read_text(encoding='utf-8')
        if not content.startswith('---\n') or not re.search(r'^name: ' + re.escape(skill.name) + r'\s*$', content, re.M):
            errors.append('Invalid skill: ' + skill.name)
    print(json.dumps({'integrity': 'FAIL' if errors else 'PASS', 'files': len(hashes), 'skills': len(skills), 'errors': errors}, ensure_ascii=False, indent=2))
    if args.environment:
        # Report names and presence only, never credential values.
        checks = {name: bool(shutil.which(name)) for name in ['python', 'git', 'cmd.exe', 'npx', 'codex']}
        checks.update({name: bool(os.environ.get(name)) for name in ['GITHUB_PAT_TOKEN', 'TAVILY_API_KEY']})
        checks.update({str(p): p.exists() for p in [Path('D:/Tools/lark-cli/lark-cli.ps1'), Path('D:/Tools/wechat-cli-local/wechat-cli.cmd')]})
        print(json.dumps({'environment_presence_only': checks, 'note': 'Presence does not establish authentication or service readiness.'}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
