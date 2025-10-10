# Production Runbook - Arizona U12 Soccer Rankings

## 🚨 **Emergency Procedures**

### **Service Level Objectives (SLOs)**
- **Daily scrape success rate**: ≥ 99%
- **Rankings job completion**: By 6:00 AM Phoenix time
- **Alert acknowledgment**: < 30 minutes
- **Data freshness**: < 24 hours old

### **Critical Alerts & Response**

#### **🔴 CRITICAL: Scrape Failure (>20% error rate)**
```bash
# 1. Check logs
tail -f scraper.log

# 2. Manual scrape attempt
python scraper_daily.py

# 3. If still failing, switch to legacy mode
export RANKING_INPUT_MODE=legacy
python generate_team_rankings_v2.py

# 4. Notify team via Slack
```

#### **🟡 WARNING: High Unresolved Teams (>10)**
```bash
# 1. Check review queue
cat data_ingest/silver/team_resolution_review.csv

# 2. Open alias operations UI
streamlit run alias_ops_ui.py

# 3. Process review queue items
# 4. Re-run scraper after fixes
```

#### **🟡 WARNING: No New Games (Weekend)**
```bash
# 1. Verify source URLs are accessible
curl -I "https://system.gotsport.com/api/v1/team_ranking_data?search[team_association]=AZ"

# 2. Check if leagues are on break
# 3. Update configuration if needed
```

## 📋 **Daily Operations**

### **Morning Checklist (6:00 AM Phoenix)**
- [ ] Check Slack for daily scrape summary
- [ ] Verify rankings published successfully
- [ ] Check for any anomalies in metrics
- [ ] Review unresolved teams count

### **Weekly Maintenance**
- [ ] Review alias operations UI for pending items
- [ ] Check backup integrity
- [ ] Review error logs for patterns
- [ ] Update team aliases based on review queue

## 🔧 **Common Operations**

### **Reprocess a Day**
```bash
# 1. Identify the problematic date
grep "2025-10-08" scraper.log

# 2. Clear Gold layer for that date
rm data_ingest/gold/All_Games_v20251008.parquet

# 3. Re-run scraper
python scraper_daily.py

# 4. Regenerate rankings
python generate_team_rankings_v2.py
```

### **Backfill a Week**
```bash
# 1. Create backfill script
cat > backfill_week.py << 'EOF'
import datetime as dt
from scraper_enhanced import enhanced_daily_run

# Run for each day of the week
for i in range(7):
    date = dt.datetime.now() - dt.timedelta(days=i)
    print(f"Backfilling {date.strftime('%Y-%m-%d')}")
    enhanced_daily_run()
EOF

# 2. Execute backfill
python backfill_week.py
```

### **Rotate Slack Webhook**
```bash
# 1. Update configuration
vim scraper_config.py
# Change ALERTS["slack_webhook"] to new URL

# 2. Test new webhook
python -c "
import scraper_config as cfg
import requests
requests.post(cfg.ALERTS['slack_webhook'], 
             json={'text': 'Test message from rankings system'})
"

# 3. Deploy change
git add scraper_config.py
git commit -m "Update Slack webhook"
git push
```

### **Roll Back Aliases**
```bash
# 1. List available snapshots
ls aliases/aliases_*.json

# 2. Restore from snapshot
cp aliases/aliases_20251007.json team_aliases.json

# 3. Verify restoration
python -c "
import json
with open('team_aliases.json') as f:
    aliases = json.load(f)
print(f'Restored {len(aliases)} master teams')
"

# 4. Re-run scraper with restored aliases
python scraper_daily.py
```

## 📊 **Monitoring & Metrics**

### **Daily Metrics Dashboard**
Access via Slack daily summary:
- **Sources OK**: X/Y (success rate)
- **Duration**: Xs (performance)
- **New games**: X (data volume)
- **Changed games**: X (data quality)
- **Unresolved teams**: X (data quality)
- **Gold checksum**: XXXX... (integrity)
- **Anomalies**: None/Warnings (health)

### **Health Check Endpoints**
```bash
# API health
curl http://localhost:8000/api/health

# Scraper health (check logs)
tail -n 100 scraper.log | grep ERROR

# Data freshness
ls -la data_ingest/gold/All_Games.parquet
```

