#!/usr/bin/env python3
"""
Command-line interface argument parsing.
"""

import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description="Advanced Web Content Discovery & Fuzzing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -u https://example.com -w common.txt -t 50
  python main.py -u https://example.com/FUZZ -w api.txt --extensions json
  python main.py -u https://example.com -w big.txt --recursive --depth 3
        """
    )
    
    # Target
    parser.add_argument("-u", "--url", required=True, help="Target URL (use FUZZ for fuzzing)")
    parser.add_argument("-w", "--wordlist", required=True, help="Path to wordlist file")
    
    # Performance
    parser.add_argument("-t", "--threads", type=int, default=50, help="Number of concurrent requests (default: 50)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    parser.add_argument("--delay", type=float, default=0, help="Delay between requests (seconds)")
    parser.add_argument("--rate-limit", type=int, help="Max requests per second")
    
    # Discovery
    parser.add_argument("--extensions", help="Comma-separated extensions to append (e.g., php,html,js)")
    parser.add_argument("--recursive", action="store_true", help="Enable recursive directory scanning")
    parser.add_argument("--depth", type=int, default=3, help="Max recursion depth (default: 3)")
    
    # Filtering
    parser.add_argument("--status", help="Show only these status codes (comma-separated, e.g., 200,403,301)")
    parser.add_argument("--exclude-status", help="Exclude these status codes")
    parser.add_argument("--filter-size", type=int, help="Exclude responses with exact size")
    parser.add_argument("--filter-words", type=int, help="Exclude responses with exact word count")
    
    # Output
    parser.add_argument("--output", help="Output file (extension determines format: .txt, .json, .csv)")
    parser.add_argument("--verbose", action="store_true", help="Show all responses including 404")
    parser.add_argument("--silent", action="store_true", help="Suppress all output except errors")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    # Advanced
    parser.add_argument("--proxy", help="Proxy URL (http:// or socks5://)")
    parser.add_argument("--headers", help="Custom headers as JSON string")
    parser.add_argument("--user-agent", help="Custom User-Agent string")
    parser.add_argument("--random-agent", action="store_true", help="Use random User-Agent for each request")
    parser.add_argument("--follow-redirects", action="store_true", help="Follow redirects")
    parser.add_argument("--wildcard-detect", action="store_true", help="Detect wildcard responses (experimental)")
    parser.add_argument("--resume", help="Resume scan from saved state file")
    
    return parser.parse_args()