document.addEventListener('DOMContentLoaded', () => {
    bindIndexEvents();
    loadTorrents();
    initRpcPage();
    initTrackersPage();
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
    const container = document.getElementById('torrents-container');
    if (!container) return;

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

async function loadRpcClients() {
    const container = document.getElementById('rpc-list-container');
    if (!container) return;

    clearMessages();
    container.innerHTML = '<p class="text-muted mb-0">Loading RPC clients...</p>';

    const result = await fetchJson('/api/rpc');
    if (!result.success) {
        container.innerHTML = `<p class="text-danger">${escapeHtml(result.error || 'Unable to load RPC clients')}</p>`;
        showMessage(result.error || 'Unable to load RPC clients', 'danger');
        return;
    }

    renderRpcClients(result.data || []);
}

function renderRpcClients(rpcList) {
    const container = document.getElementById('rpc-list-container');
    if (!container) return;

    if (!rpcList || rpcList.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No RPC clients configured.</p>';
        return;
    }

    let html = '<div class="table-responsive"><table class="table table-striped">';
    html += '<thead><tr><th>Alias</th><th>Status</th><th>Actions</th></tr></thead><tbody>';

    rpcList.forEach(rpc => {
        const alias = escapeHtml(rpc.alias);
        const status = escapeHtml(rpc.status || 'unknown');
        const isEnabled = rpc.status && rpc.status.toLowerCase() === 'enabled';
        html += `
            <tr>
                <td><strong>${alias}</strong></td>
                <td><strong>${status}</strong></td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" type="button" onclick='showRpcEditForm(${JSON.stringify(rpc.alias)})'>Configure</button>
                    ${isEnabled
                        ? `<button class="btn btn-sm btn-warning" type="button" onclick='disableRpc(${JSON.stringify(rpc.alias)})'>Disable</button>`
                        : `<button class="btn btn-sm btn-success" type="button" onclick='enableRpc(${JSON.stringify(rpc.alias)})'>Enable</button>`}
                </td>
            </tr>
        `;
    });
    html += '</tbody></table></div>';

    container.innerHTML = html;
}

async function enableRpc(alias) {
    if (!confirm(`Enable RPC client "${alias}"?`)) return;
    clearMessages();

    const result = await fetchJson(`/api/enable_rpc/${encodeURIComponent(alias)}`, {
        method: 'POST',
    });

    if (result.success) {
        showMessage(result.message || 'RPC enabled successfully');
        loadRpcClients();
    } else {
        showMessage(result.error || 'Failed to enable RPC', 'danger');
    }
}

async function disableRpc(alias) {
    if (!confirm(`Disable RPC client "${alias}"?`)) return;
    clearMessages();

    const result = await fetchJson(`/api/disable_rpc/${encodeURIComponent(alias)}`, {
        method: 'POST',
    });

    if (result.success) {
        showMessage(result.message || 'RPC disabled successfully');
        loadRpcClients();
    } else {
        showMessage(result.error || 'Failed to disable RPC', 'danger');
    }
}

function showRpcEditForm(alias) {
    const editForm = document.getElementById('rpc-edit-form');
    const aliasInput = document.getElementById('rpc_edit_alias');
    if (!editForm || !aliasInput) return;

    aliasInput.value = alias;
    document.getElementById('rpc_edit_url').value = '';
    document.getElementById('rpc_edit_host').value = '';
    document.getElementById('rpc_edit_port').value = '';
    document.getElementById('rpc_edit_username').value = '';
    document.getElementById('rpc_edit_password').value = '';
    editForm.style.display = 'block';
    editForm.scrollIntoView({ behavior: 'smooth' });
}

function hideRpcEditForm() {
    const editForm = document.getElementById('rpc-edit-form');
    if (editForm) {
        editForm.style.display = 'none';
    }
}

async function submitRpcConfiguration(event) {
    event.preventDefault();
    clearMessages();

    const payload = {
        action: 'configure',
        rpc_alias: document.getElementById('rpc_edit_alias').value,
        url: document.getElementById('rpc_edit_url').value,
        host: document.getElementById('rpc_edit_host').value,
        port: document.getElementById('rpc_edit_port').value,
        username: document.getElementById('rpc_edit_username').value,
        password: document.getElementById('rpc_edit_password').value,
    };

    const result = await fetchJson('/api/configure_rpc', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });

    if (result.success) {
        showMessage(result.message || 'RPC client configured successfully');
        hideRpcEditForm();
        loadRpcClients();
    } else {
        showMessage(result.error || 'Failed to configure RPC client', 'danger');
    }
}

function initRpcPage() {
    const page = document.getElementById('rpc-page');
    if (!page) return;

    const form = document.getElementById('configure-rpc-form');
    if (form) {
        form.addEventListener('submit', submitRpcConfiguration);
    }

    loadRpcClients();
}

async function loadTrackers() {
    const container = document.getElementById('tracker-list-container');
    if (!container) return;

    clearMessages();
    container.innerHTML = '<p class="text-muted mb-0">Loading trackers...</p>';

    const result = await fetchJson('/api/trackers');
    if (!result.success) {
        container.innerHTML = `<p class="text-danger">${escapeHtml(result.error || 'Unable to load trackers')}</p>`;
        showMessage(result.error || 'Unable to load trackers', 'danger');
        return;
    }

    renderTrackers(result.data || []);
}

function renderTrackers(trackers) {
    const container = document.getElementById('tracker-list-container');
    if (!container) return;

    if (!trackers || trackers.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No trackers found. Trackers are defined in torrt configuration.</p>';
        return;
    }

    let html = '<div class="table-responsive"><table class="table table-striped">';
    html += '<thead><tr><th>Tracker Alias</th><th>Actions</th></tr></thead><tbody>';

    trackers.forEach(tracker => {
        const alias = escapeHtml(tracker.alias);
        html += `
            <tr>
                <td><strong>${alias}</strong></td>
                <td>
                    <button class="btn btn-sm btn-primary" type="button" onclick='showTrackerEditForm(${JSON.stringify(tracker.alias)})'>Configure</button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function showTrackerEditForm(alias) {
    const editForm = document.getElementById('tracker-edit-form');
    const aliasInput = document.getElementById('tracker_edit_alias');
    if (!editForm || !aliasInput) return;

    aliasInput.value = alias;
    document.getElementById('tracker_edit_username').value = '';
    document.getElementById('tracker_edit_password').value = '';
    editForm.style.display = 'block';
    editForm.scrollIntoView({ behavior: 'smooth' });
}

function hideTrackerEditForm() {
    const editForm = document.getElementById('tracker-edit-form');
    if (editForm) {
        editForm.style.display = 'none';
    }
}

async function submitTrackerConfiguration(event) {
    event.preventDefault();
    clearMessages();

    const payload = {
        tracker_alias: document.getElementById('tracker_edit_alias').value,
        username: document.getElementById('tracker_edit_username').value,
        password: document.getElementById('tracker_edit_password').value,
    };

    const result = await fetchJson('/api/configure_tracker', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });

    if (result.success) {
        const output = result.output || result.message;
        if (output && /ERROR:/i.test(output)) {
            showMessage(output, 'danger');
        } else if (output && /WARNING:/i.test(output)) {
            showMessage(output, 'warning');
        } else {
            showMessage(result.message || 'Tracker configured successfully');
        }
        hideTrackerEditForm();
        loadTrackers();
    } else {
        showMessage(result.error || result.output || 'Failed to configure tracker', 'danger');
    }
}

function initTrackersPage() {
    const page = document.getElementById('trackers-page');
    if (!page) return;

    const form = document.getElementById('configure-tracker-form');
    if (form) {
        form.addEventListener('submit', submitTrackerConfiguration);
    }

    loadTrackers();
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
