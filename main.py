#!/usr/bin/env python3
import os
import re
import time
import requests
import qbittorrentapi
from datetime import datetime
from pathlib import Path

CONFIG_FILE = "torrents.conf"
TORRENT_FOLDER = "/torrents"  # Change to your torrent files folder
QB_HOST = "http://192.168.1.116:8081"
QB_USER = "admin"
QB_PASS = "reivf289gbegbe"

def parse_config():
    torrents = []
    cron_schedule = None

    with open(CONFIG_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                if line.startswith('# cron:'):
                    cron_schedule = line.replace('# cron:', '').strip()
                continue

            parts = line.split('|')
            if len(parts) >= 6:
                torrents.append({
                    'file_name': parts[0],
                    'name': parts[1],
                    'url': parts[2],
                    'need_updated': parts[3] == '1',
                    'save_path': parts[4],
                    'last_updated': parts[5]
                })

    return torrents, cron_schedule

def update_config(torrents):
    with open(CONFIG_FILE, 'w') as f:
        f.write("# cron: 0 */6 * * *  # Run every 6 hours\n")
        f.write("#file_name|torrent_name|torrent_url|need_updated|save_path|last_updated\n")
        for t in torrents:
            f.write(f"{t['file_name']}|{t['name']}|{t['url']}|{1 if t['need_updated'] else 0}|{t['save_path']}|{t['last_updated']}\n")

def download_torrent(url, save_path, file_name):
    try:
        # Handle blob URLs - they need special handling
        if url.startswith('blob:'):
            print(f"Warning: Blob URL detected for {file_name}. Manual download may be required.")
            print(f"URL: {url}")
            return None

        response = requests.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()

        # Use file_name from config or extract from URL
        if not file_name.endswith('.torrent'):
            filename = f"{file_name}.torrent"
        else:
            filename = file_name

        filepath = os.path.join(save_path, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)

        return filepath
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def get_existing_torrent(client, torrent_name):
    """Check if torrent already exists in qBittorrent"""
    torrents = client.torrents_info()
    for t in torrents:
        if t.name == torrent_name:
            return t
    return None

def update_torrents():
    torrents, _ = parse_config()
    updated = False

    # Connect to qBittorrent
    client = qbittorrentapi.Client(host=QB_HOST, username=QB_USER, password=QB_PASS)

    try:
        client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        print(f"qBittorrent login failed: {e}")
        return

    for torrent in torrents:
        if not torrent['need_updated']:
            continue

        torrent_file_path = os.path.join(TORRENT_FOLDER, torrent['file_name'])
        if not torrent_file_path.endswith('.torrent'):
            torrent_file_path += '.torrent'

        # Check if torrent file exists
        if not os.path.exists(torrent_file_path):
            print(f"Torrent file not found: {torrent_file_path}")
            continue

        # Check if torrent is already in qBittorrent
        existing = get_existing_torrent(client, torrent['name'])

        # Download new torrent
        print(f"Checking {torrent['name']}...")
        new_torrent = download_torrent(torrent['url'], TORRENT_FOLDER, torrent['file_name'])

        if new_torrent:
            # Add to qBittorrent with save path
            with open(new_torrent, 'rb') as f:
                client.torrents_add(
                    torrent_files=[f],
                    save_path=torrent['save_path'],
                    is_skip_checking=False,
                    is_paused=False
                )

            # If existing torrent found, optionally delete old one
            if existing:
                print(f"Existing torrent found for {torrent['name']}, new version added")
                # Uncomment to delete old torrent
                # client.torrents_delete(delete_files=False, torrent_hashes=existing.hash)

            # Update last_updated
            torrent['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated = True
            print(f"Updated {torrent['name']} to save path: {torrent['save_path']}")

    if updated:
        update_config(torrents)

    client.auth_log_out()

def setup_cron():
    """Optional: Setup cron job automatically"""
    from crontab import CronTab

    cron = CronTab(user=True)
    script_path = os.path.abspath(__file__)

    # Remove existing jobs
    cron.remove_all(comment='torrent_updater')

    # Add new job based on config
    torrents, cron_schedule = parse_config()
    if cron_schedule:
        job = cron.new(command=f'python3 {script_path}', comment='torrent_updater')
        job.setall(cron_schedule)
        cron.write()
        print(f"Cron job set to: {cron_schedule}")

def validate_url(url):
    """Check if URL is valid for automated download"""
    if url.startswith('blob:'):
        return False
    return True

if __name__ == "__main__":
    # Create torrent folder if not exists
    Path(TORRENT_FOLDER).mkdir(parents=True, exist_ok=True)

    # Validate config URLs
    torrents, _ = parse_config()
    for t in torrents:
        if not validate_url(t['url']):
            print(f"Warning: {t['name']} has blob URL - automatic download may fail")

    # Run update
    update_torrents()

    # Optional: Uncomment to setup cron
    # setup_cron()