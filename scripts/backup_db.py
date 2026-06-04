#!/usr/bin/env python3
"""
Database backup script for WorldCupGame.
Copies draft.db (and WAL/SHM files) to backups/ directory.
Retains max 8 backups, removes any older than 3 days.
"""

import os
import shutil
import glob
import time
from datetime import datetime

# Paths (relative to project root, which is parent of this script)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'instance', 'draft.db')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backups')
MAX_BACKUPS = 8
MAX_AGE_DAYS = 3


def backup():
    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f'[BACKUP] ERROR: Database not found at {DB_PATH}')
        return

    # Generate timestamped filename
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    backup_name = f'draft_{ts}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    # Copy main db file
    shutil.copy2(DB_PATH, backup_path)
    size_kb = os.path.getsize(backup_path) / 1024
    print(f'[BACKUP] Created: {backup_name} ({size_kb:.1f} KB)')

    # Copy WAL and SHM files if they exist
    for suffix in ['-wal', '-shm']:
        src = DB_PATH + suffix
        if os.path.exists(src):
            dst = backup_path + suffix
            shutil.copy2(src, dst)
            print(f'[BACKUP] Copied: {backup_name}{suffix}')

    # Cleanup: remove backups older than 3 days
    now = time.time()
    cutoff = now - (MAX_AGE_DAYS * 86400)
    removed = 0
    for f in glob.glob(os.path.join(BACKUP_DIR, 'draft_*.db')):
        if os.path.getmtime(f) < cutoff:
            os.remove(f)
            # Also remove associated WAL/SHM
            for suffix in ['-wal', '-shm']:
                wal = f + suffix
                if os.path.exists(wal):
                    os.remove(wal)
            removed += 1
            print(f'[BACKUP] Removed old: {os.path.basename(f)}')

    # Cleanup: keep only MAX_BACKUPS most recent
    backups = sorted(
        glob.glob(os.path.join(BACKUP_DIR, 'draft_*.db')),
        key=os.path.getmtime,
        reverse=True
    )
    for old in backups[MAX_BACKUPS:]:
        os.remove(old)
        for suffix in ['-wal', '-shm']:
            wal = old + suffix
            if os.path.exists(wal):
                os.remove(wal)
        removed += 1
        print(f'[BACKUP] Removed excess: {os.path.basename(old)}')

    total = len(glob.glob(os.path.join(BACKUP_DIR, 'draft_*.db')))
    print(f'[BACKUP] Done. {total} backups kept, {removed} removed.')


if __name__ == '__main__':
    backup()
