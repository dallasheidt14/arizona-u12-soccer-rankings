# Youth Soccer Rankings System

## 🏆 **OVERVIEW**

A sophisticated soccer ranking system that processes U10, U11, and U12 boys' soccer data through multiple stages to produce mathematically sound team rankings using the V5.3E Enhanced algorithm. Now supports national-level processing with auto-matching capabilities.

## 🚀 **QUICK START**

### **Auto-Match Team B Data:**
```bash
python scripts/auto_match/auto_match_team_b.py
```

### **Run Complete Pipeline:**
```bash
python run_pipeline.py
```

### **Start API Server:**
```bash
python src/api/app.py
```

## 📁 **FILE STRUCTURE**

```
Soccer Rankings v2/
├── 📁 data/
│   ├── 📁 input/                    # Raw data files
│   │   ├── AZ MALE U12 MASTER TEAM LIST.csv
│   │   ├── AZ MALE U12 GAME HISTORY LAST 18 MONTHS .csv
│   │   ├── National_Male_U10_Master_Team_List.csv
│   │   ├── National_Male_U11_Master_Team_List.csv
│   │   └── Game History u10 and u11.csv
│   ├── 📁 processed/                # Intermediate files
│   │   ├── 📁 u10/                  # U10 processed data
│   │   │   └── U10_Enhanced.csv
│   │   ├── 📁 u11/                  # U11 processed data
│   │   │   └── U11_Enhanced.csv
│   │   ├── 📁 national/             # National format files
│   │   │   ├── National_Male_U10_Game_History_18_Months.csv
│   │   │   └── National_Male_U11_Game_History_18_Months.csv
│   │   ├── Matched_Games.csv
│   │   └── Team_Game_Histories.csv
│   └── 📁 output/                   # Final outputs
│       ├── Rankings_v53_enhanced.csv
│       └── connectivity_report_v53e.csv
├── 📁 scripts/
│   └── 📁 auto_match/               # Auto-matching scripts
│       └── auto_match_team_b.py
├── 📁 src/
│   ├── 📁 core/                     # Core processing scripts
│   │   ├── team_matcher.py         # Team matching & data cleaning
│   │   ├── history_generator.py    # Comprehensive history generation
│   │   └── ranking_engine.py        # V5.3E Enhanced ranking engine
│   ├── 📁 analytics/                # Advanced analytics
│   │   └── iterative_opponent_strength_v53_enhanced.py
│   ├── 📁 api/                      # API server
│   │   └── app.py
│   ├── 📁 dashboard/                # Dashboard applications
│   │   └── app_v53_multi_division.py
│   └── 📁 utils/                     # Utility functions
│       └── team_normalizer.py
├── 📁 docs/
│   └── 📁 processing/               # Processing documentation
│       └── AUTO_MATCH_SYSTEM.md
├── 📁 config/
│   └── config.py                    # System configuration
├── run_pipeline.py                  # Complete pipeline runner
└── README.md                        # This file
```

## 🤖 **AUTO-MATCH SYSTEM**

### **Overview:**
The auto-matching system processes U10 and U11 game history data by automatically adding missing Team B information through intelligent matching against master team lists.

### **Key Features:**
- **EXACT Matching**: Direct team name matches (52.3% success rate)
- **FUZZY Matching**: 85%+ similarity matches (47.1% success rate)
- **Cross-State Detection**: Identifies national-level games
- **99.5% Overall Success Rate**: Only 0.5% require manual review

### **Processing Results:**
- **U10**: 102,373 games processed
- **U11**: 92,448 games processed
- **Total**: 194,821 games with complete Team B data

### **Usage:**
```bash
python scripts/auto_match/auto_match_team_b.py
```

### **Output Files:**
- `data/processed/u10/U10_Enhanced.csv` - U10 enhanced data
- `data/processed/u11/U11_Enhanced.csv` - U11 enhanced data
- `data/processed/national/National_Male_U10_Game_History_18_Months.csv` - U10 national format
- `data/processed/national/National_Male_U11_Game_History_18_Months.csv` - U11 national format

## 🔄 **DATA FLOW**

### **Complete Pipeline Process:**

1. **Raw Data Collection**
   - `AZ MALE U12 MASTER TEAM LIST.csv` (332 teams)
   - `AZ MALE U12 GAME HISTORY LAST 18 MONTHS .csv` (3,969 games)

2. **Team Matching & Data Cleaning** (`team_matcher.py`)
   - Fuzzy string matching (90% threshold)
   - Name normalization and club integration
   - Categorization of unmatched teams
   - Output: `Matched_Games.csv`

