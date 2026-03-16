# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import Database
from torrent_updater import TorrentUpdater
from config import Config
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Инициализация компонентов
db = Database()
updater = TorrentUpdater()

@app.route('/')
def index():
    """Главная страница"""
    topics = db.get_topics()
    history = db.get_history(50)
    return render_template('index.html', topics=topics, history=history)

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """API: Получить все топики"""
    topics = db.get_topics()
    return jsonify(topics)

@app.route('/api/topics', methods=['POST'])
def add_topic():
    """API: Добавить новый топик"""
    data = request.json

    topic_id = data.get('topic_id')
    save_path = data.get('save_path')
    category = data.get('category', '')

    if not topic_id or not save_path:
        return jsonify({'error': 'topic_id и save_path обязательны'}), 400

    try:
        topic_id = int(topic_id)
    except ValueError:
        return jsonify({'error': 'topic_id должен быть числом'}), 400

    # Получаем информацию о торренте
    torrent_info = updater.get_torrent_info(topic_id)

    if not torrent_info:
        return jsonify({'error': 'Не удалось получить информацию о торренте'}), 400

    # Добавляем в БД
    success = db.add_topic(
        topic_id=topic_id,
        title=torrent_info['title'],
        save_path=save_path,
        category=category
    )

    if not success:
        return jsonify({'error': 'Топик уже существует'}), 400

    # Добавляем в qBittorrent
    updater.update_torrent(topic_id, torrent_info)

    return jsonify({'success': True, 'topic': torrent_info})

@app.route('/api/topics/<int:topic_id>', methods=['DELETE'])
def delete_topic(topic_id):
    """API: Удалить топик"""
    db.delete_topic(topic_id)
    return jsonify({'success': True})

@app.route('/api/topics/<int:topic_id>/update', methods=['POST'])
def update_topic(topic_id):
    """API: Принудительно обновить топик"""
    torrent_info = updater.get_torrent_info(topic_id)

    if not torrent_info:
        return jsonify({'error': 'Не удалось получить информацию о торренте'}), 400

    success = updater.update_torrent(topic_id, torrent_info)

    return jsonify({
        'success': success,
        'topic': torrent_info
    })

@app.route('/api/check-all', methods=['POST'])
def check_all():
    """API: Проверить все топики"""
    results = updater.check_all_topics()
    return jsonify({'results': results})

@app.route('/api/history', methods=['GET'])
def get_history():
    """API: Получить историю"""
    limit = request.args.get('limit', 100, type=int)
    history = db.get_history(limit)
    return jsonify(history)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """API: Получить настройки"""
    return jsonify({
        'qb_url': Config.QB_URL,
        'qb_connected': updater.qb is not None
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)