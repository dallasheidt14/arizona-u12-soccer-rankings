# Arizona U12 Soccer Rankings System

A comprehensive soccer ranking system for Arizona U12 Male teams, featuring web scraping, data processing, statistical analysis, and an interactive dashboard.

## 🏆 Features

- **Web Scraping**: Automated data collection from GotSport API
- **Data Processing**: Team matching, deduplication, and data cleaning
- **Statistical Analysis**: Offensive/Defensive ratings, Strength of Schedule (SOS), Power Scores
- **Interactive Dashboard**: Streamlit-based web interface for exploring rankings
- **Real-time Updates**: Fresh data collection and ranking calculations

## 📊 Ranking Methodology

The system uses a sophisticated ranking algorithm that considers:

- **Offensive Rating**: Goals scored per game (weighted for recent performance)
- **Defensive Rating**: Goals allowed per game (weighted for recent performance)
- **Strength of Schedule (SOS)**: Quality of opponents faced
- **Power Score**: Weighted combination of all factors
- **Game Count Penalties**: Adjustments for teams with fewer games

### Formula
```
Power Score = 0.375 × Offensive Rating + 0.375 × (1 - Defensive Rating) + 0.25 × SOS
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/arizona-u12-soccer-rankings.git
   cd arizona-u12-soccer-rankings
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r dashboard_requirements.txt
   ```

3. **Run the dashboard**
   ```bash
   python -m streamlit run az_u12_dashboard.py
   ```

4. **Open your browser** to `http://localhost:8501`

## 📁 Project Structure

```
arizona-u12-soccer-rankings/
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── dashboard_requirements.txt          # Dashboard-specific dependencies
├── .gitignore                          # Git ignore rules
├── az_u12_dashboard.py                 # Streamlit dashboard
├── generate_team_rankings.py           # Main ranking calculation script
├── az_u12_team_matcher.py             # Team matching and categorization
├── az_u12_stats_sos_calculator.py      # Statistics and SOS calculations
├── api_arizona_scraper.py              # GotSport API scraper
├── fix_duplicate_games.py              # Data cleaning utilities
├── fix_duplicate_matched_games.py      # Additional data cleaning
└── data/                               # Data files (excluded from git)
    ├── Rankings_PowerScore.csv         # Final rankings
    ├── Team_Game_Histories.csv         # Game history data
    ├── Matched_Games.csv               # Processed game data
    └── AZ MALE U12 MASTER TEAM LIST.csv # Master team list
```

## 🔧 Usage

### Data Collection
```bash
# Scrape team data from GotSport
python api_arizona_scraper.py

# Clean duplicate games
python fix_duplicate_matched_games.py
```

### Generate Rankings
```bash
# Calculate rankings with current data
python generate_team_rankings.py
```

### Launch Dashboard
```bash
# Start the interactive dashboard
python -m streamlit run az_u12_dashboard.py
```

## 📈 Dashboard Features

- **Team Rankings**: Interactive table with filtering options
- **Team Details**: Comprehensive game history and statistics
- **Club Analysis**: Performance comparison by club
- **Visualizations**: Charts and graphs for data exploration
- **Data Export**: Download rankings and game data

## 🛠️ Configuration

Key parameters can be adjusted in `generate_team_rankings.py`:

```python
OFFENSE_WEIGHT = 0.375      # Weight for offensive performance
DEFENSE_WEIGHT = 0.375       # Weight for defensive performance  
SOS_WEIGHT = 0.25           # Weight for strength of schedule
RECENT_WEIGHT = 0.7         # Weight for recent games (last 10)
```

## 📊 Data Sources

- **GotSport API**: Primary data source for team and game information
- **Team Matching**: Fuzzy matching algorithm for team name variations
- **Data Validation**: Comprehensive error checking and data cleaning

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- GotSport for providing the API access
- Arizona Youth Soccer Association
- All participating teams and clubs

## 📞 Support

For questions or issues, please:
- Open an issue on GitHub
- Contact the project maintainer
- Check the documentation in the `docs/` folder

## 🔄 Version History

- **v1.0.0** - Initial release with basic ranking system
- **v1.1.0** - Added interactive dashboard
- **v1.2.0** - Improved data cleaning and deduplication
- **v1.3.0** - Enhanced team matching and SOS calculations

---

**Made with ⚽ for Arizona Youth Soccer**