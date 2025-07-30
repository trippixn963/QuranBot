#!/bin/bash
cd /root/quranbot/dashboard
source venv/bin/activate
exec python run_dashboard.py --no-checks --env production --host 0.0.0.0 --port 5000