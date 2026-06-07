import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_secret(file_rel_path, env_var=None):
    """File first; environment variable overrides if set."""
    if env_var:
        val = os.environ.get(env_var, '').strip()
        if val:
            return val
    path = os.path.join(ROOT, file_rel_path.replace('/', os.sep))
    if not os.path.isfile(path):
        return ''
    with open(path, encoding='utf-8') as f:
        return f.readline().strip()
