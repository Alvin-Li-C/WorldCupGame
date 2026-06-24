#!/usr/bin/env python3
"""Push local HEAD to origin/main via GitHub Git API when git push is blocked."""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
API = 'https://api.github.com'
REPO = 'Alvin-Li-C/WorldCupGame'
GITHUB_TOKEN_FILE = 'static/basedata/github-token.txt'
GITHUB_TOKEN_ENV = 'GITHUB_TOKEN'
DESKTOP_TOKEN_FILE = os.path.join(os.path.expanduser('~'), 'Desktop', 'GithubToken')
SKIP_PREFIXES = ('__pycache__/', '.qoder/', 'dist/', 'data/kb/', '.cursor/')


def _should_push(path: str) -> bool:
    return not any(path.startswith(p) for p in SKIP_PREFIXES)


def _read_token_file(path: str) -> str:
    if not path or not os.path.isfile(path):
        return ''
    with open(path, encoding='utf-8') as f:
        return f.readline().strip()


def _token():
    from briefing.secrets import read_secret

    tok = read_secret(GITHUB_TOKEN_FILE, GITHUB_TOKEN_ENV)
    if tok:
        return tok
    tok = _read_token_file(DESKTOP_TOKEN_FILE)
    if tok:
        return tok
    try:
        proc = subprocess.run(
            ['git', 'credential', 'fill'],
            cwd=ROOT,
            input='protocol=https\nhost=github.com\n\n',
            capture_output=True,
            text=True,
            timeout=15,
        )
        for line in proc.stdout.splitlines():
            if line.startswith('password='):
                tok = line.split('=', 1)[1].strip()
                if tok:
                    return tok
    except (subprocess.SubprocessError, OSError):
        pass
    url = subprocess.check_output(
        ['git', 'remote', 'get-url', 'origin'], cwd=ROOT, text=True,
    ).strip()
    if '@' in url and '://' in url:
        auth = url.split('://', 1)[1].split('@', 1)[0]
        if ':' in auth:
            return auth.split(':', 1)[1]
    raise SystemExit('No GitHub token available')


