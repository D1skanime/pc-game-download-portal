#!/usr/bin/env python3
"""Token-owned connected description browser proof."""

from phase35_browser import browser_config as previous_config


def browser_config(url="http://127.0.0.1:3345"):
    return previous_config(url)
