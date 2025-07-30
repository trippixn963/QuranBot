// =============================================================================
// QuranBot Dashboard JavaScript
// =============================================================================
// Interactive dashboard functionality with real-time updates and Islamic features
// =============================================================================

class QuranBotDashboard {
    constructor() {
        this.socket = null;
        this.charts = {};
        this.lastUpdate = null;
        this.updateInterval = null;
        
        // Initialize dashboard
        this.init();
    }

    // =============================================================================
    // Initialization
    // =============================================================================
    
    init() {
        console.log('🕌 Initializing QuranBot Dashboard...');
        
        // Setup WebSocket connection
        this.setupWebSocket();
        
        // Setup event listeners
        this.setupEventListeners();
        this.setupEnhancedEventListeners();
        
        // Initialize charts
        this.initializeCharts();
        
        // Setup periodic updates
        this.setupPeriodicUpdates();
        
        // Load initial data
        this.loadInitialData();
        
        // Start time display
        this.startTimeDisplay();
        
        console.log('✅ Dashboard initialized successfully');
    }

    // =============================================================================
    // WebSocket Setup
    // =============================================================================
    
    setupWebSocket() {
        try {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('🔗 Connected to QuranBot Dashboard');
                this.updateConnectionStatus('connected');
                this.hideLoading();
            });
            
            this.socket.on('disconnect', () => {
                console.log('🔌 Disconnected from QuranBot Dashboard');
                this.updateConnectionStatus('disconnected');
            });
            
            this.socket.on('dashboard_update', (data) => {
                console.log('📊 Received dashboard update');
                this.updateDashboard(data);
            });
            
