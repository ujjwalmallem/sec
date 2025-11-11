// Whale Scanner Dashboard JavaScript

const API_BASE = '';  // Same origin

// State
let scannerRunning = false;
let currentRuleType = 'all';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Whale Scanner Dashboard loaded');

    // Setup event listeners
    setupEventListeners();

    // Load initial data
    loadWatchlist();
    loadRules();
    loadSignals();
    loadRecentScans();
    updateStatus();

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadSignals();
        loadRecentScans();
        updateStatus();
    }, 30000);
});

function setupEventListeners() {
    // Scanner controls
    document.getElementById('btn-scan-once').addEventListener('click', runScanOnce);
    document.getElementById('btn-start').addEventListener('click', startScanner);
    document.getElementById('btn-stop').addEventListener('click', stopScanner);

    // Ticker management
    document.getElementById('btn-add-ticker').addEventListener('click', addTicker);
    document.getElementById('new-ticker').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addTicker();
    });

    // Rule tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentRuleType = e.target.dataset.type;
            loadRules();
        });
    });
}

// =============================================================================
// STATUS
// =============================================================================

async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();

        scannerRunning = data.scanner_running;

        document.getElementById('scanner-status').textContent =
            `Scanner: ${scannerRunning ? 'Running' : 'Stopped'}`;

        document.getElementById('btn-start').disabled = scannerRunning;
        document.getElementById('btn-stop').disabled = !scannerRunning;

        if (data.last_scan) {
            const lastUpdate = new Date(data.last_scan.completed_at ||Date.now());
            document.getElementById('last-update').textContent =
                `Last Update: ${lastUpdate.toLocaleTimeString()}`;
        }
    } catch (error) {
        console.error('Error updating status:', error);
    }
}

// =============================================================================
// SCANNER CONTROLS
// =============================================================================

async function runScanOnce() {
    try {
        showMessage('Running scan...', 'info');
        const response = await fetch(`${API_BASE}/api/scanner/run-once`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            showMessage(`Scan complete: ${data.results.signals_detected} signals detected`, 'success');
            loadSignals();
            loadRecentScans();
        } else {
            const error = await response.json();
            showMessage(`Error: ${error.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

async function startScanner() {
    try {
        const response = await fetch(`${API_BASE}/api/scanner/start`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ interval: 60 })
        });

        if (response.ok) {
            showMessage('Scanner started', 'success');
            updateStatus();
        } else {
            const error = await response.json();
            showMessage(`Error: ${error.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

async function stopScanner() {
    try {
        const response = await fetch(`${API_BASE}/api/scanner/stop`, {
            method: 'POST'
        });

        if (response.ok) {
            showMessage('Scanner stopped', 'success');
            updateStatus();
        } else {
            const error = await response.json();
            showMessage(`Error: ${error.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

// =============================================================================
// SIGNALS
// =============================================================================

async function loadSignals() {
    try {
        const response = await fetch(`${API_BASE}/api/signals`);
        const data = await response.json();

        const container = document.getElementById('signals-container');

        if (!data.signals || data.signals.length === 0) {
            container.innerHTML = '<p class="loading">No active signals</p>';
            return;
        }

        container.innerHTML = data.signals.map(signal => `
            <div class="signal-card">
                <div class="signal-header">
                    <span class="signal-symbol">${signal.symbol}</span>
                    <span class="signal-strength">Strength: ${signal.signal_strength}</span>
                </div>
                <div class="signal-type">${formatSignalType(signal.signal_type)}</div>
                <div class="signal-description">${signal.description}</div>
                ${signal.action_recommended ?
                    `<div class="signal-action">Action: ${signal.action_recommended}</div>` :
                    ''}
                <div style="margin-top: 10px; font-size: 0.85em; color: #6b7280;">
                    Detected: ${new Date(signal.detected_at).toLocaleString()}
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading signals:', error);
    }
}

function formatSignalType(type) {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// =============================================================================
// WATCHLIST
// =============================================================================

async function loadWatchlist() {
    try {
        const response = await fetch(`${API_BASE}/api/tickers`);
        const data = await response.json();

        const container = document.getElementById('watchlist-container');

        if (!data.tickers || data.tickers.length === 0) {
            container.innerHTML = '<p class="loading">No tickers in watchlist</p>';
            return;
        }

        container.innerHTML = data.tickers.map(ticker => `
            <div class="ticker-card">
                <div>
                    <div class="ticker-symbol">${ticker.symbol}</div>
                    <div class="ticker-name">${ticker.name || 'N/A'}</div>
                </div>
                <button class="ticker-remove" onclick="removeTicker('${ticker.symbol}')">
                    Remove
                </button>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading watchlist:', error);
    }
}

async function addTicker() {
    const input = document.getElementById('new-ticker');
    const symbol = input.value.trim().toUpperCase();

    if (!symbol) return;

    try {
        const response = await fetch(`${API_BASE}/api/tickers`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ symbol })
        });

        if (response.ok) {
            showMessage(`Added ${symbol}`, 'success');
            input.value = '';
            loadWatchlist();
        } else {
            const error = await response.json();
            showMessage(`Error: ${error.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

async function removeTicker(symbol) {
    if (!confirm(`Remove ${symbol} from watchlist?`)) return;

    try {
        const response = await fetch(`${API_BASE}/api/tickers/${symbol}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showMessage(`Removed ${symbol}`, 'success');
            loadWatchlist();
        } else {
            const error = await response.json();
            showMessage(`Error: ${error.error}`, 'error');
        }
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

// =============================================================================
// RULES
// =============================================================================

async function loadRules() {
    try {
        const url = currentRuleType === 'all' ?
            `${API_BASE}/api/rules` :
            `${API_BASE}/api/rules?type=${currentRuleType}`;

        const response = await fetch(url);
        const data = await response.json();

        const container = document.getElementById('rules-container');

        if (!data.rules || data.rules.length === 0) {
            container.innerHTML = '<p class="loading">No rules found</p>';
            return;
        }

        container.innerHTML = data.rules.map(rule => `
            <div class="rule-card">
                <div class="rule-header">
                    <span class="rule-name">${formatSignalType(rule.rule_name)}</span>
                    <span class="rule-type">${rule.rule_type}</span>
                </div>
                <div class="rule-description">${rule.description}</div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading rules:', error);
    }
}

// =============================================================================
// SCANS
// =============================================================================

async function loadRecentScans() {
    try {
        const response = await fetch(`${API_BASE}/api/scans/recent?limit=5`);
        const data = await response.json();

        const container = document.getElementById('scans-container');

        if (!data.scans || data.scans.length === 0) {
            container.innerHTML = '<p class="loading">No recent scans</p>';
            return;
        }

        container.innerHTML = data.scans.map(scan => `
            <div class="scan-row">
                <div>${new Date(scan.started_at).toLocaleString()}</div>
                <div><span class="scan-status ${scan.status}">${scan.status}</span></div>
                <div>${scan.symbols_scanned} symbols</div>
                <div>${scan.signals_detected} signals</div>
                <div>${scan.duration_seconds ? scan.duration_seconds.toFixed(1) + 's' : 'N/A'}</div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading scans:', error);
    }
}

// =============================================================================
// UTILITIES
// =============================================================================

function showMessage(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = type === 'error' ? 'error' : 'success';
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '1000';
    notification.style.maxWidth = '400px';

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}
