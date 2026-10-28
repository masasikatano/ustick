#!/bin/bash
# Oracle Cloud VM の cron から定期実行される更新スクリプト。
# crontab 例: 30 14 * * 2-6 ~/ustick/run_update.sh >> ~/ustick/update.log 2>&1
set -e
cd "$(dirname "$0")"

git fetch origin && git reset --hard origin/main   # リポジトリ最新化

.venv/bin/python -m src.update

git add docs/data/latest.json data/*.txt
if git diff --cached --quiet; then
  echo "no changes"
  exit 0
fi
git -c user.name="oracle-cron" -c user.email="oracle-cron@users.noreply.github.com" \
    commit -m "chore: update latest.json [skip ci]"
git push origin main
