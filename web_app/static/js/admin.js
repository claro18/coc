let tg = null;
let userId = null;
let filterTimer = null;

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
        document.getElementById('loading').innerHTML = '<div class=\"text-center fade-in\"><div class=\"text-5xl mb-5\">🔒</div><div class=\"text-gray-300 font-medium text-lg\">Please open this from the Telegram bot.</div><div class=\"text-gray-600 text-sm mt-2\">This dashboard can only be accessed through Telegram.</div></div>';
        return false;
    }
    try {
        const initData = tg.initData;
        if (!initData) {
            document.getElementById('loading').innerHTML = '<div class=\"text-center fade-in\"><div class=\"text-5xl mb-5\">⚠️</div><div class=\"text-gray-300 font-medium text-lg\">No init data available.</div></div>';
            return false;
        }
        const resp = await fetch('/api/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData }),
        });
        if (!resp.ok) {
            document.getElementById('loading').innerHTML = '<div class=\"text-center fade-in\"><div class=\"text-5xl mb-5\">🚫</div><div class=\"text-gray-300 font-medium text-lg\">Access Denied</div><div class=\"text-gray-600 text-sm mt-2\">You do not have permission to view this dashboard.</div></div>';
            return false;
        }
        const data = await resp.json();
        userId = data.user_id;
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard').style.display = 'block';
        return true;
    } catch (e) {
        document.getElementById('loading').innerHTML = '<div class=\"text-center fade-in\"><div class=\"text-5xl mb-5\">💥</div><div class=\"text-gray-300 font-medium text-lg\">Verification Failed</div><div class=\"text-gray-600 text-sm mt-2\">' + e.message + '</div></div>';
        return false;
    }
}

function removeSkeletons() {
    document.querySelectorAll('.skeleton').forEach(el => el.classList.remove('skeleton'));
}

async function loadMetrics() {
    try {
        const resp = await fetch('/api/metrics');
        const data = await resp.json();
        document.getElementById('totalUsers').textContent = data.total_users;
        document.getElementById('activeTrackers').textContent = data.active_trackers;
        document.getElementById('activeUpgrades').textContent = data.active_upgrades;
        document.getElementById('totalUpgrades').textContent = data.total_upgrades;
        removeSkeletons();
    } catch (e) {
        console.error('Metrics error:', e);
    }
}

async function loadUsers() {
    try {
        const resp = await fetch('/api/users');
        const data = await resp.json();
        const tbody = document.getElementById('userTableBody');
        const footer = document.getElementById('tableFooter');
        if (data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan=\"6\" class=\"text-center py-12 text-gray-600\">No users registered yet.</td></tr>';
            footer.textContent = '0 users';
            return;
        }
        footer.textContent = data.users.length + ' user' + (data.users.length !== 1 ? 's' : '') + ' (last 100)';
        window._allUsers = data.users;
        renderUsers(data.users);
    } catch (e) {
        console.error('Users error:', e);
    }
}

function renderUsers(users) {
    const tbody = document.getElementById('userTableBody');
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan=\"6\" class=\"text-center py-12 text-gray-600\">No matching users.</td></tr>';
        return;
    }
    tbody.innerHTML = users.map(u => {
        const thIcon = u.town_hall >= 14 ? '👑' : u.town_hall >= 11 ? '🔥' : u.town_hall >= 8 ? '⚔️' : u.town_hall >= 5 ? '🛡️' : '🏠';
        const syncLabel = u.last_sync !== 'Never' ? u.last_sync : '<span class=\"text-gray-600\">Never</span>';
        return '<tr class=\"user-row border-b border-white/5\">' +
            '<td class=\"py-3 px-4 sm:px-6 tag-text\">' + u.id + '</td>' +
            '<td class=\"py-3 px-4\"><span class=\"font-medium\">' + (u.username || '<span class=\"text-gray-600\">—</span>') + '</span></td>' +
            '<td class=\"py-3 px-4 tag-text hidden sm:table-cell\">' + (u.tag || '<span class=\"text-gray-600\">—</span>') + '</td>' +
            '<td class=\"py-3 px-4\"><span class=\"badge-th badge-th-home\">' + thIcon + ' ' + (u.town_hall || '?') + '</span></td>' +
            '<td class=\"py-3 px-4 text-gray-400 hidden md:table-cell\">' + u.created_at + '</td>' +
            '<td class=\"py-3 px-4 text-gray-400 hidden md:table-cell\">' + syncLabel + '</td>' +
            '</tr>';
    }).join('');
}

function filterUsers() {
    const q = document.getElementById('searchInput').value.toLowerCase().trim();
    if (!q) {
        renderUsers(window._allUsers || []);
        return;
    }
    const filtered = (window._allUsers || []).filter(u =>
        String(u.id).includes(q) ||
        (u.username && u.username.toLowerCase().includes(q)) ||
        (u.tag && u.tag.toLowerCase().includes(q))
    );
    renderUsers(filtered);
}

function debouncedFilter() {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(filterUsers, 200);
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
        dbEl.className = 'text-base font-semibold ' + (data.db === 'Connected' ? 'text-green-400' : 'text-red-400');
        const dot = document.getElementById('statusDot');
        const txt = document.getElementById('statusText');
        if (data.db === 'Connected') {
            dot.className = 'pulse-dot active';
            txt.textContent = 'Live';
            txt.className = 'text-green-400';
        } else {
            dot.className = 'pulse-dot inactive';
            txt.textContent = 'Degraded';
            txt.className = 'text-red-400';
        }
    } catch (e) {
        console.error('Health error:', e);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    initTelegram();
    const verified = await verifyAccess();
    if (verified) {
        await Promise.all([loadMetrics(), loadUsers(), loadHealth()]);
        setInterval(() => {
            Promise.all([loadMetrics(), loadHealth()]);
        }, 15000);
    }
});
