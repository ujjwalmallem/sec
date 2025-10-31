// Whale Scanner Web UI JavaScript

// Global state
const state = {
    socket: null,
    connected: false,
    running: false,
    signals: [],
    watchlist: [],
    charts: {},
    scanHistory: []
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeSocketIO();
    loadInitialData();
    setupEventListeners();
    initializeCharts();
});

// ===== Socket.IO =====

function initializeSocketIO() {
    state.socket = io();

    state.socket.on('connect', function() {
        console.log('Connected to server');
        updateConnectionStatus(true);
        showToast('Connected to server', 'success');
    });

    state.socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
        showToast('Disconnected from server', 'warning');
    });

    state.socket.on('status', function(data) {
        updateStatus(data);
    });

    state.socket.on('scanner_connected', function(data) {
        updateIBKRStatus(true);
        showToast('✓ Connected to IBKR', 'success');
    });

    state.socket.on('scanner_started', function(data) {
        state.running = true;
        updateScannerStatus(true);
        showToast('🐋 Scanner started', 'info');
    });

    state.socket.on('scanner_stopped', function(data) {
        state.running = false;
        updateScannerStatus(false);
        showToast('⏹ Scanner stopped', 'info');
    });

    state.socket.on('scan_update', function(data) {
        handleScanUpdate(data);
    });

    state.socket.on('scan_complete', function(data) {
        handleScanComplete(data);
    });

    state.socket.on('scanner_error', function(data) {
        showToast('Error: ' + data.message, 'danger');
    });

    state.socket.on('error', function(data) {
        showToast('Error: ' + data.message, 'danger');
    });
}

// ===== Data Loading =====

function loadInitialData() {
    // Load status
    fetch('/api/status')
        .then(res => res.json())
        .then(data => updateStatus(data))
        .catch(err => console.error('Error loading status:', err));

    // Load watchlist
    fetch('/api/watchlist')
        .then(res => res.json())
        .then(data => {
            state.watchlist = data;
            renderWatchlist();
        })
        .catch(err => console.error('Error loading watchlist:', err));

    // Load recent signals
    fetch('/api/signals')
        .then(res => res.json())
        .then(data => {
            if (data && data.length > 0) {
                data.forEach(symbolData => {
                    if (symbolData.signals) {
                        symbolData.signals.forEach(signal => {
                            addSignalToTable(signal, symbolData.symbol);
                        });
                    }
                });
            }
        })
        .catch(err => console.error('Error loading signals:', err));

    // Load scan history
    fetch('/api/recent_scans')
        .then(res => res.json())
        .then(data => {
            state.scanHistory = data;
            renderScanHistory();
        })
        .catch(err => console.error('Error loading scan history:', err));
}

// ===== Event Listeners =====

function setupEventListeners() {
    // Start/Stop buttons
    document.getElementById('start-btn').addEventListener('click', startScanner);
    document.getElementById('stop-btn').addEventListener('click', stopScanner);

    // Watchlist management
    document.getElementById('add-symbol-btn').addEventListener('click', addSymbolToWatchlist);
    document.getElementById('add-symbol-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            addSymbolToWatchlist();
        }
    });

    // Clear signals
    document.getElementById('clear-signals-btn').addEventListener('click', clearSignals);

    // Save configuration
    document.getElementById('save-config-btn').addEventListener('click', saveConfiguration);
}

// ===== Scanner Control =====

function startScanner() {
    state.socket.emit('start_scanner');
    document.getElementById('start-btn').disabled = true;
    document.getElementById('stop-btn').disabled = false;
}

function stopScanner() {
    state.socket.emit('stop_scanner');
    document.getElementById('start-btn').disabled = false;
    document.getElementById('stop-btn').disabled = true;
}

// ===== Status Updates =====

function updateConnectionStatus(connected) {
    state.connected = connected;
    const badge = document.getElementById('connection-status');

    if (connected) {
        badge.innerHTML = '<i class="fas fa-circle connection-dot connected"></i> Connected';
        badge.className = 'badge bg-success';
    } else {
        badge.innerHTML = '<i class="fas fa-circle connection-dot disconnected"></i> Disconnected';
        badge.className = 'badge bg-danger';
    }
}

