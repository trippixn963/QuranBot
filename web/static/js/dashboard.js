// =============================================================================
// QuranBot Professional Web Dashboard - JavaScript
// =============================================================================

class QuranBotDashboard {
    constructor() {
        this.updateInterval = null;
        this.isUpdating = false;
        this.retryCount = 0;
        this.maxRetries = 3;
        this.updateFrequency = 5000; // 5 seconds
        this.charts = {};
        this.notifications = [];
        
        this.init();
    }

    init() {
        console.log('🕌 QuranBot Dashboard initializing...');
        
        // Initialize components
        this.setupEventListeners();
        this.initializeCharts();
        this.startRealTimeUpdates();
        this.setupNotifications();
        
        // Initial data load
        this.updateAllData();
        
        console.log('✅ Dashboard initialized successfully');
    }

    setupEventListeners() {
        // Bot control buttons
        document.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const type = e.target.dataset.type || 'bot';
                this.handleControlAction(type, action, e.target);
            });
        });

        // Audio controls
        document.querySelectorAll('[data-audio-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.target.dataset.audioAction;
                this.handleAudioControl(action, e.target);
            });
        });

        // Volume control
        const volumeSlider = document.getElementById('volume-slider');
        if (volumeSlider) {
            volumeSlider.addEventListener('input', (e) => {
                this.handleVolumeChange(e.target.value);
            });
        }

        // Log search and filters
        const logSearch = document.getElementById('log-search');
        if (logSearch) {
            logSearch.addEventListener('input', (e) => {
                this.filterLogs(e.target.value);
            });
        }

        // Page visibility API for performance
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseUpdates();
            } else {
                this.resumeUpdates();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'r':
                        e.preventDefault();
                        this.forceUpdate();
                        break;
                    case 'p':
                        e.preventDefault();
                        this.toggleUpdates();
                        break;
                }
            }
        });
    }

    async handleControlAction(type, action, button) {
        if (button.disabled) return;

        this.setButtonLoading(button, true);
        
        try {
            const response = await fetch(`/api/${type}/control`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification(`${type} ${action} successful`, 'success');
                this.updateAllData(); // Refresh data immediately
            } else {
                throw new Error(result.error || `Failed to ${action} ${type}`);
            }
        } catch (error) {
            console.error(`Error controlling ${type}:`, error);
            this.showNotification(`Error: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    async handleAudioControl(action, button) {
        this.setButtonLoading(button, true);
        
        try {
            const response = await fetch('/api/audio/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification(`Audio ${action} successful`, 'success');
                this.updateAudioStatus();
            } else {
                throw new Error(result.error || `Failed to ${action} audio`);
            }
        } catch (error) {
            console.error('Error controlling audio:', error);
            this.showNotification(`Audio error: ${error.message}`, 'error');
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    async handleVolumeChange(volume) {
        try {
            const response = await fetch('/api/audio/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: 'volume', value: parseInt(volume) })
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                document.getElementById('volume-display').textContent = `${volume}%`;
            }
        } catch (error) {
            console.error('Error setting volume:', error);
        }
    }

    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.innerHTML = '<span class="loading"></span> Processing...';
        } else {
            button.disabled = false;
            // Restore original text (you might want to store this)
            const action = button.dataset.action || button.dataset.audioAction;
            button.innerHTML = this.getButtonText(action);
        }
    }

    getButtonText(action) {
        const buttonTexts = {
            'start': '▶️ Start',
            'stop': '⏹️ Stop',
            'restart': '🔄 Restart',
            'play': '▶️ Play',
            'pause': '⏸️ Pause',
            'skip': '⏭️ Skip'
        };
        return buttonTexts[action] || action;
    }

    startRealTimeUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        this.updateInterval = setInterval(() => {
            this.updateAllData();
        }, this.updateFrequency);

        console.log(`🔄 Real-time updates started (${this.updateFrequency}ms interval)`);
    }

    pauseUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
            console.log('⏸️ Updates paused');
        }
    }

    resumeUpdates() {
        if (!this.updateInterval) {
            this.startRealTimeUpdates();
            console.log('▶️ Updates resumed');
        }
    }

    toggleUpdates() {
        if (this.updateInterval) {
            this.pauseUpdates();
        } else {
            this.resumeUpdates();
        }
    }

    forceUpdate() {
        this.showNotification('Refreshing data...', 'info');
        this.updateAllData();
    }

    async updateAllData() {
        if (this.isUpdating) return;
        this.isUpdating = true;

        try {
            await Promise.all([
                this.updateBotStatus(),
                this.updateQuizStats(),
                this.updateListeningStats(),
                this.updateLogs(),
                this.updateDiscordHealth()
            ]);

            this.retryCount = 0;
            this.updateTimestamp();
        } catch (error) {
            console.error('Error updating data:', error);
            this.handleUpdateError(error);
        } finally {
            this.isUpdating = false;
        }
    }

    async updateBotStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            if (response.ok) {
                this.updateBotStatusUI(data.bot);
                this.updateSystemMetricsUI(data.system);
                this.updateAudioStatusUI(data.audio);
                this.updatePerformanceMetrics(data.performance);
                this.updateStorageMetrics(data.storage);
                this.updateNetworkMetrics(data.network);
                this.updateAdditionalMetrics();
            }
        } catch (error) {
            console.error('Error updating bot status:', error);
        }
    }

    updateBotStatusUI(status) {
        const statusBadge = document.getElementById('status-badge');
        const statusMessage = document.getElementById('bot-status');
        const uptimeElement = document.getElementById('uptime');
        const memoryElement = document.getElementById('memory');

        if (statusBadge) {
            statusBadge.className = `status-badge ${status.online ? 'status-online' : 'status-offline'}`;
            statusBadge.textContent = status.online ? 'Online' : 'Offline';
        }

        if (statusMessage) {
            statusMessage.textContent = status.status || 'Unknown';
            statusMessage.className = `metric-value ${status.online ? 'success' : 'error'}`;
        }

        if (uptimeElement) {
            uptimeElement.textContent = status.uptime || 'Unknown';
        }

        if (memoryElement) {
            memoryElement.textContent = status.memory || 'Unknown';
        }
    }

    updateSystemMetricsUI(metrics) {
        if (metrics.error) return;

        this.updateMetric('cpu-usage', `${metrics.cpu_percent?.toFixed(1)}%`);
        this.updateMetric('memory-usage', `${metrics.memory_percent?.toFixed(1)}%`);
        this.updateMetric('disk-usage', `${metrics.disk_percent?.toFixed(1)}%`);

        this.updateProgressBar('cpu-progress', metrics.cpu_percent);
        this.updateProgressBar('memory-progress', metrics.memory_percent);
        this.updateProgressBar('disk-progress', metrics.disk_percent);
    }

    updateAudioStatusUI(audio) {
        if (audio.error) return;

        this.updateMetric('current-surah', audio.current_surah || 'None');
        this.updateMetric('voice-channel', audio.voice_channel || 'Not connected');
        this.updateMetric('audio-status', audio.playing ? 'Playing' : 'Stopped');

        const volumeSlider = document.getElementById('volume-slider');
        const volumeDisplay = document.getElementById('volume-display');
        
        if (volumeSlider && audio.volume !== undefined) {
            volumeSlider.value = audio.volume;
        }
        
        if (volumeDisplay && audio.volume !== undefined) {
            volumeDisplay.textContent = `${audio.volume}%`;
        }
    }

    updateAdditionalMetrics() {
        console.log('🔧 Updating additional metrics...');
        // Update placeholder metrics that don't have specific API endpoints
        this.updateMetric('process-id', 'N/A');
        this.updateMetric('system-uptime', 'N/A');
    }

    updatePerformanceMetrics(performance) {
        if (!performance) return;
        
        console.log('⚡ Updating performance metrics:', performance);
        this.updateMetric('response-time', performance.response_time);
        this.updateMetric('requests-per-min', performance.requests_per_min);
        this.updateMetric('error-rate', performance.error_rate);
    }

    updateStorageMetrics(storage) {
        if (!storage) return;
        
        console.log('💾 Updating storage metrics:', storage);
        this.updateMetric('log-files', storage.log_files);
        this.updateMetric('audio-cache', storage.audio_cache);
        this.updateMetric('db-size', storage.database_size);
    }

    updateNetworkMetrics(network) {
        if (!network) return;
        
        console.log('🌐 Updating network metrics:', network);
        this.updateMetric('vps-connection', network.vps_connection);
        this.updateMetric('gateway-status', network.discord_gateway);
        this.updateMetric('api-endpoints', network.api_endpoints);
    }

    async updateQuizStats() {
        try {
            console.log('📊 Updating quiz stats...');
            const response = await fetch('/api/quiz/stats');
            const stats = await response.json();

            if (response.ok && !stats.error) {
                console.log('📊 Quiz stats received:', stats);
                console.log('📊 Updating quiz metrics...');
                this.updateMetric('quiz-questions', stats.total_questions || 0);
                this.updateMetric('quiz-accuracy', `${(stats.accuracy_rate || 0).toFixed(1)}%`);
                this.updateMetric('quiz-users', stats.total_users || 0);
                this.updateMetric('quiz-today', stats.questions_today || 0);
                this.updateLeaderboard(stats.top_users || []);
                this.updateRecentActivity(stats.recent_activity || []);
                this.updateQuizChart(stats);
                console.log('📊 Quiz stats update complete');
            } else {
                console.error('📊 Quiz stats error:', stats);
            }
        } catch (error) {
            console.error('Error updating quiz stats:', error);
        }
    }

    async updateListeningStats() {
        try {
            console.log('🎧 Updating listening stats...');
            const response = await fetch('/api/listening/stats');
            const stats = await response.json();

            if (response.ok && !stats.error) {
                console.log('🎧 Listening stats received:', stats);
                console.log('🎧 Updating listening metrics...');
                this.updateMetric('listening-time', this.formatTime(stats.total_listening_time || 0));
                this.updateMetric('active-listeners', stats.active_listeners || 0);
                this.updateMetric('sessions-today', stats.sessions_today || 0);
                this.updateMetric('average-session', this.formatTime(stats.average_session_time || 0));
                this.updateListeningChart(stats.daily_stats || {});
                console.log('🎧 Listening stats update complete');
            } else {
                console.error('🎧 Listening stats error:', stats);
            }
        } catch (error) {
            console.error('Error updating listening stats:', error);
        }
    }

    async updateLogs() {
        try {
            const response = await fetch('/api/logs?lines=50');
            const data = await response.json();

            if (response.ok && data.logs) {
                this.updateLogsUI(data.logs);
            }
        } catch (error) {
            console.error('Error updating logs:', error);
        }
    }

    updateLogsUI(logs) {
        const logsContainer = document.getElementById('logs-content');
        if (!logsContainer) return;

        logsContainer.innerHTML = logs.map(log => {
            let className = 'log-entry';
            if (log.toLowerCase().includes('error')) className += ' log-error';
            else if (log.toLowerCase().includes('warning')) className += ' log-warning';
            else if (log.toLowerCase().includes('success')) className += ' log-success';
            else className += ' log-info';

            return `<div class="${className}">${this.escapeHtml(log)}</div>`;
        }).join('');

        // Auto-scroll to bottom
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    async updateDiscordHealth() {
        try {
            console.log('🔗 Updating Discord health...');
            const response = await fetch('/api/discord/health');
            const health = await response.json();

            if (response.ok && !health.error) {
                console.log('🔗 Discord health received:', health);
                console.log('🔗 Updating Discord metrics...');
                this.updateMetric('discord-status', health.status || 'Unknown');
                this.updateMetric('discord-latency', `${(health.latency || 0).toFixed(0)}ms`);
                this.updateMetric('discord-rate-limit', `${((health.rate_limit_usage || 0) * 100).toFixed(1)}%`);
                this.updateMetric('gateway-connection', health.gateway_status || 'Unknown');
                this.updateMetric('gateway-reconnects', health.reconnects || 0);
                console.log('🔗 Discord health update complete');
            } else {
                console.error('🔗 Discord health error:', health);
            }
        } catch (error) {
            console.error('Error updating Discord health:', error);
        }
    }

    updateMetric(id, value) {
        const element = document.getElementById(id);
        if (element) {
            console.log(`✅ Updated metric ${id} to: ${value}`);
            element.textContent = value;
        } else {
            console.warn(`❌ Could not find element with id: ${id}`);
        }
    }

    updateProgressBar(id, percentage) {
        const element = document.getElementById(id);
        if (element) {
            element.style.width = `${Math.min(percentage || 0, 100)}%`;
        }
    }

    updateLeaderboard(users) {
        const container = document.getElementById('leaderboard-container');
        if (!container) return;

        container.innerHTML = users.slice(0, 5).map((user, index) => {
            const medals = ['🥇', '🥈', '🥉'];
            const isMedal = index < 3;
            const rankDisplay = isMedal ? medals[index] : `#${index + 1}`;
            const displayName = user.display_name || `User ${user.user_id?.slice(0, 8) || 'Unknown'}...`;
            const avatarUrl = user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png';
            const accuracy = (user.accuracy || 0).toFixed(1);
            const correctAnswers = user.correct_answers || 0;
            const totalQuestions = user.total_questions || 0;
            const points = user.points || 0;
            
            return `
                <div class="leaderboard-entry">
                    <div class="leaderboard-rank ${isMedal ? 'medal' : ''}">${rankDisplay}</div>
                    <div class="leaderboard-user">
                        <div class="leaderboard-user-info">
                            <img src="${avatarUrl}" alt="${displayName}" class="leaderboard-avatar">
                            <span class="leaderboard-username">${this.escapeHtml(displayName)}</span>
                        </div>
                        <div class="leaderboard-stats">
                            <span>${correctAnswers}/${totalQuestions} questions</span>
                            <span class="leaderboard-accuracy">${accuracy}% accuracy</span>
                        </div>
                    </div>
                    <div class="leaderboard-points">${points.toLocaleString()}pts</div>
                </div>
            `;
        }).join('');
    }

    updateRecentActivity(activities) {
        const container = document.getElementById('activity-feed');
        if (!container) return;

        if (activities.length === 0) {
            container.innerHTML = '<div class="activity-entry">No recent activity</div>';
            return;
        }

        container.innerHTML = activities.slice(0, 5).map(activity => {
            const displayName = activity.display_name || `User ${activity.user_id?.slice(0, 8) || 'Unknown'}...`;
            const avatarUrl = activity.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png';
            const timeAgo = this.formatTimeAgo(activity.timestamp);
            
            return `
                <div class="activity-entry">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <img src="${avatarUrl}" alt="${displayName}" style="width: 20px; height: 20px; border-radius: 50%; object-fit: cover;">
                        <div>
                            <div style="font-size: 0.9rem;"><strong>${this.escapeHtml(displayName)}</strong> ${activity.action}</div>
                            <div style="font-size: 0.8rem; color: #888;">${timeAgo} • ${activity.points} points</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    updateTimestamp() {
        const timestampElements = document.querySelectorAll('.timestamp');
        const now = new Date().toLocaleString();
        timestampElements.forEach(el => {
            el.textContent = `Last updated: ${now}`;
        });
    }

    filterLogs(searchTerm) {
        const logEntries = document.querySelectorAll('.log-entry');
        const term = searchTerm.toLowerCase();

        logEntries.forEach(entry => {
            const text = entry.textContent.toLowerCase();
            entry.style.display = text.includes(term) ? 'block' : 'none';
        });
    }

    initializeCharts() {
        console.log('📊 Initializing charts...');
        this.initializeQuizChart();
        this.initializeListeningChart();
    }

    initializeQuizChart() {
        const ctx = document.getElementById('quiz-performance-chart');
        if (!ctx) return;

        this.quizChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Correct', 'Incorrect'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: ['#27ae60', '#e74c3c'],
                    borderColor: ['#2ecc71', '#c0392b'],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#ecf0f1',
                            font: {
                                size: 12
                            }
                        }
                    }
                }
            }
        });
    }

    initializeListeningChart() {
        const ctx = document.getElementById('listening-trends-chart');
        if (!ctx) return;

        this.listeningChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['6h ago', '5h ago', '4h ago', '3h ago', '2h ago', '1h ago', 'Now'],
                datasets: [{
                    label: 'Listening Time (minutes)',
                    data: [0, 0, 0, 0, 0, 0, 0],
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#ecf0f1',
                            font: {
                                size: 12
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#ecf0f1'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#ecf0f1'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }

    updateQuizChart(stats) {
        if (!this.quizChart || !stats) return;

        const correct = stats.correct_answers || 0;
        const total = stats.total_questions || 0;
        const incorrect = total - correct;

        this.quizChart.data.datasets[0].data = [correct, incorrect];
        this.quizChart.update();
    }

    updateListeningChart(stats) {
        if (!this.listeningChart || !stats) return;

        // Generate sample data based on total listening time
        const totalTime = stats.total_listening_time || 0;
        const avgPerHour = totalTime / 24; // Rough average per hour
        
        // Create sample hourly data with some variation
        const hourlyData = [];
        for (let i = 0; i < 7; i++) {
            const variation = (Math.random() - 0.5) * 0.4; // ±20% variation
            const value = Math.max(0, (avgPerHour * (1 + variation)) / 60); // Convert to minutes
            hourlyData.push(Math.round(value));
        }

        this.listeningChart.data.datasets[0].data = hourlyData;
        this.listeningChart.update();
    }

    setupNotifications() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                pointer-events: none;
            `;
            document.body.appendChild(container);
        }
    }

    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notification-container');
        if (!container) return;

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            background: var(--${type === 'error' ? 'accent' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info'}-color);
            color: white;
            padding: 15px 20px;
            border-radius: var(--border-radius);
            margin-bottom: 10px;
            box-shadow: var(--shadow-light);
            pointer-events: auto;
            transform: translateX(100%);
            transition: var(--transition);
            max-width: 300px;
            word-wrap: break-word;
        `;

        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span>${this.getNotificationIcon(type)}</span>
                <span>${this.escapeHtml(message)}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="
                    background: none;
                    border: none;
                    color: white;
                    cursor: pointer;
                    font-size: 1.2rem;
                    margin-left: auto;
                ">×</button>
            </div>
        `;

        container.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // Auto-remove
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 300);
            }
        }, duration);
    }

    getNotificationIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    }

    handleUpdateError(error) {
        this.retryCount++;
        
        if (this.retryCount <= this.maxRetries) {
            console.log(`🔄 Retrying update (${this.retryCount}/${this.maxRetries})`);
            setTimeout(() => this.updateAllData(), 2000);
        } else {
            console.error('❌ Max retries reached, stopping updates');
            this.showNotification('Connection lost. Please refresh the page.', 'error');
            this.pauseUpdates();
        }
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }

    formatTimeAgo(timestamp) {
        if (!timestamp) return 'Unknown';
        
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diffMs = now - date;
            const diffMinutes = Math.floor(diffMs / (1000 * 60));
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            if (diffMinutes < 1) return 'Just now';
            if (diffMinutes < 60) return `${diffMinutes}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            return date.toLocaleDateString();
        } catch (e) {
            return 'Unknown';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Cleanup method
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        console.log('🧹 Dashboard cleanup completed');
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new QuranBotDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
});

// Service Worker registration for offline support (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(registration => {
                console.log('📱 Service Worker registered');
            })
            .catch(error => {
                console.log('Service Worker registration failed');
            });
    });
} 