#!/bin/bash
echo "Updating QuranBot on VPS..."
ssh -i "C:/Users/hanna/.ssh/id_rsa" root@159.89.90.90 "cd /opt/quranbot && systemctl stop quranbot && git pull && systemctl start quranbot && systemctl status quranbot" 