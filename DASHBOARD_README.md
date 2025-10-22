# ⚽ Soccer Rankings Dashboard

## 🚀 **Quick Start**

### **Option 1: Double-click to start**
```
start_dashboard.bat
```

### **Option 2: Command line**
```bash
streamlit run dashboard.py
```

The dashboard will automatically open in your browser at `http://localhost:8501`

---

## 🎯 **Features**

### **Filter Options**
- **Age Group**: U10, U11, U12, U13, U14, U15, U16, U17, U18
- **Gender**: Male, Female
- **Scope**: USA (National) or any state (AZ, CA, TX, etc.)

### **Interactive Features**
- **Clickable Teams**: Click any team name to view detailed stats and game history
- **Search Teams**: Find specific teams by name
- **Display Options**: Top 25, Top 50, Top 100, or All Teams
- **Key Metrics**: Total teams, average power score, cross-age/cross-state games
- **Download CSV**: Export filtered rankings

### **Team Detail Pages** 🆕
- **Game History**: Complete win/loss record with scores
- **Performance Charts**: Win percentage trend over time
- **Team Analysis**: Strengths and areas for improvement
- **Download Game History**: Export individual team data

### **Data Display**
- **Rankings Table**: Sortable columns with formatted data
- **Power Score**: Overall team strength (0-1 scale)
- **Win Percentage**: Team's win rate
- **SOS Score**: Strength of schedule
- **Cross-Age Games**: Games against different age groups
- **Cross-State Games**: Games against teams from other states

---

## 📊 **Available Data**

### **U10 Rankings** ✅
- **National**: 3,225 teams
- **Arizona**: 104 teams
- **All 48 states** available

### **U11 Rankings** 🔄
- Ready to generate with `python scripts/generate_rankings.py --age_group 11 --gender M`

### **U12 Rankings** 🔄
- Ready to generate with `python scripts/generate_rankings.py --age_group 12 --gender M`

---

## 🔧 **Technical Details**

### **Algorithm**: V5.3E Enhanced
- **Power Score**: Win% (40%) + Goal Diff (30%) + SOS (30%)
- **Cross-Age Support**: U10 vs U11 games included
- **Default Strength**: Unknown opponents get 0.35 strength
- **Recent Weight**: 70% weight for last 10 games

### **Data Sources**
- **Master Team Lists**: `data/input/National_Male_U10_Master_Team_List.csv`
- **Game History**: `data/Game History u10 and u11.csv`
- **Output Rankings**: `data/output/National_U10_Rankings_CROSS_AGE.csv`

---

## 🎯 **Usage Examples**

### **View National U10 Rankings**
1. Select Age Group: "10"
2. Select Gender: "Male" 
3. Select Scope: "USA (National)"
4. Click "Top 25 Teams"

### **View Team Details** 🆕
1. Click on any team name (🔍 button)
2. View complete game history with scores
3. See performance charts and analysis
4. Download team's game history

### **Search for Specific Team**
1. Select your criteria
2. Type team name in search box
3. Click on team name to view details

### **Compare State Rankings**
1. Select Age Group: "10"
2. Select Scope: "AZ" (Arizona)
3. Compare with national rankings

---

## 🚀 **Next Steps**

1. **Generate U11 Rankings**: Run U11 ranking script
2. **Generate U12 Rankings**: Run U12 ranking script  
3. **Add More States**: Generate rankings for additional states
4. **Customize Dashboard**: Modify colors, layout, or features

---

## 📝 **Notes**

- **Default Strength**: Unknown opponents get 0.35 strength (fair SOS)
- **Cross-Age Games**: U10 teams playing U11 opponents get proper credit
- **Cross-State Games**: Teams playing out-of-state opponents tracked
- **Real-time Updates**: Dashboard updates when new ranking files are generated

**Enjoy exploring the rankings! 🏆**
