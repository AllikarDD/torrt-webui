// static/script.js

// Загрузка данных при старте
document.addEventListener('DOMContentLoaded', function() {
    loadTopics();
    loadHistory();
    checkQBittorrentStatus();

    // Обработчик формы добавления
    document.getElementById('add-topic-form').addEventListener('submit', addTopic);

    // Обработчик кнопки проверки всех
    document.getElementById('check-all-btn').addEventListener('click', checkAllTopics);

    // Модальное окно
    setupModal();
});

// Загрузка топиков
async function loadTopics() {
    try {
        const response = await fetch('/api/topics');
        const topics = await response.json();
        renderTopics(topics);
    } catch (error) {
        console.error('Ошибка загрузки топиков:', error);
        showError('Не удалось загрузить список топиков');
    }
}

// Загрузка истории
async function loadHistory() {
    try {
        const response = await fetch('/api/history?limit=50');
        const history = await response.json();
        renderHistory(history);
    } catch (error) {
        console.error('Ошибка загрузки истории:', error);
    }
}

// Проверка статуса qBittorrent
async function checkQBittorrentStatus() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();

        const statusEl = document.getElementById('qb-status');
        if (settings.qb_connected) {
            statusEl.className = 'status online';
            statusEl.innerHTML = '⚡ qBittorrent: Подключено';
        } else {
            statusEl.className = 'status offline';
            statusEl.innerHTML = '⚡ qBittorrent: Отключено';
        }
    } catch (error) {
        console.error('Ошибка проверки статуса:', error);
    }
}

// Добавление топика
async function addTopic(event) {
    event.preventDefault();

    const formData = {
        topic_id: document.getElementById('topic_id').value,
        save_path: document.getElementById('save_path').value,
        category: document.getElementById('category').value
    };

    const submitBtn = event.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '⏳ Добавление...';
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/topics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok) {
            // Очищаем форму
            document.getElementById('topic_id').value = '';
            document.getElementById('save_path').value = '';
            document.getElementById('category').value = '';

            // Обновляем списки
            loadTopics();
            loadHistory();

            showMessage('Топик успешно добавлен', 'success');
        } else {
            showError(result.error || 'Ошибка при добавлении');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showError('Ошибка при добавлении топика');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Удаление топика
async function deleteTopic(topicId) {
    if (!confirm('Вы уверены, что хотите удалить этот топик?')) {
        return;
    }

    try {
        const response = await fetch(`/api/topics/${topicId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadTopics();
            loadHistory();
            showMessage('Топик удален', 'success');
        } else {
            showError('Ошибка при удалении');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showError('Ошибка при удалении топика');
    }
}

// Обновление топика
async function updateTopic(topicId) {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳...';
    btn.disabled = true;

    try {
        const response = await fetch(`/api/topics/${topicId}/update`, {
            method: 'POST'
        });

        const result = await response.json();

        if (response.ok && result.success) {
            loadTopics();
            loadHistory();
            showMessage('Топик обновлен', 'success');
        } else {
            showError('Ошибка при обновлении');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showError('Ошибка при обновлении топика');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Проверка всех топиков
async function checkAllTopics() {
    const btn = document.getElementById('check-all-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ Проверка...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/check-all', {
            method: 'POST'
        });

        const result = await response.json();

        // Показываем результаты
        const updated = result.results.filter(r => r.status === 'updated').length;
        const unchanged = result.results.filter(r => r.status === 'unchanged').length;
        const failed = result.results.filter(r => r.status === 'failed').length;

        showMessage(
            `Проверка завершена: обновлено ${updated}, без изменений ${unchanged}, ошибок ${failed}`,
            updated > 0 ? 'success' : 'info'
        );

        // Обновляем списки
        loadTopics();
        loadHistory();
    } catch (error) {
        console.error('Ошибка:', error);
        showError('Ошибка при проверке');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Показать детали топика
async function showTopicDetails(topicId) {
    try {
        const response = await fetch(`/api/topics/${topicId}/update`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.topic) {
            const modal = document.getElementById('topic-modal');
            const modalContent = document.getElementById('modal-content');

            let filesHtml = '';
            if (result.topic.files) {
                filesHtml = '<h3>Файлы:</h3><ul>';
                result.topic.files.forEach(file => {
                    const size = (file.size / 1024 / 1024).toFixed(2);
                    filesHtml += `<li>${file.path} (${size} MB)</li>`;
                });
                filesHtml += '</ul>';
            }

            modalContent.innerHTML = `
                <h2>${result.topic.title}</h2>
                <p><strong>ID:</strong> ${result.topic.topic_id}</p>
                <p><strong>Хэш:</strong> <code>${result.topic.hash}</code></p>
                <p><strong>Файлов:</strong> ${result.topic.file_count}</p>
                ${filesHtml}
            `;

            modal.style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

// Отрисовка топиков
function renderTopics(topics) {
    const container = document.getElementById('topics-container');

    if (topics.length === 0) {
        container.innerHTML = '<div class="loading">Нет отслеживаемых топиков</div>';
        return;
    }

    let html = '<table class="topics-table">';
    html += `
        <thead>
            <tr>
                <th>Название</th>
                <th>ID</th>
                <th>Путь сохранения</th>
                <th>Последнее обновление</th>
                <th>Последняя проверка</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
    `;

    topics.forEach(topic => {
        const lastUpdate = topic.last_update ? new Date(topic.last_update).toLocaleString() : 'никогда';
        const lastCheck = topic.last_check ? new Date(topic.last_check).toLocaleString() : 'никогда';

        html += `
            <tr>
                <td class="topic-title">${topic.title}</td>
                <td class="topic-id">${topic.topic_id}</td>
                <td class="topic-path" title="${topic.save_path}">${topic.save_path}</td>
                <td class="topic-date">${lastUpdate}</td>
                <td class="topic-date">${lastCheck}</td>
                <td class="topic-actions">
                    <button class="btn btn-small btn-primary" onclick="updateTopic(${topic.topic_id})">
                        🔄
                    </button>
                    <button class="btn btn-small btn-warning" onclick="showTopicDetails(${topic.topic_id})">
                        📋
                    </button>
                    <button class="btn btn-small btn-danger" onclick="deleteTopic(${topic.topic_id})">
                        🗑️
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Отрисовка истории
function renderHistory(history) {
    const container = document.getElementById('history-container');

    if (history.length === 0) {
        container.innerHTML = '<div class="loading">История пуста</div>';
        return;
    }

    let html = '';

    history.forEach(item => {
        const time = new Date(item.created_at).toLocaleString();
        let actionClass = '';

        switch(item.action) {
            case 'add': actionClass = 'add'; break;
            case 'update': actionClass = 'update'; break;
            case 'delete': actionClass = 'delete'; break;
            case 'error': actionClass = 'error'; break;
        }

        html += `
            <div class="history-item">
                <span class="history-time">${time}</span>
                <span class="history-action ${actionClass}">${item.action}</span>
                <span class="history-details">
                    <strong>${item.title}</strong> — ${item.details}
                </span>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Настройка модального окна
function setupModal() {
    const modal = document.getElementById('topic-modal');
    const closeBtn = document.querySelector('.close');

    closeBtn.onclick = function() {
        modal.style.display = 'none';
    };

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };
}

// Утилиты для сообщений
function showMessage(message, type = 'info') {
    // Можно добавить красивые тосты позже
    console.log(`[${type}] ${message}`);
    alert(message);
}

function showError(message) {
    console.error(message);
    alert('Ошибка: ' + message);
}