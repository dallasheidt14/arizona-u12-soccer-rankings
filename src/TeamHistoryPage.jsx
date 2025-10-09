import React, { useEffect, useState } from "react";
import "./TeamHistoryPage.css";

export default function TeamHistoryPage({ 
  teamName, 
  games = [], 
  onBack 
}) {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 10) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Calculate team statistics
  const stats = calculateTeamStats(games);

  const getPerfClass = (bucket) => {
    switch (bucket) {
      case "good": return "performance-up";
      case "weak": return "performance-down";
      default: return "performance-neutral";
    }
  };

  const getPerfIcon = (bucket) => {
    switch (bucket) {
      case "good": return "↑";
      case "weak": return "↓";
      default: return "•";
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className="team-history-wrapper">
      {/* Sticky Hero Header */}
      <header className={`team-header ${isScrolled ? 'scrolled' : ''}`}>
        <button className="back-btn" onClick={onBack}>
          ← Back to Rankings
        </button>
        <div className="team-info">
          <h1>{teamName}</h1>
          <p>Game History • {games.length} Matches • Last 18 Months</p>
        </div>
      </header>

      <main className="team-main fade-in-up">
        {/* Summary Panel */}
        <div className="summary-panel">
          <div className="stat-item">
            <strong>Avg GD:</strong> {stats.avgGD > 0 ? '+' : ''}{stats.avgGD.toFixed(1)}
          </div>
          <div className="stat-item">
            <strong>Record:</strong> {stats.wins}W - {stats.losses}L - {stats.ties}T
          </div>
          <div className="stat-item">
            <strong>Win Rate:</strong> {stats.winRate.toFixed(0)}%
          </div>
          <div className="stat-item">
            <strong>Expected Accuracy:</strong> {stats.expectedAccuracy.toFixed(0)}%
          </div>
        </div>

        {/* Game History Table */}
        <div className="game-card">
          <table className="game-history-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Opponent</th>
                <th>Score</th>
                <th>Expected GD</th>
                <th>Performance</th>
                <th>Opponent Strength</th>
              </tr>
            </thead>
            <tbody className="fade-in-up">
              {games.map((game, i) => (
                <tr key={i} className="game-row" style={{ animationDelay: `${i * 50}ms` }}>
                  <td className="date-cell">
                    {formatDate(game.Date)}
                  </td>
                  <td className="opponent-cell">
                    {game.Opponent}
                  </td>
                  <td className="score-cell">
                    <span className="score-badge">
                      {game.GoalsFor} - {game.GoalsAgainst}
                    </span>
                  </td>
                  <td className="expected-cell">
                    {game.expected_gd ? game.expected_gd.toFixed(2) : 'N/A'}
                  </td>
                  <td className={`performance-cell ${getPerfClass(game.impact_bucket)}`}>
                    <span className="performance-indicator">
                      {getPerfIcon(game.impact_bucket)} {game.gd_delta ? game.gd_delta.toFixed(2) : 'N/A'}
                    </span>
                  </td>
                  <td className="strength-cell">
                    <div className="strength-bar">
                      <div 
                        className="strength-fill"
                        style={{ 
                          width: `${Math.min(100, (game.Opponent_BaseStrength || 0.5) * 100)}%` 
                        }}
                      ></div>
                      <span className="strength-text">
                        {Math.round((game.Opponent_BaseStrength || 0.5) * 100)}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

// Helper function to calculate team statistics
function calculateTeamStats(games) {
  if (!games.length) {
    return {
      avgGD: 0,
      wins: 0,
      losses: 0,
      ties: 0,
      winRate: 0,
      expectedAccuracy: 0
    };
  }

  let totalGD = 0;
  let wins = 0;
  let losses = 0;
  let ties = 0;
  let expectedCorrect = 0;

  games.forEach(game => {
    const gd = game.GoalsFor - game.GoalsAgainst;
    totalGD += gd;

    if (gd > 0) wins++;
    else if (gd < 0) losses++;
    else ties++;

    // Check if performance matches expectation
    if (game.impact_bucket === 'neutral') {
      expectedCorrect++;
    }
  });

  return {
    avgGD: totalGD / games.length,
    wins,
    losses,
    ties,
    winRate: (wins / games.length) * 100,
    expectedAccuracy: (expectedCorrect / games.length) * 100
  };
}
