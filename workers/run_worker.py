#!/usr/bin/env python
"""
Celery Worker Runner
====================
Script to start Celery workers for background task processing.

Usage:
    python workers/run_worker.py           # Start analysis worker
    python workers/run_worker.py --beat    # Start beat scheduler
    python workers/run_worker.py --flower  # Start monitoring
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.celery_app import celery_app


def start_worker():
    """Start Celery worker."""
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '-Q', 'analysis,cleanup',
        '--concurrency=4',
    ])


def start_beat():
    """Start Celery beat scheduler."""
    celery_app.Beat(loglevel='info').run()


def start_flower():
    """Start Flower monitoring."""
    import subprocess
    subprocess.run([
        'celery', '-A', 'backend.app.core.celery_app',
        'flower', '--port=5555'
    ])


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Celery workers')
    parser.add_argument('--beat', action='store_true', help='Start beat scheduler')
    parser.add_argument('--flower', action='store_true', help='Start flower monitoring')
    
    args = parser.parse_args()
    
    if args.beat:
        print("Starting Celery Beat scheduler...")
        start_beat()
    elif args.flower:
        print("Starting Flower monitoring...")
        start_flower()
    else:
        print("Starting Celery worker...")
        start_worker()

