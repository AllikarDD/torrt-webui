#!/usr/bin/env python3
import os
import re
import time
import logging
import requests
import qbittorrentapi
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

CONFIG_FILE = "torrents.conf"
TORRENT_FOLDER = "/torrents"  # Change to your torrent files folder
QB_HOST = "http://192.168.1.116:8081"
QB_USER = "admin"
QB_PASS = "reivf289gbegbe"
LOG_FILE = "torrent_updater.log"
LOG_LEVEL = logging.DEBUG  # Change to DEBUG for more details

# Setup logging
def setup_logging():
    logger = logging.getLogger('TorrentUpdater')
    logger.setLevel(LOG_LEVEL)

    # File handler with rotation (5 MB per file, keep 3 backups)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setLevel(LOG_LEVEL)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize logger
logger = setup_logging()

def parse_config():
    torrents = []
    cron_schedule = None

    logger.debug("Parsing config file: %s", CONFIG_FILE)

    try:
        with open(CONFIG_FILE, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                if line.startswith('#'):
                    if line.startswith('# cron:'):
                        cron_schedule = line.replace('# cron:', '').strip()
                        logger.info("Found cron schedule: %s", cron_schedule)
                    continue

                parts = line.split('|')
                if len(parts) >= 6:
                    torrent = {
                        'file_name': parts[0],
                        'name': parts[1],
                        'url': parts[2],
                        'need_updated': parts[3] == '1',
                        'save_path': parts[4],
                        'last_updated': parts[5]
                    }
                    torrents.append(torrent)
                    logger.debug("Parsed torrent entry: %s (update: %s)",
                                 torrent['name'], torrent['need_updated'])
                else:
                    logger.warning("Line %d has incorrect format, skipping: %s", line_num, line)
    except FileNotFoundError:
        logger.error("Config file not found: %s", CONFIG_FILE)
        raise
    except Exception as e:
        logger.exception("Error parsing config file: %s", e)
        raise

    logger.info("Loaded %d torrent entries from config", len(torrents))
    return torrents, cron_schedule

def update_config(torrents):
    logger.info("Updating config file with new timestamps")

    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write("# cron: 0 */6 * * *  # Run every 6 hours\n")
            f.write("#file_name|torrent_name|torrent_url|need_updated|save_path|last_updated\n")
            for t in torrents:
                line = f"{t['file_name']}|{t['name']}|{t['url']}|{1 if t['need_updated'] else 0}|{t['save_path']}|{t['last_updated']}\n"
                f.write(line)
                logger.debug("Updated config line for: %s", t['name'])

        logger.info("Config file updated successfully")
    except Exception as e:
        logger.exception("Error updating config file: %s", e)
        raise

def download_torrent(url, save_path, file_name):
    logger.info("Downloading torrent: %s from URL: %s", file_name, url)

    try:
        # Handle blob URLs - they need special handling
        if url.startswith('blob:'):
            logger.error("Blob URL detected for %s. Automatic download not possible.", file_name)
            logger.error("URL: %s", url)
            return None

        logger.debug("Sending GET request to: %s", url)
        response = requests.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()

        logger.debug("Response status: %d, content length: %d bytes",
                     response.status_code, len(response.content))

        # Use file_name from config or extract from URL
        if not file_name.endswith('.torrent'):
            filename = f"{file_name}.torrent"
        else:
            filename = file_name

        filepath = os.path.join(save_path, filename)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        logger.info("Successfully downloaded torrent to: %s (%d bytes)",
                    filepath, len(response.content))
        return filepath

    except requests.exceptions.Timeout:
        logger.error("Timeout downloading %s from %s", file_name, url)
    except requests.exceptions.ConnectionError as e:
        logger.error("Connection error downloading %s: %s", file_name, e)
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP error downloading %s: %s", file_name, e)
    except Exception as e:
        logger.exception("Unexpected error downloading %s: %s", file_name, e)

    return None

def get_existing_torrent(client, torrent_name):
    """Check if torrent already exists in qBittorrent"""
    logger.debug("Checking if torrent exists in qBittorrent: %s", torrent_name)

    try:
        torrents = client.torrents_info()
        for t in torrents:
            if t.name == torrent_name:
                logger.info("Found existing torrent: %s (hash: %s)", t.name, t.hash)
                return t

        logger.debug("No existing torrent found for: %s", torrent_name)
        return None
    except Exception as e:
        logger.exception("Error checking existing torrents: %s", e)
        return None

def connect_qbittorrent():
    """Establish connection to qBittorrent"""
    logger.info("Connecting to qBittorrent at %s", QB_HOST)

    client = qbittorrentapi.Client(host=QB_HOST, username=QB_USER, password=QB_PASS)

    try:
        client.auth_log_in()
        logger.info("Successfully connected to qBittorrent")

        # Get and log qBittorrent version
        version = client.app_version()
        logger.info("qBittorrent version: %s", version)

        return client
    except qbittorrentapi.LoginFailed as e:
        logger.error("qBittorrent login failed: %s", e)
    except qbittorrentapi.APIConnectionError as e:
        logger.error("Cannot connect to qBittorrent API: %s", e)
    except Exception as e:
        logger.exception("Unexpected error connecting to qBittorrent: %s", e)

    return None

def add_torrent_to_client(client, torrent_file, save_path, torrent_name):
    """Add torrent to qBittorrent with error handling"""
    logger.info("Adding torrent to qBittorrent: %s", torrent_name)
    logger.debug("Save path: %s", save_path)

    try:
        with open(torrent_file, 'rb') as f:
            result = client.torrents_add(
                torrent_files=[f],
                save_path=save_path,
                is_skip_checking=False,
                is_paused=False
            )

        if result == "Ok." or result == "Fails.":
            logger.info("Successfully added torrent: %s", torrent_name)
            return True
        else:
            logger.warning("Unexpected response when adding torrent: %s", result)
            return True  # Assume success if no error

    except qbittorrentapi.APIError as e:
        logger.error("qBittorrent API error adding torrent %s: %s", torrent_name, e)
    except Exception as e:
        logger.exception("Error adding torrent %s: %s", torrent_name, e)

    return False

def update_torrents():
    logger.info("=" * 60)
    logger.info("Starting torrent update process")
    logger.info("=" * 60)

    # Parse config
    try:
        torrents, _ = parse_config()
    except Exception as e:
        logger.critical("Failed to parse config, exiting")
        return

    if not torrents:
        logger.warning("No torrents found in config")
        return

    # Create torrent folder if not exists
    try:
        Path(TORRENT_FOLDER).mkdir(parents=True, exist_ok=True)
        logger.debug("Torrent folder ready: %s", TORRENT_FOLDER)
    except Exception as e:
        logger.exception("Cannot create torrent folder: %s", e)
        return

    # Connect to qBittorrent
    client = connect_qbittorrent()
    if not client:
        logger.error("Cannot proceed without qBittorrent connection")
        return

    updated = False

    for torrent_idx, torrent in enumerate(torrents, 1):
        logger.info("Processing torrent %d/%d: %s", torrent_idx, len(torrents), torrent['name'])

        if not torrent['need_updated']:
            logger.info("Skipping %s (auto-update disabled)", torrent['name'])
            continue

        # Check torrent file exists
        torrent_file_path = os.path.join(TORRENT_FOLDER, torrent['file_name'])
        if not torrent_file_path.endswith('.torrent'):
            torrent_file_path += '.torrent'

        if not os.path.exists(torrent_file_path):
            logger.warning("Torrent file not found: %s", torrent_file_path)
            continue

        # Check if torrent exists in qBittorrent
        existing = get_existing_torrent(client, torrent['name'])

        # Download new torrent
        logger.info("Downloading latest version for: %s", torrent['name'])
        new_torrent = download_torrent(torrent['url'], TORRENT_FOLDER, torrent['file_name'])

        if new_torrent:
            # Add to qBittorrent
            success = add_torrent_to_client(client, new_torrent, torrent['save_path'], torrent['name'])

            if success:
                # Handle existing torrent if needed
                if existing:
                    logger.info("Existing torrent found for %s, new version added", torrent['name'])
                    # Optionally delete old torrent
                    # client.torrents_delete(delete_files=False, torrent_hashes=existing.hash)
                    # logger.info("Old torrent deleted: %s", existing.hash)

                # Update timestamp
                old_date = torrent['last_updated']
                torrent['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                logger.info("Updated %s: last_updated changed from %s to %s",
                            torrent['name'], old_date, torrent['last_updated'])
        else:
            logger.error("Failed to download new torrent for: %s", torrent['name'])

    # Update config if changes were made
    if updated:
        logger.info("Changes detected, updating config file")
        update_config(torrents)
    else:
        logger.info("No updates performed")

    # Logout from qBittorrent
    try:
        client.auth_log_out()
        logger.debug("Logged out from qBittorrent")
    except:
        pass

    logger.info("=" * 60)
    logger.info("Torrent update process completed")
    logger.info("=" * 60)

def validate_url(url):
    """Check if URL is valid for automated download"""
    if url.startswith('blob:'):
        return False
    return True

def setup_cron():
    """Optional: Setup cron job automatically"""
    logger.info("Setting up cron job")

    try:
        from crontab import CronTab

        cron = CronTab(user=True)
        script_path = os.path.abspath(__file__)

        # Remove existing jobs
        cron.remove_all(comment='torrent_updater')
        logger.debug("Removed existing cron jobs")

        # Add new job based on config
        torrents, cron_schedule = parse_config()
        if cron_schedule:
            job = cron.new(command=f'python3 {script_path} >> {LOG_FILE} 2>&1',
                           comment='torrent_updater')
            job.setall(cron_schedule)
            cron.write()
            logger.info("Cron job set to: %s", cron_schedule)
        else:
            logger.warning("No cron schedule found in config")

    except Exception as e:
        logger.exception("Error setting up cron: %s", e)

def get_qbittorrent_torrents(filter=None, category=None, sort=None, limit=None):
    """
    Get list of torrents from qBittorrent with optional filters

    Parameters:
    - filter: Filter torrents (all, downloading, seeding, completed, paused, active, inactive)
    - category: Filter by category name
    - sort: Sort by field (name, size, progress, ratio, etc.)
    - limit: Limit number of results

    Returns:
    - List of torrents with detailed information or None if error
    """
    logger.info("Fetching torrents from qBittorrent")

    # Connect to qBittorrent
    client = connect_qbittorrent()
    if not client:
        logger.error("Cannot connect to qBittorrent to fetch torrents")
        return None

    try:
        # Get torrents with optional filters
        torrents_data = client.torrents_info(
            filter=filter,
            category=category,
            sort=sort,
            limit=limit
        )

        logger.info("Successfully fetched %d torrents from qBittorrent", len(torrents_data))

        # Format torrent information
        torrent_list = []
        for torrent in torrents_data:
            torrent_info = torrent.items()

            # torrent_info = {
            #     # Basic info
            #     'name': torrent.name,
            #     'hash': torrent.hash,
            #     'size': torrent.size,
            #     'size_human': format_size(torrent.size),
            #     'progress': torrent.progress * 100,  # Convert to percentage
            #     'state': torrent.state,
            #     'category': torrent.category,
            #     'save_path': torrent.save_path,
            #     'content_path': torrent.content_path,
            #
            #     # Transfer info
            #     'downloaded': torrent.downloaded,
            #     'uploaded': torrent.uploaded,
            #     'ratio': torrent.ratio,
            #     'download_speed': torrent.dlspeed,
            #     'upload_speed': torrent.upspeed,
            #     'eta': torrent.eta,
            #
            #     # Dates
            #     'added_on': datetime.fromtimestamp(torrent.added_on).strftime('%Y-%m-%d %H:%M:%S') if torrent.added_on else None,
            #     'completed_on': datetime.fromtimestamp(torrent.completion_on).strftime('%Y-%m-%d %H:%M:%S') if torrent.completion_on else None,
            #     'last_activity': datetime.fromtimestamp(torrent.last_activity).strftime('%Y-%m-%d %H:%M:%S') if torrent.last_activity else None,
            #
            #     # Connection info
            #     'num_seeds': torrent.num_seeds,
            #     'num_leechs': torrent.num_leechs,
            #     'num_complete': torrent.num_complete,
            #     'num_incomplete': torrent.num_incomplete,
            #
            #     # Additional
            #     'priority': torrent.priority,
            #     'sequence': torrent.prio first,
            # 'tracker': torrent.tracker,
            # 'tags': torrent.tags.split(',') if torrent.tags else [],
            #
            # # Magnet info
            # 'magnet_uri': torrent.magnet_uri if hasattr(torrent, 'magnet_uri') else None
            # }

            torrent_list.append(torrent_info)

            # Log detailed info for debugging
            logger.debug("Torrent: %s | Progress: %.1f%% | State: %s | Seeds: %d",
                         torrent.name, torrent.progress * 100, torrent.state, torrent.num_seeds)

        client.auth_log_out()
        return torrent_list

    except Exception as e:
        logger.exception("Error fetching torrents from qBittorrent: %s", e)
        try:
            client.auth_log_out()
        except:
            pass
        return None

def format_size(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"

def print_torrents_table(torrents, detailed=False):
    """Print torrents in a formatted table"""
    if not torrents:
        print("No torrents found")
        return

    if detailed:
        # Detailed view
        for i, t in enumerate(torrents, 1):
            print(f"\n{'='*60}")
            print(f"{i}. {t['name']}")
            print(f"{'='*60}")
            print(f"Hash: {t['hash']}")
            print(f"Size: {t['size_human']} ({t['size']} bytes)")
            print(f"Progress: {t['progress']:.1f}%")
            print(f"State: {t['state']}")
            print(f"Category: {t['category'] or 'None'}")
            print(f"Save Path: {t['save_path']}")
            print(f"Downloaded: {format_size(t['downloaded'])}")
            print(f"Uploaded: {format_size(t['uploaded'])}")
            print(f"Ratio: {t['ratio']:.2f}")
            print(f"Speed: ↓{format_size(t['download_speed'])}/s ↑{format_size(t['upload_speed'])}/s")
            print(f"ETA: {t['eta']} seconds" if t['eta'] > 0 else "ETA: N/A")
            print(f"Added: {t['added_on']}")
            if t['completed_on']:
                print(f"Completed: {t['completed_on']}")
            print(f"Seeds: {t['num_seeds']} (total: {t['num_complete']})")
            print(f"Peers: {t['num_leechs']} (total: {t['num_incomplete']})")
            if t['tags']:
                print(f"Tags: {', '.join(t['tags'])}")
    else:
        # Simple table view
        print("\n{:<4} {:<60} {:>10} {:>8} {:>12} {:>8}".format(
            "#", "Name", "Size", "Progress", "State", "Seeds"))
        print("-" * 110)

        for i, t in enumerate(torrents[:20], 1):  # Show first 20
            name = t['name'][:57] + "..." if len(t['name']) > 60 else t['name']
            print("{:<4} {:<60} {:>10} {:>7.1f}% {:>12} {:>8}".format(
                i, name, t['size_human'], t['progress'], t['state'][:12], t['num_seeds']))

        if len(torrents) > 20:
            print(f"\n... and {len(torrents) - 20} more torrents")

def search_torrents(torrents, search_term):
    """Search torrents by name or hash"""
    results = []
    search_term = search_term.lower()

    for t in torrents:
        if (search_term in t['name'].lower() or
                search_term in t['hash'].lower() or
                (t['category'] and search_term in t['category'].lower())):
            results.append(t)

    return results

def get_torrent_stats(torrents):
    """Get statistics about torrents"""
    if not torrents:
        return {}

    total_size = sum(t['size'] for t in torrents)
    total_downloaded = sum(t['downloaded'] for t in torrents)
    total_uploaded = sum(t['uploaded'] for t in torrents)

    downloading = [t for t in torrents if 'downloading' in t['state'].lower()]
    seeding = [t for t in torrents if 'seeding' in t['state'].lower() or 'uploading' in t['state'].lower()]
    paused = [t for t in torrents if 'paused' in t['state'].lower()]
    completed = [t for t in torrents if t['progress'] == 100]

    stats = {
        'total_count': len(torrents),
        'total_size': format_size(total_size),
        'total_downloaded': format_size(total_downloaded),
        'total_uploaded': format_size(total_uploaded),
        'ratio': total_uploaded / total_downloaded if total_downloaded > 0 else 0,
        'downloading_count': len(downloading),
        'seeding_count': len(seeding),
        'paused_count': len(paused),
        'completed_count': len(completed)
    }

    return stats


def test_get_torrents():
    """Test function to get and display torrents"""
    logger.info("Testing torrent list function")

    torrents = get_qbittorrent_torrents()

    if torrents:
        # # Print statistics
        # stats = get_torrent_stats(torrents)
        # print("\n" + "="*60)
        # print("TORRENT STATISTICS")
        # print("="*60)
        # for key, value in stats.items():
        #     print(f"{key}: {value}")
        #
        # # Print table
        # print_torrents_table(torrents, detailed=False)
        #
        # # Option: print detailed for first 3
        # # print_torrents_table(torrents[:3], detailed=True)
        #
        # # Example: search for specific torrents
        # # results = search_torrents(torrents, "frieren")
        # # if results:
        # #     print(f"\nFound {len(results)} matching torrents")
        # #     print_torrents_table(results)

        return torrents
    else:
        print("Failed to get torrents")
        return None

if __name__ == "__main__":
    import sys

    logger.info("Torrent Updater starting")
    logger.debug("Python version: %s", os.sys.version)
    logger.debug("Working directory: %s", os.getcwd())
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            test_get_torrents()
            sys.exit(0)
        elif sys.argv[1] == "--update":
            update_torrents()
            sys.exit(0)

    # Default behavior
    update_torrents()