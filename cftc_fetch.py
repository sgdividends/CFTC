name: Fetch CFTC leveraged funds data

on:
  schedule:
    # CFTC releases COT data Fridays ~3:30pm ET (covering prior Tuesday's
    # positions). Run at 21:30 UTC to clear both EST (8:30pm ET) and EDT
    # (5:30pm ET) with margin. Occasionally shifts for holidays -- if a
    # Friday is a market holiday, CFTC delays release; a failed/empty run
    # that week is expected, not a bug.
    - cron: '30 21 * * 5'
  workflow_dispatch: {}  # allows manual trigger from the Actions tab

permissions:
  contents: write

jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run fetch script
        run: python cftc_fetch.py

      - name: Commit updated data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/cftc/sp500_leveraged_funds.csv
          git diff --quiet --cached || git commit -m "Update CFTC leveraged funds data"
          git push
