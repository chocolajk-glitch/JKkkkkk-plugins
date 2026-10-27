"""Codex lifecycle hooks: create local code checkpoints, never push.

stdin: documented Codex hook JSON. stdout: JSON only. No third-party packages.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
STATE = Path(os.environ.get('CODEX_GIT_HOOK_STATE', str(Path(os.environ.get('PLUGIN_DATA', str(BASE))) / 'git-checkpoints')))
SOURCE = set('.py .pyi .js .jsx .mjs .cjs .ts .tsx .java .kt .kts .go .rs .c .h .cpp .hpp .cc .cs .fs .swift .m .mm .php .rb .scala .sql .sh .bash .ps1 .psm1 .bat .cmd .html .htm .css .scss .sass .less .vue .svelte .dart .lua .r .jl .ex .exs .erl .clj .cljs .ipynb .proto .graphql .gql .tf .sol .zig .asm .s'.split())
EXCLUDED = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', 'dist', 'build', '.next', '.nuxt', 'target', 'vendor', '.cache'}
IGNORE = '\n# Codex automatic checkpoint exclusions\n.env\n.env.*\n!.env.example\n!.env.sample\n*.pem\n*.key\n*.pfx\n*.p12\nnode_modules/\n.venv/\nvenv/\n__pycache__/\n.pytest_cache/\n.mypy_cache/\ndist/\nbuild/\n.next/\ntarget/\n*.log\n'


def git(root, *args, check=True, data=None):
    p = subprocess.run(['git', '-C', str(root), *args], input=data, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=90)
    if check and p.returncode:
        # Never echo command output: it can contain secrets or hook output.
        raise RuntimeError(f'git {args[0]} failed (exit {p.returncode}); inspect Git manually')
    return p


def root_for(cwd):
    p = git(cwd, 'rev-parse', '--show-toplevel', check=False)
    return Path(os.fsdecode(p.stdout).strip()).resolve() if p.returncode == 0 else cwd


def key(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    temp.replace(path)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def head(root):
    p = git(root, 'rev-parse', '--verify', 'HEAD', check=False)
    return p.stdout.decode().strip() if not p.returncode else None


def status(root):
    raw = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--no-renames').stdout
    return [(x[:2].decode('ascii'), os.fsdecode(x[3:])) for x in raw.split(b'\0') if x]


def sensitive(name):
    p = Path(name)
    return (any(x in EXCLUDED for x in p.parts) or
            (p.name.startswith('.env') and p.name not in {'.env.example', '.env.sample'}) or
            p.suffix.lower() in {'.pem', '.key', '.pfx', '.p12'} or
            p.name.lower() in {'credentials.json', 'id_rsa', 'id_ed25519'})


def scan(root):
    result = {}
    for directory, folders, files in os.walk(root, followlinks=False):
        folders[:] = [x for x in folders if x not in EXCLUDED and not (Path(directory) / x).is_symlink()]
        for name in files:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or sensitive(relative):
                continue
            if len(result) >= 30000:
                raise RuntimeError('directory too large; use a dedicated project directory')
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def is_code(name):
    return Path(name).suffix.lower() in SOURCE or Path(name).name in {'Dockerfile', 'Makefile', 'CMakeLists.txt'}


def run(event):
    STATE.mkdir(parents=True, exist_ok=True)
    cwd = Path(event['cwd']).resolve()
    session = str(event['session_id'])
    turn = str(event.get('turn_id', ''))
    if not turn:
        return 'Skipped: event has no turn_id.'
    root = root_for(cwd)
    token = key(session + ':' + turn)
    baseline = STATE / (token + '.json')
    lease = STATE / (key(str(root).lower()) + '.lease')
    kind = event['hook_event_name']
    if kind == 'UserPromptSubmit':
        if baseline.exists():
            return None  # A Stop continuation must not overwrite the baseline.
        broad = {Path(root.anchor), Path.home(), Path('D:/Code'), Path('D:/Tools'), Path('D:/Codex'), Path.home() / 'Documents'}
        if root in broad:
            return 'Skipped: workspace is a shared parent directory.'
        prompt = str(event.get('prompt', ''))
        if re.search(r'只分析|仅分析|只读|不要(?:动手|修改|提交)|不提交|先不(?:用)?动手|do not (?:commit|modify)|don.t commit|read.only', prompt, re.I):
            return None
        repo = git(root, 'rev-parse', '--is-inside-work-tree', check=False).returncode == 0
        if repo and status(root):
            return 'Skipped: repository already has uncommitted files; automatic checkpoint disabled for this turn.'
        record = {'token': token, 'session': session, 'turn': turn, 'root': str(root), 'repo': repo,
                  'head': head(root) if repo else None, 'files': {} if repo else scan(root)}
        try:
            with lease.open('x', encoding='utf-8') as f:
                json.dump({'token': token, 'conflict': False}, f)
        except FileExistsError:
            owner = read(lease)
            owner['conflict'] = True
            save(lease, owner)
            return 'Skipped: another turn owns this repository; both automatic checkpoints are disabled.'
        save(baseline, record)
        return None
    if kind not in {'Stop', 'Interrupt'} or not baseline.exists():
        return None
    record = read(baseline)
    if str(root) != record['root']:
        return 'Skipped: workspace root changed.'
    if record.get('done'):
        return None
    try:
        owner = read(lease)
        if owner['token'] != token or owner['conflict']:
            return 'Skipped: overlapping tasks detected.'
        if kind == 'Interrupt':
            return None
        if event.get('stop_hook_active'):
            return 'Skipped: Stop continuation; checkpoint deferred.'
        message = str(event.get('last_assistant_message') or '')
        if re.search(r'等待(?:你|用户)|任务尚未完成|任务未完成|测试失败|检查失败|请(?:你)?确认|需要你(?:确认|提供)|tests? (?:failed|failing)|awaiting (?:input|approval)|task (?:incomplete|unfinished)', message, re.I):
            return 'Skipped: final response indicates unfinished work or failed checks.'
        if record['repo']:
            if head(root) != record['head']:
                return 'Skipped: HEAD changed during this turn (possibly already committed).'
            entries = status(root)
            if any(flags[0] != ' ' and flags != '??' for flags, _ in entries):
                return 'Skipped: index contains staged changes; preserving their owner.'
            names = [name for _, name in entries]
        else:
            if git(root, 'rev-parse', '--is-inside-work-tree', check=False).returncode == 0:
                return 'Skipped: another process initialized Git during this turn.'
            current = scan(root)
            names = [name for name in current.keys() | record['files'].keys() if current.get(name) != record['files'].get(name)]
        if not any(is_code(name) for name in names):
            return None
        if any(sensitive(name) for name in names):
            return 'Skipped: sensitive or generated file detected in changes.'
        if not record['repo']:
            git(root, 'init')
            ignore = root / '.gitignore'
            with ignore.open('a', encoding='utf-8', newline='\n') as f:
                f.write(IGNORE)
            names = sorted(set(names) | {'.gitignore'})
        for setting in ('user.name', 'user.email'):
            if not git(root, 'config', '--get', setting, check=False).stdout.strip():
                return 'Skipped: Git author identity is missing.'
        names = sorted(set(names))
        names = [name for name in names if git(root, '--literal-pathspecs', 'check-ignore', '--quiet', '--', name, check=False).returncode != 0]
        if not any(is_code(name) for name in names):
            return None
        payload = b'\0'.join(os.fsencode(x) for x in names) + b'\0'
        git(root, '--literal-pathspecs', 'add', '--pathspec-from-file=-', '--pathspec-file-nul', data=payload)
        staged = {os.fsdecode(x) for x in git(root, 'diff', '--cached', '--name-only', '-z', '--no-renames').stdout.split(b'\0') if x}
        if not staged.issubset(set(names)):
            return 'Skipped: index changed concurrently; inspect staged files before committing.'
        if git(root, 'diff', '--cached', '--quiet', check=False).returncode == 0:
            return None
        # Cheap secret screening; no claim that this detects every credential.
        diff = git(root, 'diff', '--cached', '--no-ext-diff', '--no-textconv', '--unified=0').stdout
        if re.search(rb'(?m)^\+(?!\+).*(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{24,})', diff):
            git(root, 'reset', '--quiet', '--', *names, check=False) if record['head'] else git(root, 'rm', '--cached', '--quiet', '--', *names, check=False)
            return 'Skipped: possible credential detected; changes preserved.'
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        git(root, 'commit', '-m', f'chore: checkpoint code changes ({stamp})')
        revision = head(root)[:12]
        return f'Git checkpoint created: {revision} ({len(names)} files). Local commit only; no push.'
    finally:
        record['done'] = True
        save(baseline, record)
        if lease.exists() and read(lease).get('token') == token:
            lease.unlink()


def main():
    event = {}
    try:
        event = json.load(sys.stdin)
        message = run(event)
    except Exception as exc:
        message = f'Git checkpoint hook: {type(exc).__name__}: {exc}'
    if message:
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / 'events.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps({'time': datetime.now(timezone.utc).isoformat(), 'event': event.get('hook_event_name'), 'message': message}, ensure_ascii=False) + '\n')
    print(json.dumps({'systemMessage': message} if message else {}, ensure_ascii=False))


if __name__ == '__main__':
    main()
