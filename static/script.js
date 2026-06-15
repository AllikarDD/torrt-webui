document.addEventListener('DOMContentLoaded', () => {
    bindIndexEvents();
    loadTorrents();
});

function bindIndexEvents() {
    const addForm = document.getElementById('add-torrent-form');
    if (addForm) {
        addForm.addEventListener('submit', handleAddTorrent);
    }

    const removeForm = document.getElementById('remove-torrent-form');
    if (removeForm) {
        removeForm.addEventListener('submit', handleRemoveTorrent);
    }

    const registerForm = document.getElementById('register-torrent-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegisterTorrent);
    }

    const unregisterForm = document.getElementById('unregister-torrent-form');
    if (unregisterForm) {
        unregisterForm.addEventListener('submit', handleUnregisterTorrent);
    }

    const walkButton = document.getElementById('walk-button');
    if (walkButton) {
        walkButton.addEventListener('click', handleWalk);
    }

    const refreshButton = document.getElementById('refresh-torrents');
    if (refreshButton) {
        refreshButton.addEventListener('click', loadTorrents);
    }
}

async function fetchJson(path, options = {}) {
    const response = await fetch(path, options);
    const contentType = response.headers.get('content-type') || '';
    let payload = {success: false, error: 'Invalid server response'};

    if (contentType.includes('application/json')) {
        payload = await response.json();
    }

    if (!response.ok) {
        payload.success = false;
        payload.error = payload.error || `HTTP ${response.status}`;
    }

    return payload;
}

function showMessage(message, category = 'success') {
    const container = document.getElementById('page-messages');
    if (!container) return;
    container.innerHTML = `
        <div class="alert alert-${category} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
}

function clearMessages() {
    const container = document.getElementById('page-messages');
    if (container) {
        container.innerHTML = '';
    }
}

async function loadTorrents() {
    const result = await fetchJson('/api/torrents');
    if (!result.success) {
        showMessage(result.error || 'Unable to load torrents', 'danger');
        return;
    }
    renderTorrents(result.data || []);
}

function renderTorrents(torrents) {
    const container = document.getElementById('torrents-container');
    const count = document.getElementById('torrent-count');
    if (!container || !count) return;

    if (!torrents || torrents.length === 0) {
        container.innerHTML = '<p class="text-muted">No torrents registered. Add one below!</p>';
        count.textContent = '0';
        return;
    }

    let html = '<div class="table-responsive"><table class="table table-sm table-striped">';
    html += '<thead><tr><th>Hash</th><th>Name</th><th>Tracker</th></tr></thead><tbody>';

    torrents.forEach(torrent => {
        html += `
            <tr>
                <td class="torrent-hash">${escapeHtml(torrent.hash)}</td>
                <td>${escapeHtml(torrent.name || 'N/A')}</td>
                <td>${escapeHtml(torrent.tracker || 'N/A')}</td>
            </tr>
        `;
    });
    html += '</tbody></table></div>';

    container.innerHTML = html;
    count.textContent = torrents.length.toString();
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

async function handleAddTorrent(event) {
    event.preventDefault();
    clearMessages();

    const payload = {
        url: document.getElementById('add-url').value,
        download_path: document.getElementById('add-download-path').value,
        content_layout: document.getElementById('add-content-layout').value,
    };

    const result = await fetchJson('/api/add_torrent', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });

    if (result.success) {
        showMessage(result.message || 'Torrent added successfully');
        document.getElementById('add-torrent-form').reset();
        loadTorrents();
    } else {
        showMessage(result.error || 'Failed to add torrent', 'danger');
    }
}

async function handleRemoveTorrent(event) {
    event.preventDefault();
    clearMessages();

    const payload = {
        torrent_hash: document.getElementById('remove-torrent-hash').value,
    };

    const result = await fetchJson('/api/remove_torrent', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });

    if (result.success) {
        showMessage(result.message || 'Torrent removed successfully');
        document.getElementById('remove-torrent-form').reset();
        loadTorrents();
    } else {
        showMessage(result.error || 'Failed to remove torrent', 'danger');
    }
}

async function handleRegisterTorrent(event) {
    event.preventDefault();
    clearMessages();

    const payload = {
        torrent_hash: document.getElementById('register-torrent-hash').value,
    };

    const result = await fetchJson('/api/register_torrent', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });

    if (result.success) {
        showMessage(result.message || 'Torrent registered successfully');
        document.getElementById('register-torrent-form').reset();
        loadTorrents();
    } else {
        showMessage(result.error || 'Failed to register torrent', 'danger');
    }
}

async function handleUnregisterTorrent(event) {
    event.preventDefault();
    clearMessages();

    const payload = {
        torrent_hash: document.getElementById('unregister-torrent-hash').value,
    };

    const result = await fetchJson('/api/unregister_torrent', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });

    if (result.success) {
        showMessage(result.message || 'Torrent unregistered successfully');
        document.getElementById('unregister-torrent-form').reset();
        loadTorrents();
    } else {
        showMessage(result.error || 'Failed to unregister torrent', 'danger');
    }
}

async function handleWalk() {
    clearMessages();
    const walkResult = document.getElementById('walk-result');
    if (walkResult) {
        walkResult.innerHTML = '<div class="text-muted">Running walk...</div>';
    }

    const result = await fetchJson('/api/walk', {
        method: 'POST',
    });

    if (result.success) {
        showMessage(result.message || 'Walk completed successfully');
        if (walkResult) {
            walkResult.innerHTML = `<div class="alert alert-success">${escapeHtml(result.output || result.message || '')}</div>`;
        }
        loadTorrents();
    } else {
        showMessage(result.error || 'Failed to run walk', 'danger');
        if (walkResult) {
            walkResult.innerHTML = `<div class="alert alert-danger">${escapeHtml(result.output || result.error || '')}</div>`;
        }
    }
}
