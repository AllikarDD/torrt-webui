# config.py
import os

class Config:
    # qBittorrent settings
    QB_URL = os.getenv('QB_URL', 'http://192.168.1.116:8081')
    QB_USERNAME = os.getenv('QB_USERNAME', 'admin')
    QB_PASSWORD = os.getenv('QB_PASSWORD', 'reivf289gbegbe')

    # RuTracker settings
    RUTRACKER_COOKIE = os.getenv('RUTRACKER_COOKIE', 'bb_session=0-42312143-LwN8oevcJtoa9PKBtVJ2')

    # Database
    DATABASE = 'torrents.db'

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = True