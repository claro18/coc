let tg = null;
let userId = null;
let searchTimer = null;
let currentModalUserId = null;
let maintenanceState = { enabled: false, message: '' };

function initTelegram() {
    if (window.Telegram && window.Telegram.WebApp) {
        tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        return true;
    }
    return false;
}

async function verifyAccess() {
    if (!tg) {
        document.getElementById('loading').innerHTML = '<div class=\"text-center fade-in\"><div class=\"text-4xl mb-4\">🔒</div><div class=\"text-gray-300 font-medium\">Please open this from the Telegram bot.</div></div>';
        return false;
    }
    try {
        const initData = tg.initData;
        if (!initData) {
            document.getElementById('loading').innerHTML = '<div class=\"text-center fade-in\"><div class=\"text-4xl mb-4\">⚠️</div><div class=\"text-gray-300 font-medium\">No init data available.</div></div>';
            return false;
        }
        const resp = await fetch('/api/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ initData }) });
        if (!resp.ok) {
            document.getElementById('loading').innerHTML = '<div class=\"text-center fade-in\"><div class=\"text-4xl mb-4\">🚫</div><div class=\"text-gray-300 font-medium\">Access Denied</div></div>';
            return false;
        }
        const data = await resp.json();
        userId = data.user_id;
        document.getElementById('loading').style.display = 'none';
        document.getElementById('sidebar').style.display = 'flex';
        document.getElementById('mainContent').style.display = 'block';
        return true;
    } catch (e) {
        document.getElementById('loading').innerHTML = '<div class=\"text-center fade-in\"><div class=\"text-4xl mb-4\">💥</div><div class=\"text-gray-300 font-medium\">Verification Failed</div></div>';
        return false;
    }
}

function removeSkeletons() { document.querySelectorAll('.skeleton').forEach(el => el.classList.remove('skeleton')); }

function showToast(msg, type) {
    const el = document.getElementById('toast');
    el.innerHTML = msg;
    el.style.borderLeft = '3px solid ' + (type === 'error' ? '#ef4444' : '#22c55e');
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 4000);
}

function switchPage(page) {
    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    document.querySelector('.sidebar-link[data-page=\"' + page + '\"]').classList.add('active');
}

document.querySelectorAll('.sidebar-link').forEach(link => {
    link.addEventListener('click', () => switchPage(link.dataset.page));
});

async function loadMetrics() {
    try {
        const resp = await fetch('/api/metrics');
        const data = await resp.json();
        document.getElementById('totalUsers').textContent = data.total_users;
        document.getElementById('bannedUsers').textContent = data.banned_users;
        document.getElementById('activeUpgrades').textContent = data.active_upgrades;
        document.getElementById('totalUpgrades').textContent = data.total_upgrades;
        removeSkeletons();
    } catch (e) { console.error(e); }
}

async function loadUsers() {
    try {
        const resp = await fetch('/api/users');
        const data = await resp.json();
        const tbody = document.getElementById('userTableBody');
        const footer = document.getElementById('userTableFooter');
        if (data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan=\"7\" class=\"text-center py-10 text-gray-600\">No users registered yet.</td></tr>';
            footer.textContent = '0 users';
            return;
        }
        footer.textContent = data.users.length + ' user(s) (last 100)';
        window._allUsers = data.users;
        renderUsers(data.users);
    } catch (e) { console.error(e); }
}

function renderUsers(users) {
    const tbody = document.getElementById('userTableBody');
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan=\"7\" class=\"text-center py-10 text-gray-600\">No matching users.</td></tr>';
        return;
    }
    tbody.innerHTML = users.map(u => {
        const thIcon = u.town_hall >= 14 ? '👑' : u.town_hall >= 11 ? '🔥' : u.town_hall >= 8 ? '⚔️' : u.town_hall >= 5 ? '🛡️' : '🏠';
        const banBadge = u.is_banned ? '<span class=\"text-red-400 text-xs font-semibold\">🚫 Banned</span>' : '<span class=\"text-green-400 text-xs font-semibold\">✅ Active</span>';
        const banAction = u.is_banned
            ? '<button onclick=\"unbanUser(' + u.id + ')\" class=\"text-xs text-green-400 hover:text-green-300 font-semibold\">Unban</button>'
            : '<button onclick=\"showUserDetail(' + u.id + ')\" class=\"text-xs text-blue-400 hover:text-blue-300 font-semibold\">Details</button>';
        return '<tr class=\"user-row border-b border-white/5 cursor-pointer\" onclick=\"showUserDetail(' + u.id + ')\">' +
            '<td class=\"py-2.5 px-4 tag-text\">' + u.id + '</td>' +
            '<td class=\"py-2.5 px-4\"><span class=\"font-medium\">' + (u.username || '<span class=\"text-gray-600\">—</span>') + '</span></td>' +
            '<td class=\"py-2.5 px-4 tag-text hidden sm:table-cell\">' + (u.tag || '<span class=\"text-gray-600\">—</span>') + '</td>' +
            '<td class=\"py-2.5 px-4\"><span class=\"badge-th\">' + thIcon + ' ' + (u.town_hall || '?') + '</span></td>' +
            '<td class=\"py-2.5 px-4 text-gray-400 text-xs hidden md:table-cell\">' + (u.last_seen || '<span class=\"text-gray-600\">—</span>') + '</td>' +
            '<td class=\"py-2.5 px-4 text-center\">' + banBadge + '</td>' +
            '<td class=\"py-2.5 px-4 text-center\" onclick=\"event.stopPropagation()\">' + banAction + '</td></tr>';
    }).join('');
}

function debouncedSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
        const q = document.getElementById('searchInput').value.trim();
        if (!q) { renderUsers(window._allUsers || []); return; }
        try {
            const resp = await fetch('/api/users/search?q=' + encodeURIComponent(q));
            const data = await resp.json();
            renderUsers(data.users);
        } catch (e) {}
    }, 250);
}

async function showUserDetail(uid) {
    currentModalUserId = uid;
    try {
        const resp = await fetch('/api/users/' + uid);
        const u = await resp.json();
        document.getElementById('modalTitle').textContent = u.username || 'User #' + u.id;
        document.getElementById('modalBody').innerHTML =
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">User ID</span><span class=\"tag-text\">' + u.id + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Username</span><span>' + (u.username || '<span class=\"text-gray-600\">—</span>') + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Tag</span><span>' + (u.tag || '<span class=\"text-gray-600\">—</span>') + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Town Hall</span><span class=\"badge-th\">🏰 ' + (u.town_hall || 0) + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Builders</span><span>' + u.total_builders + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Buildings (snapshot)</span><span>' + u.buildings_count + '</span></div>' +
            '<div class=\"border-t border-white/5 my-2\"></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Total Upgrades</span><span class=\"font-semibold text-purple-400\">' + u.total_upgrades + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Completed</span><span class=\"font-semibold text-green-400\">' + u.completed_upgrades + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Active</span><span class=\"font-semibold text-yellow-400\">' + u.active_upgrades + '</span></div>' +
            '<div class=\"border-t border-white/5 my-2\"></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Joined</span><span class=\"text-xs\">' + u.created_at + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Last Seen</span><span class=\"text-xs\">' + (u.last_seen || '<span class=\"text-gray-600\">—</span>') + '</span></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Last Sync</span><span class=\"text-xs\">' + u.last_sync + '</span></div>' +
            '<div class=\"border-t border-white/5 my-2\"></div>' +
            '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Status</span><span>' + (u.is_banned ? '<span class=\"text-red-400 font-semibold\">🚫 Banned</span>' : '<span class=\"text-green-400 font-semibold\">✅ Active</span>') + '</span></div>' +
            (u.ban_reason ? '<div class=\"flex justify-between\"><span class=\"text-gray-500\">Ban Reason</span><span class=\"text-red-400\">' + u.ban_reason + '</span></div>' : '');
        document.getElementById('modalBanBtn').style.display = u.is_banned ? 'none' : '';
        document.getElementById('modalUnbanBtn').style.display = u.is_banned ? '' : 'none';
        document.getElementById('userModal').classList.add('open');
    } catch (e) { showToast('Error loading user details', 'error'); }
}

function closeModal() { document.getElementById('userModal').classList.remove('open'); currentModalUserId = null; }

function modalBan() { banUser(currentModalUserId); }
function modalUnban() { unbanUser(currentModalUserId); }

async function banUser(uid) {
    const reason = prompt('Ban reason (optional):');
    if (reason === null) return;
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (tg) headers['x-init-data'] = tg.initData;
        await fetch('/api/users/' + uid + '/ban', { method: 'POST', headers, body: JSON.stringify({ reason: reason || '' }) });
        showToast('User banned successfully');
        closeModal();
        loadUsers();
    } catch (e) { showToast('Failed to ban user', 'error'); }
}

async function unbanUser(uid) {
    try {
        const headers = {};
        if (tg) headers['x-init-data'] = tg.initData;
        await fetch('/api/users/' + uid + '/unban', { method: 'POST', headers });
        showToast('User unbanned successfully');
        closeModal();
        loadUsers();
    } catch (e) { showToast('Failed to unban user', 'error'); }
}

function updatePreview() {
    const text = document.getElementById('broadcastText').value;
    document.getElementById('broadcastPreview').innerHTML = text || '<span class=\"text-gray-600\">Message preview will appear here...</span>';
}

async function sendBroadcast() {
    const text = document.getElementById('broadcastText').value.trim();
    if (!text) { showToast('Please write a message first', 'error'); return; }
    const btn = document.getElementById('sendBtn');
    const status = document.getElementById('broadcastStatus');
    btn.disabled = true;
    status.textContent = 'Queuing...';
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (tg) headers['x-init-data'] = tg.initData;
        const resp = await fetch('/api/broadcast', { method: 'POST', headers, body: JSON.stringify({ text }) });
        const data = await resp.json();
        if (data.ok) {
            showToast('Broadcast queued successfully!');
            status.textContent = 'Sent! The bot will deliver in the background.';
            document.getElementById('broadcastText').value = '';
            document.getElementById('broadcastPreview').innerHTML = '<span class=\"text-gray-600\">Message preview will appear here...</span>';
            loadBroadcastLog();
        } else {
            showToast('Failed to queue broadcast', 'error');
            status.textContent = 'Failed.';
        }
    } catch (e) { showToast('Error sending broadcast', 'error'); status.textContent = 'Error.'; }
    btn.disabled = false;
}

async function loadBroadcastLog() {
    try {
        const resp = await fetch('/api/broadcast/history');
        const data = await resp.json();
        const tbody = document.getElementById('broadcastLogBody');
        if (data.broadcasts.length === 0) {
            tbody.innerHTML = '<tr><td colspan=\"6\" class=\"text-center py-10 text-gray-600\">No broadcasts yet.</td></tr>';
            return;
        }
        tbody.innerHTML = data.broadcasts.map(b => {
            const statusBadge = b.status === 'completed' ? '<span class=\"text-green-400 text-xs font-semibold\">✅ Done</span>' :
                b.status === 'sending' ? '<span class=\"text-yellow-400 text-xs font-semibold\">⏳ Sending...</span>' :
                '<span class=\"text-gray-400 text-xs font-semibold\">⏳ Pending</span>';
            return '<tr class=\"border-b border-white/5\">' +
                '<td class=\"py-2.5 px-4 tag-text\">#' + b.id + '</td>' +
                '<td class=\"py-2.5 px-4 text-xs text-gray-400 max-w-xs truncate\">' + escHtml(b.text) + '</td>' +
                '<td class=\"py-2.5 px-4 text-xs hidden sm:table-cell\">' + b.sent_count + '</td>' +
                '<td class=\"py-2.5 px-4 text-xs hidden sm:table-cell\">' + b.failed_count + '</td>' +
                '<td class=\"py-2.5 px-4 text-xs text-gray-500 hidden md:table-cell\">' + b.created_at + '</td>' +
                '<td class=\"py-2.5 px-4\">' + statusBadge + '</td></tr>';
        }).join('');
    } catch (e) { console.error(e); }
}

function escHtml(s) { return s.replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function loadMaintenance() {
    try {
        const resp = await fetch('/api/maintenance');
        const data = await resp.json();
        maintenanceState = data;
        document.getElementById('maintenanceToggle').className = 'toggle' + (data.enabled ? ' on' : '');
        document.getElementById('maintenanceMsg').value = data.message || '';
    } catch (e) { console.error(e); }
}

function toggleMaintenance() {
    maintenanceState.enabled = !maintenanceState.enabled;
    document.getElementById('maintenanceToggle').className = 'toggle' + (maintenanceState.enabled ? ' on' : '');
}

async function saveMaintenance() {
    const msg = document.getElementById('maintenanceMsg').value.trim();
    const status = document.getElementById('maintenanceStatus');
    status.textContent = 'Saving...';
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (tg) headers['x-init-data'] = tg.initData;
        await fetch('/api/maintenance', { method: 'POST', headers, body: JSON.stringify({ enabled: maintenanceState.enabled, message: msg }) });
        status.textContent = 'Saved!';
        showToast(maintenanceState.enabled ? 'Maintenance mode enabled' : 'Maintenance mode disabled');
        setTimeout(() => status.textContent = '', 2000);
        loadMaintenance();
    } catch (e) { showToast('Error saving settings', 'error'); status.textContent = 'Error.'; }
}

async function loadHealth() {
    try {
        const resp = await fetch('/api/health');
        const data = await resp.json();
        document.getElementById('uptime').textContent = data.uptime;
        document.getElementById('uptimeHeader').textContent = data.uptime;
        document.getElementById('schedulerJobs').textContent = data.scheduler_jobs;
        const dbEl = document.getElementById('dbStatus');
        dbEl.textContent = data.db;
        dbEl.className = 'text-sm font-semibold ' + (data.db === 'Connected' ? 'text-green-400' : 'text-red-400');
        const dot = document.getElementById('statusDot');
        const txt = document.getElementById('statusText');
        if (data.db === 'Connected') {
            dot.className = 'pulse-dot active';
            txt.textContent = 'Live';
            txt.className = 'text-green-400 text-xs';
        } else {
            dot.className = 'pulse-dot inactive';
            txt.textContent = 'Degraded';
            txt.className = 'text-red-400 text-xs';
        }
    } catch (e) { console.error(e); }
}

document.addEventListener('DOMContentLoaded', async () => {
    initTelegram();
    const verified = await verifyAccess();
    if (verified) {
        await Promise.all([loadMetrics(), loadUsers(), loadHealth(), loadMaintenance(), loadBroadcastLog()]);
        setInterval(() => { loadMetrics(); loadHealth(); }, 15000);
        setInterval(() => loadBroadcastLog(), 10000);
    }
});
