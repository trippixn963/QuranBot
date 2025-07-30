# 🕌 QuranBot Dashboard

**Beautiful, real-time web dashboard for QuranBot monitoring and management**

*بِسْمِ اللهِ الرَّحْمٰنِ الرَّحِيْمِ - In the name of Allah, the Most Gracious, the Most Merciful*

## ✨ Features

### 🎯 **Core Dashboard Features**
- **Real-time Monitoring**: Live updates of bot status, performance, and activity
- **Islamic Design**: Beautiful Islamic-themed interface with Arabic elements
- **Responsive Layout**: Works perfectly on desktop, tablet, and mobile devices
- **Interactive Charts**: Dynamic visualizations of bot performance and usage
- **Community Leaderboard**: Track top users and Islamic knowledge quiz performance

### 📊 **Monitoring Capabilities**
- **Bot Health**: Real-time status, uptime, and connection monitoring
- **Performance Metrics**: Response times, error rates, and API usage
- **Islamic Content Stats**: Quiz questions, Quranic verses, and content categories
- **Community Analytics**: User engagement, quiz accuracy, and participation
- **System Health**: Gateway latency, database performance, and resource usage

### 🕌 **Islamic Features**
- **Arabic Typography**: Beautiful Arabic fonts and Islamic calligraphy
- **Islamic Greetings**: Traditional Arabic greetings and phrases
- **Hijri Calendar**: Islamic calendar integration (planned)
- **Prayer Times**: Mecca prayer times (planned)
- **Content Verification**: Islamic content accuracy indicators

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- QuranBot running and generating data
- Modern web browser

### Installation

1. **Install Dependencies**
   ```bash
   cd dashboard
   pip install -r requirements.txt
   ```

2. **Configure Environment** (Optional)
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start Dashboard**
   ```bash
   python run_dashboard.py
   ```

4. **Access Dashboard**
   Open your browser to: `http://localhost:5000`

### Development Mode
```bash
python run_dashboard.py --debug --env development
```

### Production Mode
```bash
python run_dashboard.py --env production --host 0.0.0.0 --port 8080
```

## 🎨 Dashboard Sections

### 1. **Overview Cards**
- **Bot Status**: Connection status, uptime, and basic metrics
- **Islamic Content**: Quiz questions and Quranic verses statistics
- **Community**: User engagement and participation metrics
- **Performance**: Response times, error rates, and health indicators

### 2. **Analytics Charts**
- **Activity Chart**: Bot activity over time with customizable timeframes
- **Quiz Categories**: Distribution of quiz questions across Islamic topics
- **Performance Trends**: Historical performance data and trends

### 3. **Community Leaderboard**
- **Top Users**: Ranked by Islamic knowledge quiz performance
- **User Statistics**: Points, streaks, and accuracy metrics
- **Community Stats**: Total participants and engagement metrics

### 4. **Recent Activity**
- **Real-time Feed**: Live updates of bot activities and events
- **Event Types**: Commands, quiz questions, verses, and system events
- **Activity History**: Searchable log of recent bot interactions

## ⚙️ Configuration

### Environment Variables

```bash
# Flask Configuration
FLASK_ENV=development|production|testing
DASHBOARD_SECRET_KEY=your-secret-key-here
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=5000

# Update Settings  
DASHBOARD_REFRESH_INTERVAL=5
CHART_UPDATE_INTERVAL=15
DASHBOARD_MAX_HISTORY=100

# Islamic Features
SHOW_ARABIC_TEXT=True
SHOW_HIJRI_DATE=True
REQUIRE_ARABIC_CONTENT=True

# Security (Production)
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
RATE_LIMIT_ENABLED=True
RATE_LIMIT_DEFAULT=100 per hour

# Monitoring Thresholds
RESPONSE_TIME_WARNING=500
RESPONSE_TIME_CRITICAL=1000
ERROR_RATE_WARNING=5
ERROR_RATE_CRITICAL=10
```

### Dashboard Themes

The dashboard supports multiple Islamic themes:

- **Default Islamic**: Teal and green Islamic colors
- **Ramadan Night**: Purple and gold for Ramadan
- **Hajj Gold**: Gold and orange for Hajj season

## 🔧 API Endpoints

### Core Data Endpoints
- `GET /api/overview` - Dashboard overview data
- `GET /api/leaderboard` - Community leaderboard
- `GET /api/content` - Islamic content statistics
- `GET /api/performance` - Performance metrics

