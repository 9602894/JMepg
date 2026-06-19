name: 拆分 EPG 并提交

on:
  schedule:
    # 每天北京时间 6:00 (UTC 22:00) 运行，可根据需要修改
    - cron: '0 22 * * *'
  workflow_dispatch:    # 允许手动触发

jobs:
  split-epg:
    runs-on: ubuntu-latest
    permissions:
      contents: write   # 授予推送权限

    steps:
      - name: 检出代码
        uses: actions/checkout@v4
        with:
          fetch-depth: 0   # 获取完整历史，便于提交

      - name: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 安装依赖
        run: |
          pip install requests

      - name: 运行拆分脚本
        run: |
          python split_epg_by_displayname.py

      - name: 检查更改并提交
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add epg_by_channel_displayname/
          # 如果有更改才提交，避免空提交
          if git diff --staged --quiet; then
            echo "没有新更改，跳过提交"
          else
            git commit -m "自动更新 EPG 拆分文件 [skip ci]"
            git push
          fi
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
