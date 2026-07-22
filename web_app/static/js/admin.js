let tg = null;
let userId = null;

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
        document.getElementById('loading').textContent = 'Please open this from the Telegram bot.';
        return false;
    }

    try {
        const initData = tg.initData;
        if (!initData) {
            document.getElementById('loading').textContent = 'No init data available.';
            return false;
        }

        const resp = await fetch('/api/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData }),
        });

        if (!resp.ok) {
            document.getElementById('loading').textContent = 'Access denied.';
            return false;
        }

        const data = await resp.json();
        userId = data.user_id;
        document.getElementById('loading').style.display = 'none';
        document.getElementById('dashboard').style.display = 'block';
        return true;
    } catch (e) {
        document.getElementById('loading').textContent = 'Verification failed: ' + e.message;
        return false;
    }
}

async function loadMetrics() {
    try {
        const resp = await fetch('/api/metrics');
        const data = await resp.json();
        document.getElementById('totalUsers').textContent = data.total_users;
        document.getElementById('activeTrackers').textContent = data.active_trackers;
        document.getElementById('activeUpgrades').textContent = data.active_upgrades;
        document.getElementById('totalUpgrades').textContent = data.total_upgrades;
    } catch (e) {
        console.error('Failed to load metrics:', e);
    }
}

async function loadUsers() {
    try {
        const resp = await fetch('/api/users');
        const data = await resp.json();
        const tbody = document.querySelector('#userTable tbody');
        tbody.innerHTML = '';

        if (data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-gray-400 py-4">No users registered yet.</td></tr>';
            return;
        }

        data.users.forEach(user => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-gray-700 hover:bg-gray-700';
            tr.innerHTML = `
                <td class="py-2 px-3"><code>${user.id}</code></td>
                <td class="py-2 px-3">${user.username || '-'}</td>
                <td class="py-2 px-3">${user.town_hall || '-'}</td>
                <td class="py-2 px-3">${user.created_at}</td>
                <td class="py-2 px-3">${user.last_sync}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('Failed to load users:', e);
    }
}

async function loadHealth() {
    try {
        const resp = await fetch('/api/health');
        const data = await resp.json();
        document.getElementById('uptime').textContent = data.uptime;
        document.getElementById('schedulerJobs').textContent = data.scheduler_jobs;
        document.getElementById('dbStatus').textContent = data.db;
        document.getElementById('dbStatus').className = data.db === 'Connected' ? 'text-green-400 font-semibold' : 'text-red-400 font-semibold';
    } catch (e) {
        console.error('Failed to load health:', e);
    }
}

function filterUsers() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const rows = document.querySelectorAll('#userTable tbody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    initTelegram();
    const verified = await verifyAccess();
    if (verified) {
        await Promise.all([loadMetrics(), loadUsers(), loadHealth()]);
        setInterval(() => {
            Promise.all([loadMetrics(), loadHealth()]);
        }, 30000);
    }
});
