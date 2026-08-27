#!/bin/bash
set -e
cd /root/sales_dashboard
source /root/sales_dashboard/dash_env.sh

python3 dashboard.py > /root/sales_dashboard/update.log 2>&1

if [ -n "$(git status --porcelain docs/)" ]; then
  git add docs/
  git commit -m "Avtomat yangilash: $(TZ='Asia/Tashkent' date '+%d.%m.%Y %H:%M')" >> /root/sales_dashboard/update.log 2>&1
  git pull --rebase -X ours >> /root/sales_dashboard/update.log 2>&1
  git push >> /root/sales_dashboard/update.log 2>&1
  echo "$(TZ='Asia/Tashkent' date '+%H:%M') - yangilandi" >> /root/sales_dashboard/update.log
else
  echo "$(TZ='Asia/Tashkent' date '+%H:%M') - ozgarish yoq" >> /root/sales_dashboard/update.log
fi