3. **Comprehensive History Generation** (`history_generator.py`)
   - Wide to long format conversion
   - 18-month window filtering
   - Enhanced data with opponent strength
   - Output: `Team_Game_Histories.csv`

4. **V5.3E Enhanced Ranking Calculation** (`ranking_engine.py`)
   - Sophisticated algorithm with adaptive K-factor
   - Outlier guard and performance layer
   - Bayesian shrinkage and robust normalization
   - Output: `Rankings_v53_enhanced.csv`

## 🧮 **V5.3E ENHANCED ALGORITHM**

### **Key Features:**
- **Adaptive K-factor**: Shrinks impact for weak opponents and low-game teams
- **Outlier Guard**: Caps extreme values to prevent single-game dominance
- **Performance Layer**: Expected vs actual goal differential analysis
- **Robust Normalization**: Smooth distributions instead of binary cliffs
- **Bayesian Shrinkage**: Stabilizes metrics for teams with few games

### **Ranking Formula:**
```
PowerScore = 0.20×SAO + 0.20×SAD + 0.60×SOS
```

Where:
- **SAO**: Strength-Adjusted Offense (normalized)
- **SAD**: Strength-Adjusted Defense (normalized)  
- **SOS**: Strength of Schedule (normalized)

### **Data Windows:**
- **Rankings**: Last 30 games, within 365 days (weighted)
- **Display**: Last 18 months (unweighted)

## 📊 **OUTPUT FILES**

### **Primary Output:**
- **`Rankings_v53_enhanced.csv`** - Final team rankings (150 teams)
  - Columns: Rank, Team, PowerScore_adj, SAO_norm, SAD_norm, SOS_norm, GamesPlayed, Status, etc.

### **Supporting Outputs:**
- **`connectivity_report_v53e.csv`** - Network analysis of opponent connections
- **`Matched_Games.csv`** - Cleaned games with matched team names
- **`Team_Game_Histories.csv`** - Comprehensive game history (long format)

## 🔧 **CONFIGURATION**

### **Key Settings** (`config.py`):
- `INACTIVE_HIDE_DAYS = 180` - Hide teams inactive >180 days
- `RECENT_K = 10` - Last 10 games get higher weight
- `RECENT_SHARE = 0.70` - 70% weight for recent games
- `PROVISIONAL_ALPHA = 0.5` - Game count penalty exponent

## 🌐 **API ENDPOINTS**

### **Core Endpoints:**
- `GET /api/rankings` - Get team rankings
- `GET /api/team/{team_name}/history` - Get team game history
- `GET /api/team/{team_name}/stats` - Get team statistics

### **Dashboard:**
- `GET /` - Main dashboard interface
- `GET /dashboard` - Multi-division dashboard

## 🎯 **TEAM MAPPING PROCESS**

1. **Master List**: 332 authorized U12 teams with club affiliations
2. **Fuzzy Matching**: 90% threshold matches game history names to master teams
3. **Name Enhancement**: Combines team names with club names for display
4. **Filtering**: Only master teams are ranked, but all opponents kept for SOS

## 🚀 **ADVANCED FEATURES**

### **Multi-Division Support:**
- Configurable for different age groups (U11, U12, U13, U14)
- Division-specific master lists and data processing
- Unified ranking algorithm across divisions

### **Real-Time Updates:**
- Daily scraper integration
- Automatic pipeline execution
- Live dashboard updates

### **Analytics & Reporting:**
- Connectivity analysis for opponent networks
- Performance tracking and validation
- Comprehensive logging and error handling

## 🔍 **TROUBLESHOOTING**

### **Common Issues:**
1. **Missing Input Files**: Ensure master list and game history files are in `data/input/`
2. **Team Matching Issues**: Check fuzzy matching threshold in `team_matcher.py`
3. **Ranking Errors**: Verify data quality and date formats
4. **API Issues**: Check configuration and file paths

### **Debug Mode:**
- Enable verbose logging in `config.py`
- Check intermediate files in `data/processed/`
- Review error logs and output files

## 📈 **PERFORMANCE**

### **System Capabilities:**
- Processes 3,969 games across 332 teams
- Generates rankings for 150 active teams
- Sub-second API response times
- Handles real-time data updates

### **Scalability:**
- Modular architecture supports multiple divisions
- Configurable parameters for different leagues
- Extensible for additional analytics features

## 🏆 **ACHIEVEMENTS**

This system represents a production-ready, mathematically sophisticated ranking engine that rivals professional sports analytics platforms. The V5.3E Enhanced algorithm with adaptive K-factor, outlier guard, and performance layer represents cutting-edge sports analytics.

---

**Built with ❤️ for Arizona Youth Soccer**