### WebSocket Events
- `connect` - Client connection
- `dashboard_update` - Real-time data updates  
- `request_update` - Manual update request

## 🔒 Security Features

### Production Security
- **HTTPS Support**: SSL/TLS encryption
- **CORS Protection**: Configurable cross-origin policies
- **Rate Limiting**: API endpoint protection
- **Security Headers**: XSS, CSRF, and clickjacking protection
- **Content Security Policy**: Script and resource restrictions

### Data Protection
- **Local Data Only**: No external data transmission
- **Encrypted Sessions**: Secure session management
- **Access Control**: Admin-only features (planned)

## 🎯 Islamic Design Philosophy

### Visual Elements
- **Color Palette**: Inspired by Islamic art and calligraphy
- **Typography**: Combination of modern sans-serif and traditional Arabic fonts
- **Layout**: Clean, organized design respecting Islamic aesthetics
- **Icons**: Islamic symbols and mosque iconography

### Content Presentation
- **Arabic Text**: Proper RTL support and Arabic typography
- **Islamic Greetings**: Traditional greetings in Arabic and English
- **Respectful Language**: Islamic terminology and respectful expressions
- **Community Focus**: Emphasis on Ummah and collective benefit

## 📱 Responsive Design

### Desktop (1200px+)
- Full-width layout with sidebar navigation
- Multi-column card layout
- Large charts and detailed statistics
- Complete feature set

### Tablet (768px - 1199px)
- Adaptive grid layout
- Collapsed navigation
- Optimized chart sizes
- Touch-friendly interface

### Mobile (< 768px)
- Single-column layout
- Simplified navigation
- Mobile-optimized charts
- Essential features only

## 🔄 Real-time Updates

### WebSocket Connection
- **Automatic Reconnection**: Handles connection drops gracefully
- **Live Data Streaming**: Real-time updates without page refresh
- **Connection Status**: Visual indicators for connection health
- **Fallback Polling**: HTTP fallback if WebSocket fails

### Update Frequency
- **Overview Data**: Every 5 seconds
- **Charts**: Every 15 seconds  
- **Activity Feed**: Real-time
- **Leaderboard**: Every 30 seconds

## 🚀 Deployment

### Development
```bash
# Simple development server
python run_dashboard.py --debug

# With custom host/port
python run_dashboard.py --host 127.0.0.1 --port 3000 --debug
```

### Production with Gunicorn
```bash
# Install Gunicorn
pip install gunicorn eventlet

# Run with Gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 dashboard.app:app
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY dashboard/ .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "run_dashboard.py", "--env", "production"]
```

### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name dashboard.quranbot.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔍 Troubleshooting

### Common Issues

**Dashboard not loading data:**
- Ensure QuranBot is running and generating data
- Check database path in configuration
- Verify data directory permissions

**WebSocket connection failed:**
- Check firewall settings
- Verify port accessibility  
- Try HTTP fallback mode

**Charts not updating:**
- Check browser console for JavaScript errors
- Verify API endpoints are accessible
- Clear browser cache

**Performance issues:**
- Reduce update frequencies in config
- Check server resources
- Optimize database queries

### Debug Mode
```bash
# Enable verbose logging
python run_dashboard.py --debug --env development

# Check logs
tail -f dashboard/logs/dashboard.log
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Install development dependencies
4. Make your changes
5. Test thoroughly
6. Submit a pull request

### Islamic Content Guidelines
- Ensure Arabic text is authentic and properly formatted
- Verify Islamic references with scholarly sources
- Maintain respectful Islamic terminology
- Test RTL layout and Arabic typography

## 📞 Support

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Community support and questions
- **Documentation**: Comprehensive setup guides
- **Discord Community**: Real-time community support

### Islamic Content Review
All Islamic content and design elements are reviewed for authenticity and respect. Community scholars and knowledgeable members help verify Islamic accuracy.

---

**🕌 May Allah accept this work and make it beneficial for the Islamic community.**

*This dashboard is created as an act of worship and service to Allah, with the intention of supporting the global Muslim Ummah through modern technology.*

**بارك الله فيكم - May Allah bless you all**

---

**Latest Update**: Dashboard v1.0.0  
**Compatibility**: QuranBot v2.4+  
**License**: Community Service License  
**Language**: Python 3.9+ / JavaScript ES6+