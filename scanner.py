#!/usr/bin/env python3
"""
Core scanning engine.
"""

import asyncio
import aiohttp
import os
import time
import random
import signal
from typing import Set, List, Optional, Dict, Tuple
from urllib.parse import urljoin
from dataclasses import dataclass

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.console import Console

from wordlist import read_wordlist, count_lines
from requester import Requester
import output

console = Console()

@dataclass
class ScanResult:
    """Simple result container."""
    url: str
    status: int
    size: int
    content_type: str = ''

class Scanner:
    """
    Main scanner class. Orchestrates the discovery process.
    """

    def __init__(self, args):
        self.args = args
        self.base_url = args.url.rstrip('/')
        self.fuzz_mode = 'FUZZ' in args.url
        self.wordlist_path = args.wordlist
        self.extensions = [ext.strip() for ext in args.extensions.split(',')] if args.extensions else []
        self.recursive = args.recursive
        self.max_depth = args.depth
        self.verbose = args.verbose
        self.silent = args.silent
        self.debug = args.debug
        self.output_file = args.output

        # Status filtering
        self.status_filter = None
        if args.status:
            self.status_filter = [int(s.strip()) for s in args.status.split(',')]
        self.exclude_status = []
        if args.exclude_status:
            self.exclude_status = [int(s.strip()) for s in args.exclude_status.split(',')]

        # Size filtering
        self.filter_size = args.filter_size
        self.filter_words = args.filter_words

        # Internal state
        self.found_urls: Set[str] = set()
        self.pending_queue: asyncio.Queue = asyncio.Queue()
        self.seen_paths: Set[str] = set()
        self.stats = {
            'total': 0,
            'found': 0,
            'errors': 0,
            'start_time': time.time()
        }
        self._shutdown = False

        # Pre-count wordlist for progress bar
        self.total_words = count_lines(self.wordlist_path)

    def should_filter(self, resp: aiohttp.ClientResponse, content: str) -> bool:
        """
        Apply user-defined filters. Return True if response should be ignored.
        """
        # Status code filtering
        if self.status_filter and resp.status not in self.status_filter:
            return True
        if resp.status in self.exclude_status:
            return True

        # Size filtering
        if self.filter_size and len(content) == self.filter_size:
            return True
        if self.filter_words and len(content.split()) == self.filter_words:
            return True

        return False

    async def producer(self):
        """
        Read the wordlist and push URLs into the queue.
        """
        async for word in read_wordlist(self.wordlist_path):
            if self._shutdown:
                break

            if self.fuzz_mode:
                url = self.base_url.replace('FUZZ', word)
            else:
                url = urljoin(self.base_url + '/', word)

            # Add base URL
            if url not in self.seen_paths:
                self.seen_paths.add(url)
                await self.pending_queue.put((url, 0))

            # Add extensions
            if not self.fuzz_mode and self.extensions:
                for ext in self.extensions:
                    ext_url = f"{url}.{ext}"
                    if ext_url not in self.seen_paths:
                        self.seen_paths.add(ext_url)
                        await self.pending_queue.put((ext_url, 0))

    async def consumer(self, requester: Requester, task_id: TaskID, progress: Progress):
        """
        Consume URLs from the queue, perform requests, and handle results.
        """
        while not self._shutdown:
            try:
                url, depth = await asyncio.wait_for(self.pending_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                if self.pending_queue.empty():
                    break
                continue

            self.stats['total'] += 1
            start_time = time.time()

            try:
                resp = await requester.request('GET', url)
                elapsed = time.time() - start_time

                if resp:
                    content = await resp.text()
                    size = len(content)
                    content_type = resp.headers.get('content-type', '')

                    # Always show in verbose mode
                    if self.verbose:
                        output.print_result(url, resp.status, size, content_type, verbose=True, silent=self.silent)

                    # Check if interesting (passes filters)
                    if not self.should_filter(resp, content):
                        self.stats['found'] += 1
                        self.found_urls.add(url)

                        # Show in normal mode (if not verbose, we already printed above)
                        if not self.verbose:
                            output.print_result(url, resp.status, size, content_type, verbose=False, silent=self.silent)

                        # Save to file
                        if self.output_file:
                            await output.save_result(url, resp.status, size, self.output_file)

                        # Recursive scan
                        if self.recursive and depth < self.max_depth:
                            if self._is_directory(resp, url):
                                new_base = url if url.endswith('/') else url + '/'
                                await self._add_recursive(new_base, depth + 1)
                else:
                    self.stats['errors'] += 1

            except Exception as e:
                self.stats['errors'] += 1
                if self.debug:
                    output.debug(f"Error on {url}: {e}")

            # Update progress
            progress.update(task_id, advance=1,
                            found=self.stats['found'],
                            errors=self.stats['errors'])
            self.pending_queue.task_done()

    def _is_directory(self, resp: aiohttp.ClientResponse, url: str) -> bool:
        """Heuristic to decide if a URL points to a directory."""
        if url.endswith('/'):
            return True
        # Redirect to a directory-like location
        if resp.status in (301, 302) and 'location' in resp.headers:
            loc = resp.headers['location']
            if loc.endswith('/') or '.' not in loc.split('/')[-1]:
                return True
        # Could also check content-type or presence of index page, but keep simple.
        return False

    async def _add_recursive(self, base_url: str, depth: int):
        """
        Start a recursive producer for a newly discovered directory.
        """
        async def recursive_producer():
            async for word in read_wordlist(self.wordlist_path):
                if self._shutdown:
                    break
                url = urljoin(base_url, word)
                if url not in self.seen_paths:
                    self.seen_paths.add(url)
                    await self.pending_queue.put((url, depth))

                    if self.extensions:
                        for ext in self.extensions:
                            ext_url = f"{url}.{ext}"
                            if ext_url not in self.seen_paths:
                                self.seen_paths.add(ext_url)
                                await self.pending_queue.put((ext_url, depth))

        asyncio.create_task(recursive_producer())

    async def run(self):
        """
        Main scan loop.
        """
        console.print(f"\n[cyan]🎯 Target:[/cyan] {self.base_url}")
        console.print(f"[cyan]📚 Wordlist:[/cyan] {self.wordlist_path} ({self.total_words} entries)")
        console.print(f"[cyan]⚡ Threads:[/cyan] {self.args.threads}")
        if self.extensions:
            console.print(f"[cyan]🔧 Extensions:[/cyan] {', '.join(self.extensions)}")
        console.print("")

        # Setup signal handler for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._shutdown_handler)

        # Create requester
        async with Requester(
            timeout=self.args.timeout,
            proxy=self.args.proxy,
            headers=self._parse_headers(self.args.headers),
            user_agent=self.args.user_agent,
            random_agent=self.args.random_agent,
            follow_redirects=self.args.follow_redirects,
            max_retries=3,
            rate_limit=self.args.rate_limit,
            delay=self.args.delay
        ) as requester:

            # Progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                "•",
                TextColumn("[cyan]{task.completed}/{task.total}"),
                "•",
                TextColumn("[green]✓ {task.fields[found]} found"),
                "•",
                TextColumn("[red]✗ {task.fields[errors]} errors"),
                transient=False,
            ) as progress:

                task_id = progress.add_task(
                    "Scanning...",
                    total=self.total_words or None,  # None if counting failed -> indeterminate
                    found=0,
                    errors=0
                )

                # Start producer
                producer_task = asyncio.create_task(self.producer())

                # Start consumers
                consumers = [
                    asyncio.create_task(self.consumer(requester, task_id, progress))
                    for _ in range(self.args.threads)
                ]

                # Wait for producer to finish
                await producer_task

                # Wait for queue to empty
                await self.pending_queue.join()

                # Shutdown
                self._shutdown = True
                for c in consumers:
                    c.cancel()
                await asyncio.gather(*consumers, return_exceptions=True)

        # Print summary
        elapsed = time.time() - self.stats['start_time']
        output.print_summary(self.stats, self.found_urls, self.base_url, elapsed, self.silent)

    def _shutdown_handler(self):
        """Handle Ctrl+C gracefully."""
        self._shutdown = True
        console.print("\n[yellow]⚠ Shutting down gracefully...[/yellow]")

    def _parse_headers(self, headers_arg: Optional[str]) -> Optional[Dict]:
        """Parse headers from JSON string."""
        if not headers_arg:
            return None
        try:
            import json
            return json.loads(headers_arg)
        except Exception:
            output.error("Failed to parse headers. Must be valid JSON.")
            return None