function updateStatus(data) {
    if (data.running !== undefined) {
        state.running = data.running;
        updateScannerStatus(data.running);
    }

    if (data.connected !== undefined) {
        updateIBKRStatus(data.connected);
    }

    if (data.scan_count !== undefined) {
        document.getElementById('scan-count').textContent = 'Scans: ' + data.scan_count;
        document.getElementById('total-scans').textContent = data.scan_count;
    }

    if (data.last_scan) {
        const lastScan = new Date(data.last_scan);
        document.getElementById('last-scan').textContent = lastScan.toLocaleTimeString();
    }

    if (data.watchlist) {
        state.watchlist = data.watchlist;
        renderWatchlist();
    }
}

function updateScannerStatus(running) {
    const badge = document.getElementById('scanner-status');

    if (running) {
        badge.textContent = 'Running';
        badge.className = 'badge bg-success running';
        document.getElementById('start-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
    } else {
        badge.textContent = 'Stopped';
        badge.className = 'badge bg-secondary';
        document.getElementById('start-btn').disabled = false;
        document.getElementById('stop-btn').disabled = true;
    }
}

function updateIBKRStatus(connected) {
    const badge = document.getElementById('ibkr-status');

    if (connected) {
        badge.textContent = 'Connected';
        badge.className = 'badge bg-success';
    } else {
        badge.textContent = 'Disconnected';
        badge.className = 'badge bg-secondary';
    }
}

// ===== Signal Handling =====

function handleScanUpdate(data) {
    console.log('Scan update:', data);

    // Update watchlist item as scanning
    highlightWatchlistItem(data.symbol, true);

    // Add signals to table
    if (data.signals && data.signals.length > 0) {
        data.signals.forEach(signal => {
            addSignalToTable(signal, data.symbol);
        });

        // Update stats
        updateStats();

        // Play notification sound (optional)
        // playNotificationSound();
    }

    // Update charts
    if (data.metrics) {
        updateChartsWithData(data.symbol, data.metrics);
    }

    // Remove scanning highlight after delay
    setTimeout(() => {
        highlightWatchlistItem(data.symbol, false);
    }, 2000);
}

function handleScanComplete(data) {
    console.log('Scan complete:', data);

    // Update scan history
    state.scanHistory.unshift({
        timestamp: new Date().toISOString(),
        scan_number: data.scan_number,
        symbols_scanned: data.results.length,
        total_signals: data.results.reduce((sum, r) => sum + (r.signals ? r.signals.length : 0), 0)
    });
    state.scanHistory = state.scanHistory.slice(0, 20); // Keep last 20

    renderScanHistory();
    updateStats();
}

function addSignalToTable(signal, symbol) {
    const tbody = document.getElementById('signals-tbody');

    // Remove "no signals" message if present
    if (tbody.querySelector('td[colspan]')) {
        tbody.innerHTML = '';
    }

    // Create row
    const row = document.createElement('tr');
    row.className = 'signal-row signal-new';

    const time = new Date(signal.timestamp || Date.now()).toLocaleTimeString();
    const signalType = getSignalTypeBadge(signal.type || 'UNKNOWN');
    const strength = signal.signal_strength || 0;
    const strengthBar = createStrengthBar(strength);

    // Contract info
    let contract = 'N/A';
    if (signal.strike && signal.right) {
        contract = `$${signal.strike} ${signal.right}`;
        if (signal.dte !== undefined) {
            contract += ` (${signal.dte}D)`;
        }
    } else {
        contract = signal.description || 'Combo Signal';
    }

    // P/C Ratio
    let pcRatio = 'N/A';
    if (signal.pc_ratio !== undefined) {
        pcRatio = getPCRatioBadge(signal.pc_ratio);
    }

    row.innerHTML = `
        <td>${time}</td>
        <td><strong>${signal.symbol || symbol}</strong></td>
        <td>${signalType}</td>
        <td>${contract}</td>
        <td>${signal.volume ? formatNumber(signal.volume) : 'N/A'}</td>
        <td>${signal.open_interest ? formatNumber(signal.open_interest) : 'N/A'}</td>
        <td>${pcRatio}</td>
        <td><small>${signal.action || 'MONITOR'}</small></td>
        <td>${strengthBar}</td>
    `;

    // Add to beginning of table
    tbody.insertBefore(row, tbody.firstChild);

    // Keep max 100 rows
    while (tbody.children.length > 100) {
        tbody.removeChild(tbody.lastChild);
    }

    // Remove highlight after animation
    setTimeout(() => {
        row.classList.remove('signal-new');
    }, 2000);

    // Add to state
    state.signals.unshift(signal);
}

function clearSignals() {
    const tbody = document.getElementById('signals-tbody');
    tbody.innerHTML = `
        <tr>
            <td colspan="9" class="text-center text-muted py-5">
                <i class="fas fa-search fa-3x mb-3"></i>
                <br>No signals yet. Start scanner to begin monitoring.
            </td>
        </tr>
    `;
    state.signals = [];
    updateStats();
}

// ===== Watchlist Management =====

function renderWatchlist() {
    const container = document.getElementById('watchlist-items');
    container.innerHTML = '';

    state.watchlist.forEach(symbol => {
        const item = document.createElement('div');
        item.className = 'watchlist-item';
        item.dataset.symbol = symbol;

        item.innerHTML = `
            <span><strong>${symbol}</strong></span>
            <button class="btn btn-sm btn-outline-danger" onclick="removeSymbolFromWatchlist('${symbol}')">
                <i class="fas fa-times"></i>
            </button>
        `;

        container.appendChild(item);
    });
}

function addSymbolToWatchlist() {
    const input = document.getElementById('add-symbol-input');
    const symbol = input.value.trim().toUpperCase();

    if (!symbol) {
        showToast('Please enter a symbol', 'warning');
        return;
    }

    if (state.watchlist.includes(symbol)) {
        showToast('Symbol already in watchlist', 'warning');
        return;
    }

    state.watchlist.push(symbol);

    fetch('/api/watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: state.watchlist })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            renderWatchlist();
            input.value = '';
            showToast(`Added ${symbol} to watchlist`, 'success');
        }
    })
    .catch(err => {
        console.error('Error adding symbol:', err);
        showToast('Error adding symbol', 'danger');
    });
}