### **Anomaly Detection**
- **No new games on weekend**: Normal during off-season
- **High changed games ratio**: Possible retro edits, investigate
- **High unresolved teams**: Alias drift, review queue
- **High error rate**: Source issues, check URLs

## 🛠 **Troubleshooting**

### **Scraper Won't Start**
```bash
# 1. Check Python environment
python --version
pip list | grep -E "(httpx|rapidfuzz|pandas)"

# 2. Check file permissions
ls -la scraper_daily.py
chmod +x scraper_daily.py

# 3. Check configuration
python -c "import scraper_config; print('Config OK')"

# 4. Test with dry run
python scraper_daily.py --dry-run
```

### **Data Quality Issues**
```bash
# 1. Validate Gold layer schema
python -c "
import pandas as pd
df = pd.read_parquet('data_ingest/gold/All_Games.parquet')
print('Schema:', df.columns.tolist())
print('Records:', len(df))
print('Nulls:', df.isnull().sum())
"

# 2. Check for duplicates
python -c "
import pandas as pd
df = pd.read_parquet('data_ingest/gold/All_Games.parquet')
dupes = df.duplicated(subset=['match_id'])
print('Duplicates:', dupes.sum())
"

# 3. Validate team matches
python -c "
import pandas as pd
df = pd.read_parquet('data_ingest/gold/All_Games.parquet')
unmatched = df[df['home_team_match'].isna() | df['away_team_match'].isna()]
print('Unmatched teams:', len(unmatched))
"
```

### **API Issues**
```bash
# 1. Check API server status
ps aux | grep uvicorn

# 2. Restart API server
pkill -f uvicorn
python api_server.py &

# 3. Test API endpoints
curl http://localhost:8000/api/health
curl "http://localhost:8000/api/rankings?state=AZ&limit=5"
```

### **Dashboard Issues**
```bash
# 1. Check Streamlit process
ps aux | grep streamlit

# 2. Restart dashboard
pkill -f streamlit
streamlit run az_u12_dashboard.py &

# 3. Check data file paths
ls -la Rankings*.csv Team_Game_Histories*.csv
```

## 🔄 **Deployment Procedures**

### **Code Deployment**
```bash
# 1. Pull latest changes
git pull origin main

# 2. Install new dependencies
pip install -r requirements.txt

# 3. Run tests
python -m pytest tests/

# 4. Restart services
pkill -f "scraper_daily.py"
pkill -f "api_server.py"
pkill -f "streamlit"

# 5. Start services
python scraper_daily.py &
python api_server.py &
streamlit run az_u12_dashboard.py &
```

### **Configuration Changes**
```bash
# 1. Backup current config
cp scraper_config.py scraper_config.py.backup

# 2. Update configuration
vim scraper_config.py

# 3. Test configuration
python -c "import scraper_config; print('Config valid')"

# 4. Deploy change
git add scraper_config.py
git commit -m "Update scraper configuration"
git push
```

## 📞 **Escalation Procedures**

### **Level 1: Automated Recovery**
- Scraper retries automatically (3 attempts)
- Fallback to legacy data mode
- Slack alerts for monitoring

### **Level 2: Manual Intervention**
- Review alias operations UI
- Manual scrape execution
- Configuration adjustments

### **Level 3: System Administrator**
- Server/network issues
- Database corruption
- Security incidents

## 📚 **Reference Information**

### **File Locations**
- **Config**: `scraper_config.py`
- **Logs**: `scraper.log`
- **Data**: `data_ingest/gold/`
- **Aliases**: `team_aliases.json`
- **Backups**: `backups/`
- **Snapshots**: `aliases/`

### **Key Commands**
```bash
# Daily operations
python scraper_daily.py                    # Run scraper
python generate_team_rankings_v2.py        # Generate rankings
python api_server.py                       # Start API server
streamlit run az_u12_dashboard.py          # Start dashboard
streamlit run alias_ops_ui.py              # Alias management

# Monitoring
tail -f scraper.log                        # Watch logs
curl http://localhost:8000/api/health      # API health
ls -la data_ingest/gold/                  # Check data freshness
```

### **Environment Variables**
```bash
export RANKING_INPUT_MODE=gold             # Use Gold layer
export RANKING_INPUT_MODE=legacy          # Use legacy CSV
export SCRAPER_ENV=production             # Production mode
```

---

**Last Updated**: 2025-10-08  
**Version**: 1.0  
**Maintainer**: Arizona U12 Soccer Rankings Team
