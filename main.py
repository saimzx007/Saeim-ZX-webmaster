#!/usr/bin/env python3
"""
Main entry point for the web content discovery tool.
"""

import asyncio
import sys
from cli import parse_args
from scanner import Scanner

def main():
    print(r"""
    ╔══════════════════════════════════════════════════════════╗
    ║  ██╗   ██╗██╗  ████████╗██████╗  █████╗                 ║
    ║  ██║   ██║██║  ╚══██╔══╝██╔══██╗██╔══██╗                ║
    ║  ██║   ██║██║     ██║   ██████╔╝███████║                ║
    ║  ██║   ██║██║     ██║   ██╔══██╗██╔══██║                ║
    ║  ╚██████╔╝██║     ██║   ██║  ██║██║  ██║                ║
    ║   ╚═════╝ ╚═╝     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝                ║
    ║                                                          
    ║        🚀 WEB CONTENT DISCOVERY TOOL v2.0                ║
    ║    This Tool Development By   Saeim ZX... Your Daddy     ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    args = parse_args()
    scanner = Scanner(args)
    
    try:
        asyncio.run(scanner.run())
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()