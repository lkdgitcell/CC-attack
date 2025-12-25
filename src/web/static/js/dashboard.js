// Dashboard JavaScript
let currentSessionId = null;
let websocket = null;
let requestsChart = null;
let responseTimeChart = null;
let startTime = null;
let duration = 60;

// Initialize charts
function initCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                ticks: { color: '#bbb' },
                grid: { color: '#0f3460' }
            },
            x: {
                ticks: { color: '#bbb' },
                grid: { color: '#0f3460' }
            }
        },
        plugins: {
            legend: {
                labels: { color: '#eee' }
            }
        }
    };

    // Requests Chart
    const requestsCtx = document.getElementById('requestsChart').getContext('2d');
    requestsChart = new Chart(requestsCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Requests/sec',
                data: [],
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                tension: 0.4
            }]
        },
        options: chartOptions
    });

    // Response Time Chart
    const responseCtx = document.getElementById('responseTimeChart').getContext('2d');
    responseTimeChart = new Chart(responseCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Avg Response Time (ms)',
                data: [],
                borderColor: '#2ecc71',
                backgroundColor: 'rgba(46, 204, 113, 0.1)',
                tension: 0.4
            }]
        },
        options: chartOptions
    });
}

// Add log entry
function addLog(message, type = 'info') {
    const logsContainer = document.getElementById('logsContainer');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;

    const time = new Date().toLocaleTimeString();
    logEntry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-message">${message}</span>
    `;

    logsContainer.insertBefore(logEntry, logsContainer.firstChild);

    // Limit log entries
    while (logsContainer.children.length > 100) {
        logsContainer.removeChild(logsContainer.lastChild);
    }
}

// Update statistics
function updateStats(stats) {
    document.getElementById('totalRequests').textContent = stats.total_requests.toLocaleString();
    document.getElementById('successfulRequests').textContent = stats.successful_requests.toLocaleString();
    document.getElementById('failedRequests').textContent = stats.failed_requests.toLocaleString();
    document.getElementById('successRate').textContent = stats.success_rate.toFixed(2) + '%';
    document.getElementById('requestsPerSec').textContent = stats.requests_per_second.toFixed(2);
    document.getElementById('avgResponse').textContent = (stats.avg_response_time * 1000).toFixed(2) + 'ms';

    // Update progress bar
    if (startTime) {
        const elapsed = (Date.now() - startTime) / 1000;
        const progress = Math.min((elapsed / duration) * 100, 100);
        document.getElementById('progressBar').style.width = progress + '%';
        document.getElementById('progressText').textContent =
            `${Math.floor(elapsed)}s / ${duration}s - ${stats.total_requests} requests`;
    }

    // Update charts
    const now = new Date().toLocaleTimeString();

    // Add new data point
    requestsChart.data.labels.push(now);
    requestsChart.data.datasets[0].data.push(stats.requests_per_second);

    responseTimeChart.data.labels.push(now);
    responseTimeChart.data.datasets[0].data.push(stats.avg_response_time * 1000);

    // Keep only last 20 points
    if (requestsChart.data.labels.length > 20) {
        requestsChart.data.labels.shift();
        requestsChart.data.datasets[0].data.shift();
        responseTimeChart.data.labels.shift();
        responseTimeChart.data.datasets[0].data.shift();
    }

    requestsChart.update('none');
    responseTimeChart.update('none');
}

// Connect WebSocket
function connectWebSocket(sessionId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;

    websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
        addLog('WebSocket connected', 'success');

        // Send ping every 30 seconds
        setInterval(() => {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send('ping');
            }
        }, 30000);
    };

    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'stats_update') {
            updateStats(data.data);
        } else if (data.type === 'attack_complete') {
            updateStats(data.data);
            addLog('Attack completed!', 'success');
            onAttackComplete();
        } else if (data.type === 'pong') {
            // Pong received
        }
    };

    websocket.onerror = (error) => {
        addLog('WebSocket error: ' + error, 'error');
    };

    websocket.onclose = () => {
        addLog('WebSocket disconnected', 'warning');
        websocket = null;
    };
}

// Start attack
async function startAttack(formData) {
    try {
        const response = await fetch('/api/attack/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start attack');
        }

        const data = await response.json();
        currentSessionId = data.session_id;

        addLog(`Attack started: ${data.message}`, 'success');

        // Connect WebSocket
        connectWebSocket(currentSessionId);

        // Update UI
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
        document.getElementById('attackForm').querySelectorAll('input, select').forEach(el => {
            el.disabled = true;
        });

        startTime = Date.now();
        duration = formData.duration;

    } catch (error) {
        addLog('Error starting attack: ' + error.message, 'error');
        alert('Failed to start attack: ' + error.message);
    }
}

// Stop attack
async function stopAttack() {
    if (!currentSessionId) return;

    try {
        const response = await fetch(`/api/attack/stop/${currentSessionId}`, {
            method: 'POST'
        });

        if (response.ok) {
            addLog('Attack stopped by user', 'warning');
            onAttackComplete();
        }
    } catch (error) {
        addLog('Error stopping attack: ' + error.message, 'error');
    }
}

// On attack complete
function onAttackComplete() {
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    document.getElementById('attackForm').querySelectorAll('input, select').forEach(el => {
        el.disabled = false;
    });

    if (websocket) {
        websocket.close();
    }

    startTime = null;
    currentSessionId = null;
}

// Download proxies
async function downloadProxies() {
    const proxyType = document.getElementById('proxyType').value;

    addLog(`Downloading ${proxyType.toUpperCase()} proxies...`, 'info');

    try {
        const response = await fetch('/api/proxy/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                proxy_type: proxyType,
                validate: true
            })
        });

        if (!response.ok) {
            throw new Error('Download failed');
        }

        const data = await response.json();
        addLog(
            `Downloaded ${data.total_downloaded} proxies, ${data.working} working`,
            'success'
        );

    } catch (error) {
        addLog('Error downloading proxies: ' + error.message, 'error');
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    initCharts();

    // Form submission
    document.getElementById('attackForm').addEventListener('submit', (e) => {
        e.preventDefault();

        const formData = {
            target_url: document.getElementById('targetUrl').value,
            mode: document.getElementById('mode').value,
            threads: parseInt(document.getElementById('threads').value),
            duration: parseInt(document.getElementById('duration').value),
            proxy_type: document.getElementById('proxyType').value,
            use_http2: document.getElementById('useHttp2').checked,
            simulation_mode: document.getElementById('simulationMode').checked,
            whitelist: document.getElementById('whitelist').value
                .split(',')
                .map(s => s.trim())
                .filter(s => s),
            authorization_token: document.getElementById('authToken').value || null
        };

        // Validation
        if (!formData.simulation_mode && !formData.authorization_token) {
            alert('Authorization token required for real attacks!');
            return;
        }

        // Confirm real attack
        if (!formData.simulation_mode) {
            if (!confirm('⚠️ WARNING: You are about to launch a REAL attack.\n\nDo you have written authorization to test this target?')) {
                return;
            }
        }

        startAttack(formData);
    });

    // Stop button
    document.getElementById('stopBtn').addEventListener('click', stopAttack);

    // Download proxies button
    document.getElementById('downloadProxiesBtn').addEventListener('click', downloadProxies);

    // Simulation mode toggle
    document.getElementById('simulationMode').addEventListener('change', (e) => {
        const authTokenGroup = document.getElementById('authTokenGroup');
        authTokenGroup.style.display = e.target.checked ? 'none' : 'block';
    });

    // Check server status
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            addLog(`Server connected - Version ${data.version}`, 'success');
        })
        .catch(err => {
            addLog('Failed to connect to server', 'error');
        });
});
