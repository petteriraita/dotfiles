#!/usr/bin/env python3
"""Use a separate persistent Brave profile for authorized browser tasks."""
import argparse
import os
from pathlib import Path
import shutil
import sys
from playwright.sync_api import sync_playwright, Error

PROFILE = Path.home() / '.local/share/codex-browser/profile'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['open', 'text'], help='open a visible browser or print page text')
    parser.add_argument('url', help='http(s) URL to open')
    args = parser.parse_args()
    if not args.url.startswith(('https://', 'http://')):
        parser.error('URL must use http or https')
    executable = shutil.which('brave-browser-stable')
    if not executable:
        parser.error('brave-browser-stable is not installed')
    PROFILE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(PROFILE, 0o700)
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(str(PROFILE), executable_path=executable, headless=args.mode == 'text')
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
            if args.mode == 'open':
                print('Automation browser open. Close its window when finished.', flush=True)
                import time
                while context.pages:
                    time.sleep(0.5)
            else:
                print('URL:', page.url)
                print(page.locator('body').inner_text(timeout=30000))
            context.close()
    except Error as e:
        print('Browser automation error:', e, file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