def _api(method, path, token, payload=None, retries=5):
    data = None
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'WorldCupGame-deploy',
    }
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(f'{API}{path}', data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionResetError) as e:
            last_err = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403, 404, 422):
                raise
            wait = min(2 ** attempt, 30)
            print(f'  retry {attempt + 1}/{retries} after {wait}s: {e}', file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(last_err or f'API failed: {path}')


def _git(*args):
    return subprocess.check_output(
        ['git', *args], cwd=ROOT, text=True, encoding='utf-8', errors='replace',
    ).strip()


def _remote_in_local(remote_sha: str) -> bool:
    try:
        subprocess.check_output(['git', 'cat-file', '-t', remote_sha], cwd=ROOT, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def _local_blob_sha(path: str) -> str:
    full = os.path.join(ROOT, path.replace('/', os.sep))
    return _git('hash-object', full)


def _remote_tree_blobs(token: str, commit_sha: str) -> dict[str, str]:
    tree_sha = _api('GET', f'/repos/{REPO}/git/commits/{commit_sha}', token)['tree']['sha']
    data = _api('GET', f'/repos/{REPO}/git/trees/{tree_sha}?recursive=1', token)
    return {
        item['path']: item['sha']
        for item in data.get('tree') or []
        if item.get('type') == 'blob'
    }


def _blob_for_path(token, path):
    full = os.path.join(ROOT, path.replace('/', os.sep))
    with open(full, 'rb') as f:
        content = f.read()
    blob = _api('POST', f'/repos/{REPO}/git/blobs', token, {
        'content': base64.b64encode(content).decode('ascii'),
        'encoding': 'base64',
    })
    return blob['sha']


def _push_one_commit(token, remote_sha, commit_sha):
    paths = _git('diff-tree', '--no-commit-id', '--name-only', '-r', commit_sha).splitlines()
    paths = [p for p in paths if p]
    if not paths:
        msg = _git('log', '-1', '--format=%B', commit_sha).strip() or 'empty commit'
        parent_tree = _api('GET', f'/repos/{REPO}/git/commits/{remote_sha}', token)['tree']['sha']
        commit = _api('POST', f'/repos/{REPO}/git/commits', token, {
            'message': msg,
            'tree': parent_tree,
            'parents': [remote_sha],
        })
        return commit['sha'], 0

    tree_entries = []
    for path in paths:
        full = os.path.join(ROOT, path.replace('/', os.sep))
        if not os.path.isfile(full):
            print(f'  skip deleted: {path}')
            continue
        sha = _blob_for_path(token, path)
        tree_entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': sha})
        print(f'  blob {path}')

    tree = _api('POST', f'/repos/{REPO}/git/trees', token, {
        'base_tree': remote_sha,
        'tree': tree_entries,
    })
    msg = _git('log', '-1', '--format=%B', commit_sha).strip()
    commit = _api('POST', f'/repos/{REPO}/git/commits', token, {
        'message': msg,
        'tree': tree['sha'],
        'parents': [remote_sha],
    })
    return commit['sha'], len(tree_entries)


def _push_delta(token, remote_sha, local_sha):
    """Push only files whose blob sha differs from remote (API commits not in local clone)."""
    remote_blobs = _remote_tree_blobs(token, remote_sha)
    candidates = set(_git('log', '--pretty=format:', '--name-only', 'origin/main..HEAD').splitlines())
    candidates = {p for p in candidates if p and _should_push(p)}
    to_push = []
    for path in sorted(candidates):
        full = os.path.join(ROOT, path.replace('/', os.sep))
        if not os.path.isfile(full):
            continue
        if remote_blobs.get(path) != _local_blob_sha(path):
            to_push.append(path)

    if not to_push:
        print('Remote tree already matches local changes since origin/main.')
        return remote_sha, 0

    print(f'Delta push: {len(to_push)} file(s) differ from remote')
    tree_entries = []
    for path in to_push:
        sha = _blob_for_path(token, path)
        tree_entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'sha': sha})
        print(f'  blob {path}')

    tree = _api('POST', f'/repos/{REPO}/git/trees', token, {
        'base_tree': remote_sha,
        'tree': tree_entries,
    })
    messages = _git('log', '--format=%s', 'origin/main..HEAD').splitlines()
    commit_msg = '\n'.join(messages) if messages else _git('log', '-1', '--format=%B', local_sha)
    commit = _api('POST', f'/repos/{REPO}/git/commits', token, {
        'message': commit_msg,
        'tree': tree['sha'],
        'parents': [remote_sha],
    })
    return commit['sha'], len(tree_entries)


def main():
    token = _token()
    branch = 'main'
    remote_sha = _api('GET', f'/repos/{REPO}/git/ref/heads/{branch}', token)['object']['sha']
    local_sha = _git('rev-parse', 'HEAD')
    if remote_sha == local_sha:
        print('Already up to date on remote.')
        return 0

    if _remote_in_local(remote_sha):
        commits = _git('rev-list', '--reverse', f'{remote_sha}..{local_sha}').splitlines()
        commits = [c for c in commits if c]
        if not commits:
            print('No commits to push.')
            return 0
        print(f'Pushing {len(commits)} commit(s) onto {remote_sha[:8]}...')
        total_files = 0
        for commit_sha in commits:
            short = commit_sha[:8]
            title = _git('log', '-1', '--format=%s', commit_sha)
            print(f'commit {short}: {title}')
            remote_sha, n = _push_one_commit(token, remote_sha, commit_sha)
            total_files += n
            _api('PATCH', f'/repos/{REPO}/git/refs/heads/{branch}', token, {'sha': remote_sha})
            print(f'  -> {remote_sha[:8]} ({n} files)')
        print(f'Done. {len(commits)} commits, {total_files} blobs -> {remote_sha[:8]}')
        return 0

    print(f'Remote {remote_sha[:8]} not in local clone; delta push to {local_sha[:8]}...')
    remote_sha, n = _push_delta(token, remote_sha, local_sha)
    if n:
        _api('PATCH', f'/repos/{REPO}/git/refs/heads/{branch}', token, {'sha': remote_sha})
    print(f'Pushed {n} files -> {remote_sha[:8]}')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f'HTTP {e.code}: {body[:500]}', file=sys.stderr)
        raise SystemExit(1)