            this.socket.on('error', (error) => {
                console.error('❌ WebSocket error:', error);
                this.updateConnectionStatus('error');
            });
            
        } catch (error) {
            console.error('❌ Failed to setup WebSocket:', error);
            this.updateConnectionStatus('error');
            this.hideLoading();
        }
    }

    // =============================================================================
    // Event Listeners
    // =============================================================================
    
    setupEventListeners() {
        // Activity timeframe selector
        const activityTimeframe = document.getElementById('activity-timeframe');
        if (activityTimeframe) {
            activityTimeframe.addEventListener('change', (e) => {
                this.updateActivityChart(e.target.value);
            });
        }
        
        // Manual refresh button (if added)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                this.refreshDashboard();
            }
        });
    }

    // =============================================================================
    // Data Loading
    // =============================================================================
    
    async loadInitialData() {
        try {
            console.log('📥 Loading initial dashboard data...');
            
            // Load overview data
            const overviewResponse = await fetch('/api/overview');
            const overviewData = await overviewResponse.json();
            
            // Load leaderboard data
            const leaderboardResponse = await fetch('/api/leaderboard');
            const leaderboardData = await leaderboardResponse.json();
            
            // Load content data
            const contentResponse = await fetch('/api/content');
            const contentData = await contentResponse.json();
            
            // Update dashboard with initial data
            this.updateDashboard(overviewData);
            this.updateLeaderboard(leaderboardData);
            this.updateContentCharts(contentData);
            
            // Load enhanced features
            await this.loadEnhancedData();
            
            console.log('✅ Initial data loaded successfully');
            
        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    // =============================================================================
    // Dashboard Updates
    // =============================================================================
    
    updateDashboard(data) {
        try {
            // Update bot status
            this.updateBotStatus(data.bot_info);
            
            // Update Islamic content stats
            this.updateIslamicContent(data.islamic_content);
            
            // Update community stats
            this.updateCommunityStats(data.community);
            
            // Update performance metrics
            this.updatePerformanceMetrics(data.performance);
            
            // Update recent activity
            this.updateRecentActivity(data.recent_activity);
            
            // Update last updated time
            this.updateLastUpdated(data.timestamp);
            
        } catch (error) {
            console.error('❌ Failed to update dashboard:', error);
        }
    }

    updateBotStatus(botInfo) {
        if (!botInfo) return;
        
        // Bot status indicator
        const statusElement = document.getElementById('bot-status');
        if (statusElement) {
            const statusIndicator = statusElement.querySelector('.status-indicator');
            if (statusIndicator) {
                statusIndicator.className = `status-indicator ${botInfo.status}`;
                statusIndicator.textContent = botInfo.status.charAt(0).toUpperCase() + botInfo.status.slice(1);
            }
        }
        
        // Update stats
        this.updateElement('bot-uptime', this.formatUptime(botInfo.uptime_hours));
        this.updateElement('total-sessions', this.formatNumber(botInfo.total_sessions));
        this.updateElement('gateway-latency', `${this.formatNumber(botInfo.gateway_latency || 0)}ms`);
    }

    updateIslamicContent(contentInfo) {
        if (!contentInfo) return;
        
        this.updateElement('total-verses', this.formatNumber(contentInfo.total_verses));
        this.updateElement('total-quizzes', this.formatNumber(contentInfo.total_quizzes));
        this.updateElement('quiz-categories', this.formatNumber(contentInfo.quiz_categories));
        this.updateElement('verse-categories', this.formatNumber(contentInfo.verse_categories));
    }

    updateCommunityStats(communityInfo) {
        if (!communityInfo) return;
        
        this.updateElement('total-users', this.formatNumber(communityInfo.total_users));
        this.updateElement('quiz-questions-sent', this.formatNumber(communityInfo.quiz_questions_sent));
        
        // Calculate accuracy
        const accuracy = communityInfo.total_quiz_attempts > 0 
            ? (communityInfo.correct_answers / communityInfo.total_quiz_attempts * 100).toFixed(1)
            : 0;
        this.updateElement('quiz-accuracy', `${accuracy}%`);
    }

    updatePerformanceMetrics(performanceInfo) {
        if (!performanceInfo) return;
        
        this.updateElement('avg-response-time', `${performanceInfo.avg_response_time}ms`);
        this.updateElement('error-rate', `${performanceInfo.error_rate}%`);
        this.updateElement('recent-api-calls', this.formatNumber(performanceInfo.recent_calls));
        
        // Update health indicator
        const healthElement = document.getElementById('performance-health');
        if (healthElement) {
            const indicator = healthElement.querySelector('.health-indicator');
            if (indicator) {
                indicator.className = `health-indicator ${performanceInfo.system_health}`;
                indicator.textContent = performanceInfo.system_health.charAt(0).toUpperCase() + 
                                      performanceInfo.system_health.slice(1);
            }
        }
    }

    updateRecentActivity(activities) {
        if (!activities || !Array.isArray(activities)) return;
        
        const activityList = document.getElementById('activity-list');
        if (!activityList) return;
        
        activityList.innerHTML = '';
        
        activities.forEach(activity => {
            const activityItem = this.createActivityItem(activity);
            activityList.appendChild(activityItem);
        });
    }

    createActivityItem(activity) {
        const item = document.createElement('div');
        item.className = 'activity-item';
        
        const iconClass = this.getActivityIconClass(activity.severity);
        const timeAgo = this.formatTimeAgo(activity.timestamp);
        
        item.innerHTML = `
            <div class="activity-icon ${iconClass}">
                <i class="fas ${this.getActivityIcon(activity.event_type)}"></i>
            </div>
            <div class="activity-content">
                <div class="activity-type">${this.formatActivityType(activity.event_type)}</div>
                <div class="activity-data">${activity.event_data || 'No additional data'}</div>
            </div>
            <div class="activity-time">${timeAgo}</div>
        `;
        
        return item;
    }

    // =============================================================================
    // Leaderboard Updates
    // =============================================================================
    
    async updateLeaderboard(data) {
        if (!data || !data.top_users) return;
        
        const leaderboardList = document.getElementById('leaderboard-list');
        if (!leaderboardList) return;
        
        leaderboardList.innerHTML = '';
        
        data.top_users.forEach((user, index) => {
            const item = this.createLeaderboardItem(user, index + 1);
            leaderboardList.appendChild(item);
        });
    }

    createLeaderboardItem(user, rank) {
        const item = document.createElement('div');
        item.className = 'leaderboard-item';
        
        const accuracy = user.total_attempts > 0 
            ? (user.correct_answers / user.total_attempts * 100).toFixed(1)
            : 0;
        
        const rankClass = rank <= 3 ? 'rank top-3' : 'rank';
        const rankIcon = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : rank;
        
        item.innerHTML = `
            <div class="${rankClass}">${rankIcon}</div>
            <div class="user-info">
                <div class="user-name">${user.display_name || user.username || 'Unknown User'}</div>
                <div class="user-display">@${user.username || 'unknown'}</div>
            </div>
            <div class="points">${this.formatNumber(user.points)}</div>
            <div class="streak">${this.formatNumber(user.best_streak)}</div>
            <div class="accuracy">${accuracy}%</div>
        `;
        
        return item;
    }

    // =============================================================================
    // Chart Management
    // =============================================================================
    
    initializeCharts() {
        this.initializeActivityChart();
        this.initializeQuizCategoriesChart();
    }

    initializeActivityChart() {
        const canvas = document.getElementById('activity-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        this.charts.activity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Bot Activity',
                    data: [],
                    borderColor: '#1ABC9C',
                    backgroundColor: 'rgba(26, 188, 156, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                }
            }
        });
    }

    initializeQuizCategoriesChart() {
        const canvas = document.getElementById('quiz-categories-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        this.charts.quizCategories = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#1ABC9C',
                        '#3498DB',
                        '#9B59B6',
                        '#E74C3C',
                        '#F39C12',
                        '#2ECC71',
                        '#E67E22'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }

    async updateContentCharts(contentData) {
        if (!contentData) return;
        
        // Update quiz categories chart
        if (this.charts.quizCategories && contentData.quiz_data) {
            const categories = contentData.quiz_data.categories;
            if (categories) {
                const labels = Object.keys(categories);
                const data = Object.values(categories);
                
                this.charts.quizCategories.data.labels = labels;
                this.charts.quizCategories.data.datasets[0].data = data;
                this.charts.quizCategories.update();
            }
        }
    }

    // =============================================================================
    // Utility Functions
    // =============================================================================
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (!statusElement) return;
        
        const statusDot = statusElement.querySelector('.status-dot');
        const statusText = statusElement.querySelector('.status-text');
        
        if (statusDot && statusText) {
            statusElement.className = `status-indicator ${status}`;
            
            switch (status) {
                case 'connected':
                    statusText.textContent = 'Connected';
                    break;
                case 'connecting':
                    statusText.textContent = 'Connecting...';
                    break;
                case 'disconnected':
                    statusText.textContent = 'Disconnected';
                    break;
                case 'error':
                    statusText.textContent = 'Connection Error';
                    break;
                default:
                    statusText.textContent = 'Unknown';
            }
        }
    }

    updateLastUpdated(timestamp) {
        const element = document.getElementById('last-updated');
        if (element && timestamp) {
            element.textContent = new Date(timestamp).toLocaleTimeString();
        }
    }

    formatNumber(num) {
        if (num === undefined || num === null) return '0';
        return new Intl.NumberFormat().format(num);
    }

    formatUptime(hours) {
        if (!hours) return '0h';
        
        if (hours < 1) {
            return `${Math.round(hours * 60)}m`;
        } else if (hours < 24) {
            return `${Math.round(hours)}h`;
        } else {
            const days = Math.floor(hours / 24);
            const remainingHours = Math.round(hours % 24);
            return `${days}d ${remainingHours}h`;
        }
    }

    formatTimeAgo(timestamp) {
        if (!timestamp) return 'Unknown';
        
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        
        if (diffSec < 60) return 'Just now';
        if (diffMin < 60) return `${diffMin}m ago`;
        if (diffHour < 24) return `${diffHour}h ago`;
        return `${diffDay}d ago`;
    }

    getActivityIconClass(severity) {
        switch (severity?.toLowerCase()) {
            case 'error': return 'error';
            case 'warning': return 'warning';
            case 'success': return 'success';
            default: return 'info';
        }
    }

    getActivityIcon(eventType) {
        const iconMap = {
            'bot_startup': 'fa-power-off',
            'bot_shutdown': 'fa-power-off',
            'command_executed': 'fa-terminal',
            'quiz_sent': 'fa-question-circle',
            'verse_sent': 'fa-book-quran',
            'user_joined': 'fa-user-plus',
            'error': 'fa-exclamation-triangle',
            'default': 'fa-info-circle'
        };
        
        return iconMap[eventType] || iconMap.default;
    }

    formatActivityType(eventType) {
        return eventType.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    // =============================================================================
    // Time Display
    // =============================================================================
    
    startTimeDisplay() {
        this.updateTimeDisplay();
        setInterval(() => this.updateTimeDisplay(), 1000);
    }

    updateTimeDisplay() {
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            const now = new Date();
            timeElement.textContent = now.toLocaleTimeString();
        }
        
        // Update Hijri date (placeholder - would need actual Hijri conversion)
        const hijriElement = document.getElementById('hijri-date');
        if (hijriElement) {
            hijriElement.textContent = 'Hijri Date Available Soon';
        }
    }

    // =============================================================================
    // Periodic Updates
    // =============================================================================
    
    setupPeriodicUpdates() {
        // Update every 30 seconds
        this.updateInterval = setInterval(() => {
            if (this.socket && this.socket.connected) {
                this.socket.emit('request_update');
            }
        }, 30000);
    }

    // =============================================================================
    // Error Handling
    // =============================================================================
    
    showError(message) {
        console.error('Dashboard Error:', message);
        // Could implement toast notifications here
    }

    hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
        }
    }

    refreshDashboard() {
        console.log('🔄 Refreshing dashboard...');
        this.loadInitialData();
    }

    // =============================================================================
    // Historical Charts
    // =============================================================================
    
    async loadHistoricalCharts() {
        const days = document.getElementById('chart-period')?.value || 7;
        
        try {
            // Load bot performance history
            const botStatsResponse = await fetch(`/api/historical/bot-stats?days=${days}`);
            const botStatsData = await botStatsResponse.json();
            this.updateBotPerformanceChart(botStatsData.chart_data);
            
            // Load quiz activity history
            const quizStatsResponse = await fetch(`/api/historical/quiz-stats?days=${days}`);
            const quizStatsData = await quizStatsResponse.json();
            this.updateQuizActivityChart(quizStatsData.chart_data);
            
        } catch (error) {
            console.error('Error loading historical charts:', error);
        }
    }
    
    updateBotPerformanceChart(data) {
        const ctx = document.getElementById('bot-performance-chart');
        if (!ctx || !data) return;
        
        if (this.charts.botPerformance) {
            this.charts.botPerformance.destroy();
        }
        
        this.charts.botPerformance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Runtime Hours',
                    data: data.datasets.runtime_hours,
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46, 204, 113, 0.1)',
                    yAxisID: 'y'
                }, {
                    label: 'Memory Usage (MB)',
                    data: data.datasets.memory_usage,
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Bot Performance Over Time'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Runtime Hours' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Memory (MB)' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }
    
    updateQuizActivityChart(data) {
        const ctx = document.getElementById('quiz-activity-chart');
        if (!ctx || !data) return;
        
        if (this.charts.quizActivity) {
            this.charts.quizActivity.destroy();
        }
        
        this.charts.quizActivity = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Questions Sent',
                    data: data.datasets.questions_sent,
                    backgroundColor: '#3498db'
                }, {
                    label: 'Correct Answers',
                    data: data.datasets.correct_answers,
                    backgroundColor: '#2ecc71'
                }, {
                    label: 'Total Attempts',
                    data: data.datasets.attempts,
                    backgroundColor: '#f39c12'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Quiz Activity Trends'
                    }
                }
            }
        });
    }
    
    // =============================================================================
    // Live Audio Status
    // =============================================================================
    
    async loadAudioStatus() {
        try {
            const response = await fetch('/api/audio/status');
            const data = await response.json();
            this.updateAudioStatus(data.audio_status);
        } catch (error) {
            console.error('Error loading audio status:', error);
        }
    }
    
    updateAudioStatus(audioData) {
        if (!audioData) return;
        
        // Update Surah information
        const surahInfo = audioData.surah_info || {};
        this.updateElement('surah-arabic', surahInfo.name_arabic || 'الفاتحة');
        this.updateElement('surah-english', `${surahInfo.name_transliteration || 'Al-Fatihah'} - ${surahInfo.name_english || 'The Opening'}`);
        this.updateElement('current-verse', `Verse ${audioData.current_verse || 1}`);
        this.updateElement('total-verses', surahInfo.total_verses || 7);
        this.updateElement('reciter-name', audioData.reciter || 'Saad Al Ghamdi');
        
        // Update playback status
        const playIndicator = document.getElementById('play-indicator');
        const playIcon = document.getElementById('play-icon');
        const playStatus = document.getElementById('play-status');
        
        if (audioData.is_playing) {
            playIndicator.className = 'play-indicator playing';
            playIcon.className = 'fas fa-play';
            playStatus.textContent = 'Playing';
        } else {
            playIndicator.className = 'play-indicator paused';
            playIcon.className = 'fas fa-pause';
            playStatus.textContent = 'Paused';
        }
        
        // Update listeners count
        this.updateElement('listeners-count', audioData.listeners_count || 0);
        
        // Update progress bar
        const progress = audioData.total_duration_seconds > 0 
            ? (audioData.current_position_seconds / audioData.total_duration_seconds) * 100 
            : 0;
        
        const progressFill = document.getElementById('audio-progress');
        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }
        
        // Update time display
        this.updateElement('current-time', this.formatTime(audioData.current_position_seconds || 0));
        this.updateElement('total-time', this.formatTime(audioData.total_duration_seconds || 0));
    }
    
    // =============================================================================
    // User Profiles
    // =============================================================================
    
    async loadUserProfiles() {
        try {
            const response = await fetch('/api/users/activity?limit=10');
            const data = await response.json();
            this.displayUserProfiles(data.activities);
        } catch (error) {
            console.error('Error loading user profiles:', error);
        }
    }
    
    displayUserProfiles(activities) {
        const profilesGrid = document.getElementById('profiles-grid');
        if (!profilesGrid || !activities) return;
        
        // Get unique users from recent activities
        const uniqueUsers = {};
        activities.forEach(activity => {
            if (!uniqueUsers[activity.user_id]) {
                uniqueUsers[activity.user_id] = {
                    user_id: activity.user_id,
                    display_name: activity.display_name,
                    last_activity: activity.timestamp,
                    activity_count: 1
                };
            } else {
                uniqueUsers[activity.user_id].activity_count++;
            }
        });
        
        const users = Object.values(uniqueUsers).slice(0, 6);
        
        profilesGrid.innerHTML = users.map(user => `
            <div class="profile-card" onclick="dashboard.showUserProfile('${user.user_id}')">
                <div class="profile-header">
                    <div class="profile-avatar">
                        ${user.display_name ? user.display_name[0].toUpperCase() : 'U'}
                    </div>
                    <div class="profile-info">
                        <h4>${user.display_name || 'Unknown User'}</h4>
                        <div class="user-id">${user.user_id.substring(0, 8)}...</div>
                    </div>
                </div>
                <div class="profile-stats">
                    <div class="stat-item">
                        <div class="stat-value">${user.activity_count}</div>
                        <div class="stat-label">Activities</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${this.timeAgo(user.last_activity)}</div>
                        <div class="stat-label">Last Seen</div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    async showUserProfile(userId) {
        try {
            const response = await fetch(`/api/user/${userId}/profile`);
            const profileData = await response.json();
            this.displayUserProfileModal(profileData);
        } catch (error) {
            console.error('Error loading user profile:', error);
        }
    }
    
    displayUserProfileModal(profileData) {
        const modal = document.getElementById('user-profile-modal');
        const modalTitle = document.getElementById('profile-modal-title');
        const modalBody = document.getElementById('profile-modal-body');
        
        if (!modal || !modalTitle || !modalBody) return;
        
        const basicStats = profileData.basic_stats || {};
        const summary = profileData.summary || {};
        
        modalTitle.textContent = `${basicStats.display_name || basicStats.username || 'User Profile'}`;
        
        modalBody.innerHTML = `
            <div class="profile-details">
                <div class="profile-summary">
                    <h4>📊 Statistics</h4>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">${basicStats.correct_answers || 0}</div>
                            <div class="stat-label">Correct Answers</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${basicStats.total_attempts || 0}</div>
                            <div class="stat-label">Total Attempts</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${basicStats.best_streak || 0}</div>
                            <div class="stat-label">Best Streak</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${summary.total_points || 0}</div>
                            <div class="stat-label">Total Points</div>
                        </div>
                    </div>
                </div>
                
                <div class="achievements-section">
                    <h4>🏆 Achievements</h4>
                    <div class="achievements-list">
                        ${profileData.achievements && profileData.achievements.length > 0 
                            ? profileData.achievements.map(achievement => `
                                <div class="achievement-item">
                                    <strong>${achievement.achievement_name}</strong>
                                    <p>${achievement.description || ''}</p>
                                    <small>Earned: ${new Date(achievement.earned_at).toLocaleDateString()}</small>
                                </div>
                            `).join('')
                            : '<p class="no-data">No achievements yet</p>'
                        }
                    </div>
                </div>
                
                <div class="activity-section">
                    <h4>📋 Recent Activity</h4>
                    <div class="activity-timeline">
                        ${profileData.recent_activity && profileData.recent_activity.length > 0
                            ? profileData.recent_activity.slice(0, 5).map(activity => `
                                <div class="activity-item">
                                    <div class="activity-type">${this.formatActivityType(activity.activity_type)}</div>
                                    <div class="activity-time">${this.timeAgo(activity.timestamp)}</div>
                                </div>
                            `).join('')
                            : '<p class="no-data">No recent activity</p>'
                        }
                    </div>
                </div>
            </div>
        `;
        
        modal.style.display = 'block';
    }
    
    // =============================================================================
    // Enhanced Event Listeners
    // =============================================================================
    
    setupEnhancedEventListeners() {
        // Chart period selector
        const chartPeriod = document.getElementById('chart-period');
        if (chartPeriod) {
            chartPeriod.addEventListener('change', () => {
                this.loadHistoricalCharts();
            });
        }
        
        // User search
        const searchBtn = document.getElementById('search-user-btn');
        const searchInput = document.getElementById('user-search');
        
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => {
                const userId = searchInput.value.trim();
                if (userId) {
                    this.showUserProfile(userId);
                }
            });
            
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const userId = searchInput.value.trim();
                    if (userId) {
                        this.showUserProfile(userId);
                    }
                }
            });
        }
        
        // Profile modal close
        const closeBtn = document.getElementById('close-profile-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                document.getElementById('user-profile-modal').style.display = 'none';
            });
        }
        
        // Activity refresh button
        const refreshBtn = document.getElementById('refresh-activity');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                refreshBtn.classList.add('loading');
                this.loadData().finally(() => {
                    refreshBtn.classList.remove('loading');
                });
            });
        }
        
        // Modal click outside to close
        window.addEventListener('click', (e) => {
            const modal = document.getElementById('user-profile-modal');
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    // =============================================================================
    // Utility Functions
    // =============================================================================
    
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    timeAgo(timestamp) {
        if (!timestamp) return 'Never';
        
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }
    
    formatActivityType(type) {
        const types = {
            'quiz_answered': '🧠 Quiz Answered',
            'achievement_earned': '🏆 Achievement',
            'voice_joined': '🎵 Joined Voice',
            'voice_left': '👋 Left Voice',
            'command_used': '⚡ Command Used'
        };
        return types[type] || '📋 Activity';
    }
    
    // Enhanced load data method
    async loadEnhancedData() {
        await Promise.all([
            this.loadAudioStatus(),
            this.loadHistoricalCharts(),
            this.loadUserProfiles()
        ]);
    }
    
    // =============================================================================
    // Cleanup
    // =============================================================================
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.socket) {
            this.socket.disconnect();
        }
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// =============================================================================
// Initialize Dashboard
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🕌 QuranBot Dashboard - بِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيْمِ');
    
    // Create global dashboard instance
    window.quranBotDashboard = new QuranBotDashboard();
    
    // Handle page unload
    window.addEventListener('beforeunload', () => {
        if (window.quranBotDashboard) {
            window.quranBotDashboard.destroy();
        }
    });
});

// =============================================================================
// Service Worker Registration (for PWA capabilities)
// =============================================================================

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((registration) => {
                console.log('📱 Service Worker registered successfully');
            })
            .catch((error) => {
                console.log('❌ Service Worker registration failed:', error);
            });
    });
}