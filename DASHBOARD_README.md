# AZ U12 Rankings Dashboard

## 🚀 Quick Start

The interactive dashboard is now running! Open your web browser and go to:

**http://localhost:8501**

## 📊 Dashboard Features

### 🏠 Overview Page
- **Summary Metrics**: Total teams, average games, total games, #1 team
- **Power Score Distribution**: Histogram showing how teams are distributed
- **Games vs Power Score Scatter**: See the relationship between sample size and performance
- **Top 20 Teams Bar Chart**: Visual ranking of the best teams

### 🏆 Team Rankings Page
- **Interactive Table**: Sortable rankings with all key metrics
- **Club Filter**: Filter teams by their club
- **Games Filter**: Set minimum games played threshold
- **Top N Filter**: Show top 10, 25, 50, 100, or all teams

### 🔍 Team Details Page
- **Team Selector**: Choose any team to view detailed stats
- **Team Metrics**: Rank, Power Score, Games Played, Win %
- **Statistics Table**: Goals For/Game, Goals Against/Game, SOS, etc.
- **Record Breakdown**: Wins, Losses, Ties with percentages
- **Recent Games**: Last 10 games with opponents and results

### 🏢 Club Analysis Page
- **Club Statistics**: Teams per club, average power scores, total records
- **Club Comparison Chart**: Top 10 clubs by average power score

### 📥 Data Export Page
- **Download Rankings**: Get the complete rankings CSV
- **Download Game Histories**: Get all team game histories CSV

## 🎛️ How to Use

1. **Navigate**: Use the sidebar to switch between different views
2. **Filter**: Use the filters on each page to narrow down results
3. **Explore**: Click on charts to interact with them
4. **Export**: Download data for further analysis
5. **Compare**: Use the team details page to compare specific teams

## 🔧 Technical Details

### Ranking Methodology
- **Offense Weight**: 37.5% (Goals For per Game)
- **Defense Weight**: 37.5% (1 - Goals Against per Game)
- **SOS Weight**: 25% (Strength of Schedule)
- **Recent Game Weight**: 70% weight on last 10 games
- **Game Count Penalties**: 
  - ≥20 games: No penalty
  - 10-19 games: 0.9x multiplier
  - <10 games: 0.75x multiplier

### Data Sources
- **Rankings_PowerScore.csv**: Complete team rankings
- **Team_Game_Histories.csv**: Individual game records per team

## 🛠️ Troubleshooting

If the dashboard doesn't load:
1. Make sure the CSV files are in the same directory as the dashboard script
2. Check that Streamlit is installed: `pip install streamlit`
3. Try refreshing your browser
4. Check the terminal for any error messages

## 📱 Mobile Friendly

The dashboard is responsive and works on mobile devices for basic viewing and filtering.

---

**Enjoy exploring your AZ U12 rankings!** ⚽
