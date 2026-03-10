#!/usr/bin/env python3
"""
Wordlist manager: efficient reading and counting of wordlist files.
"""

import aiofiles
import os
from typing import AsyncGenerator

async def read_wordlist(filepath: str) -> AsyncGenerator[str, None]:
    """
    Asynchronously yield each non-empty, non-comment line from the wordlist.
    """
    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Wordlist not found: {filepath}")
        
        async with aiofiles.open(filepath, mode='r', encoding='utf-8', errors='ignore') as f:
            async for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    yield line
    except Exception as e:
        print(f"❌ Error reading wordlist: {e}")
        raise

def count_lines(filepath: str) -> int:
    """
    Synchronously count the number of valid (non-empty, non-comment) lines in a wordlist.
    Used for progress bar total.
    """
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    count += 1
    except Exception:
        # If we can't count, just return 0 (progress bar will be indeterminate)
        return 0
    return count

def get_stats(filepath: str) -> dict:
    """
    Return detailed statistics about the wordlist.
    """
    stats = {
        'total_lines': 0,
        'valid_entries': 0,
        'comments': 0,
        'empty_lines': 0,
        'file_size': 0,
        'file_name': os.path.basename(filepath)
    }
    try:
        stats['file_size'] = os.path.getsize(filepath)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                stats['total_lines'] += 1
                line = line.strip()
                if not line:
                    stats['empty_lines'] += 1
                elif line.startswith('#'):
                    stats['comments'] += 1
                else:
                    stats['valid_entries'] += 1
    except Exception:
        pass
    return stats