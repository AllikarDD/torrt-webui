# torrent_updater.py
import requests
import qbittorrentapi
import hashlib
import bencoder
import time
import logging
from datetime import datetime
from database import Database
from config import Config

logger = logging.getLogger(__name__)

class TorrentUpdater:
    def __init__(self):
        self.db = Database()
        self.qb = None
        self.connect_qbittorrent()

    def connect_qbittorrent(self):
        """Подключение к qBittorrent"""
        try:
            self.qb = qbittorrentapi.Client(
                host=Config.QB_URL,
                username=Config.QB_USERNAME,
                password=Config.QB_PASSWORD
            )
            self.qb.auth_log_in()
            logger.info("Подключение к qBittorrent успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к qBittorrent: {e}")
            return False

    def get_torrent_info(self, topic_id):
        """Получение информации о торренте с RuTracker"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': f'bb_session={Config.RUTRACKER_COOKIE}'
        }

        # Получаем название темы
        topic_url = f'https://rutracker.org/forum/viewtopic.php?t={topic_id}'
        download_url = f'https://rutracker.org/forum/dl.php?t={topic_id}'

        try:
            session = requests.Session()
            session.headers.update(headers)

            # Получаем название темы
            topic_response = session.get(topic_url)
            topic_response.raise_for_status()

            # Парсим название (упрощенно)
            import re
            title_match = re.search(r'<title>(.+?)</title>', topic_response.text)
            title = title_match.group(1) if title_match else f"Topic {topic_id}"
            title = title.replace(' - RuTracker.org', '').strip()

            # Скачиваем торрент
            download_response = session.get(download_url, stream=True)
            download_response.raise_for_status()

            torrent_content = download_response.content

            # Декодируем торрент для получения информации
            try:
                decoded = bencoder.decode(torrent_content)
                info_hash = hashlib.sha1(bencoder.encode(decoded[b'info'])).hexdigest().upper()

                # Получаем список файлов
                files = []
                if b'files' in decoded[b'info']:
                    for f in decoded[b'info'][b'files']:
                        path = b'/'.join(f[b'path']).decode('utf-8', errors='ignore')
                        size = f[b'length']
                        files.append({'path': path, 'size': size})
                else:
                    name = decoded[b'info'][b'name'].decode('utf-8', errors='ignore')
                    size = decoded[b'info'][b'length']
                    files.append({'path': name, 'size': size})

                return {
                    'topic_id': topic_id,
                    'title': title,
                    'hash': info_hash,
                    'content': torrent_content,
                    'files': files,
                    'file_count': len(files)
                }

            except Exception as e:
                logger.error(f"Ошибка декодирования торрента: {e}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при получении торрента {topic_id}: {e}")
            return None

    def update_torrent(self, topic_id, torrent_info):
        """Обновление торрента в qBittorrent"""
        topic = self.db.get_topic(topic_id)
        if not topic:
            logger.error(f"Топик {topic_id} не найден в БД")
            return False

        try:
            # Ищем торрент в qBittorrent
            torrents = self.qb.torrents_info()
            existing_torrent = None
            for t in torrents:
                if t['hash'].upper() == torrent_info['hash'].upper():
                    existing_torrent = t
                    break

            if existing_torrent:
                logger.info(f"Торрент уже существует: {existing_torrent['name']}")

                # Проверяем, нужно ли обновлять
                if existing_torrent['hash'].upper() == torrent_info['hash'].upper():
                    logger.info("Хэши совпадают, обновление не требуется")
                    return True

            # Сохраняем путь
            save_path = topic['save_path']

            # Удаляем старый торрент если он есть
            if existing_torrent:
                self.qb.torrents_delete(
                    delete_files=False,
                    torrent_hashes=existing_torrent['hash']
                )
                logger.info("Старый торрент удален из клиента")

            # Добавляем новый торрент
            self.qb.torrents_add(
                torrent_files=torrent_info['content'],
                save_path=save_path,
                is_paused=True
            )
            logger.info("Новый торрент добавлен")

            # Ждем появления торрента
            time.sleep(2)

            # Запускаем проверку
            torrents = self.qb.torrents_info()
            for t in torrents:
                if t['hash'].upper() == torrent_info['hash'].upper():
                    self.qb.torrents_recheck(torrent_hashes=t['hash'])
                    self.qb.torrents_resume(torrent_hashes=t['hash'])
                    logger.info(f"Запущена проверка для {t['name']}")
                    break

            # Обновляем информацию в БД
            self.db.update_topic(
                topic_id,
                last_hash=torrent_info['hash'],
                last_update=datetime.now()
            )

            self.db.add_history(topic_id, 'update', 'Торрент обновлен')

            return True

        except Exception as e:
            logger.error(f"Ошибка при обновлении торрента: {e}")
            self.db.add_history(topic_id, 'error', str(e))
            return False

    def check_all_topics(self):
        """Проверка всех активных топиков"""
        topics = self.db.get_topics()
        results = []

        for topic in topics:
            logger.info(f"Проверка топика {topic['topic_id']}: {topic['title']}")

            # Получаем актуальную информацию
            torrent_info = self.get_torrent_info(topic['topic_id'])

            if not torrent_info:
                results.append({
                    'topic_id': topic['topic_id'],
                    'title': topic['title'],
                    'status': 'error',
                    'message': 'Не удалось получить информацию'
                })
                continue

            # Проверяем изменился ли хэш
            if torrent_info['hash'] != topic.get('last_hash'):
                logger.info(f"Обнаружено изменение в топике {topic['topic_id']}")

                # Обновляем торрент
                success = self.update_torrent(topic['topic_id'], torrent_info)

                results.append({
                    'topic_id': topic['topic_id'],
                    'title': topic['title'],
                    'status': 'updated' if success else 'failed',
                    'message': 'Торрент обновлен' if success else 'Ошибка обновления'
                })
            else:
                results.append({
                    'topic_id': topic['topic_id'],
                    'title': topic['title'],
                    'status': 'unchanged',
                    'message': 'Изменений нет'
                })

            # Обновляем время проверки
            self.db.update_topic(topic['topic_id'], last_check=datetime.now())

        return results