function removeSymbolFromWatchlist(symbol) {
    state.watchlist = state.watchlist.filter(s => s !== symbol);

    fetch('/api/watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: state.watchlist })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            renderWatchlist();
            showToast(`Removed ${symbol} from watchlist`, 'info');
        }
    })
    .catch(err => {
        console.error('Error removing symbol:', err);
        showToast('Error removing symbol', 'danger');
    });
}

function highlightWatchlistItem(symbol, highlight) {
    const item = document.querySelector(`.watchlist-item[data-symbol="${symbol}"]`);
    if (item) {
        if (highlight) {
            item.classList.add('scanning');
        } else {
            item.classList.remove('scanning');
        }
    }
}

// ===== Charts =====

function initializeCharts() {
    // P/C Ratio Chart
    const pcRatioCtx = document.getElementById('pcRatioChart').getContext('2d');
    state.charts.pcRatio = new Chart(pcRatioCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'P/C Ratio',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Volume Chart
    const volumeCtx = document.getElementById('volumeChart').getContext('2d');
    state.charts.volume = new Chart(volumeCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Call Volume',
                data: [],
                backgroundColor: 'rgba(75, 192, 192, 0.5)'
            }, {
                label: 'Put Volume',
                data: [],
                backgroundColor: 'rgba(255, 99, 132, 0.5)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });

    // Signal Distribution Chart
    const signalDistCtx = document.getElementById('signalDistChart').getContext('2d');
    state.charts.signalDist = new Chart(signalDistCtx, {
        type: 'doughnut',
        data: {
            labels: ['Bullish', 'Bearish', 'Neutral'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(201, 203, 207, 0.8)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });

    // Heatmap Chart (simplified as bar chart)
    const heatmapCtx = document.getElementById('heatmapChart').getContext('2d');
    state.charts.heatmap = new Chart(heatmapCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Whale Signals by Symbol',
                data: [],
                backgroundColor: 'rgba(0, 102, 204, 0.8)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y'
        }
    });
}

function updateChartsWithData(symbol, metrics) {
    // Update P/C Ratio chart
    if (state.charts.pcRatio && metrics.pc_ratio_volume) {
        const chart = state.charts.pcRatio;
        const time = new Date().toLocaleTimeString();

        chart.data.labels.push(time);
        chart.data.datasets[0].data.push(metrics.pc_ratio_volume);

        // Keep last 20 points
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update();
    }

    // Update Volume chart
    if (state.charts.volume && metrics.call_volume) {
        const chart = state.charts.volume;

        if (!chart.data.labels.includes(symbol)) {
            chart.data.labels.push(symbol);
            chart.data.datasets[0].data.push(metrics.call_volume);
            chart.data.datasets[1].data.push(metrics.put_volume);
            chart.update();
        }
    }

    // Update signal distribution
    updateSignalDistribution();

    // Update heatmap
    updateHeatmap();
}

function updateSignalDistribution() {
    const bullish = state.signals.filter(s =>
        s.type && (s.type.includes('BULLISH') || s.type === 'STRONG_BULL')
    ).length;

    const bearish = state.signals.filter(s =>
        s.type && (s.type.includes('BEARISH') || s.type === 'INSTITUTIONAL_HEDGE')
    ).length;

    const neutral = state.signals.length - bullish - bearish;

    if (state.charts.signalDist) {
        state.charts.signalDist.data.datasets[0].data = [bullish, bearish, neutral];
        state.charts.signalDist.update();
    }
}

function updateHeatmap() {
    // Count signals by symbol
    const symbolCounts = {};
    state.signals.forEach(signal => {
        const symbol = signal.symbol;
        symbolCounts[symbol] = (symbolCounts[symbol] || 0) + 1;
    });

    const labels = Object.keys(symbolCounts);
    const data = Object.values(symbolCounts);

    if (state.charts.heatmap) {
        state.charts.heatmap.data.labels = labels;
        state.charts.heatmap.data.datasets[0].data = data;
        state.charts.heatmap.update();
    }
}

// ===== Scan History =====

function renderScanHistory() {
    const tbody = document.getElementById('history-tbody');

    if (state.scanHistory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No scan history available</td></tr>';
        return;
    }

    tbody.innerHTML = '';

    state.scanHistory.forEach(scan => {
        const row = document.createElement('tr');
        const time = new Date(scan.timestamp).toLocaleString();

        row.innerHTML = `
            <td>${scan.scan_number}</td>
            <td>${time}</td>
            <td>${scan.symbols_scanned}</td>
            <td>${scan.total_signals}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" disabled>
                    <i class="fas fa-eye"></i> View
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });
}

// ===== Stats =====

function updateStats() {
    const totalSignals = state.signals.length;
    const whaleSignals = state.signals.filter(s =>
        s.signal_strength && s.signal_strength > 75
    ).length;
    const symbolsScanned = new Set(state.signals.map(s => s.symbol)).size;

    document.getElementById('total-signals').textContent = totalSignals;
    document.getElementById('whale-signals').textContent = whaleSignals;
    document.getElementById('symbols-scanned').textContent = symbolsScanned;
}

// ===== Configuration =====

function saveConfiguration() {
    showToast('Configuration save feature coming soon', 'info');
}

// ===== Utility Functions =====

function getSignalTypeBadge(type) {
    const badges = {
        'EXTREME_BULLISH': '<span class="badge badge-extreme-bullish">EXTREME BULL</span>',
        'BULLISH': '<span class="badge badge-bullish">BULLISH</span>',
        'BEARISH': '<span class="badge badge-bearish">BEARISH</span>',
        'EXTREME_BEARISH': '<span class="badge badge-extreme-bearish">EXTREME BEAR</span>',
        'STRONG_BULL': '<span class="badge bg-primary">STRONG BULL</span>',
        'INSTITUTIONAL_HEDGE': '<span class="badge bg-warning">INST HEDGE</span>',
        'RETAIL_FOMO': '<span class="badge bg-danger">RETAIL FOMO</span>',
        'CALL_HEDGE': '<span class="badge bg-secondary">CALL HEDGE</span>',
        'PUT_HEDGE': '<span class="badge bg-secondary">PUT HEDGE</span>'
    };

    return badges[type] || `<span class="badge bg-secondary">${type}</span>`;
}

function getPCRatioBadge(ratio) {
    let className, label;

    if (ratio < 0.5) {
        className = 'extreme-bullish';
        label = `${ratio.toFixed(3)} (⚡BULL)`;
    } else if (ratio < 0.7) {
        className = 'bullish';
        label = `${ratio.toFixed(3)} (↑)`;
    } else if (ratio <= 1.3) {
        className = 'neutral';
        label = `${ratio.toFixed(3)} (→)`;
    } else if (ratio <= 1.5) {
        className = 'bearish';
        label = `${ratio.toFixed(3)} (↓)`;
    } else {
        className = 'extreme-bearish';
        label = `${ratio.toFixed(3)} (⚡BEAR)`;
    }

    return `<span class="pc-ratio-indicator ${className}">${label}</span>`;
}

function createStrengthBar(strength) {
    let className;
    if (strength >= 90) className = 'extreme';
    else if (strength >= 75) className = 'high';
    else if (strength >= 50) className = 'medium';
    else className = 'low';

    return `
        <div class="strength-bar">
            <div class="strength-fill ${className}" style="width: ${strength}%">
                ${strength}
            </div>
        </div>
    `;
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(2) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    // Create toast
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    container.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}
