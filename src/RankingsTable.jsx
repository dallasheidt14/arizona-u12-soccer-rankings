import React, { useState } from "react";
import "./RankingsTable.css";

export default function RankingsTable({ teams, type, onTeamClick }) {
  // --- Sorting state
  const [sortConfig, setSortConfig] = useState({
    key: "PowerScore_adj",
    direction: "desc",
  });

  // --- Sorting logic
  const sortedTeams = React.useMemo(() => {
    if (!sortConfig.key) return teams;
    return [...teams].sort((a, b) => {
      const valA = a[sortConfig.key] ?? "";
      const valB = b[sortConfig.key] ?? "";
      const isNumeric = !isNaN(parseFloat(valA)) && !isNaN(parseFloat(valB));
      const order = sortConfig.direction === "asc" ? 1 : -1;
      
      if (isNumeric) {
        return (parseFloat(valA) - parseFloat(valB)) * order;
      }
      return valA.toString().localeCompare(valB.toString()) * order;
    });
  }, [teams, sortConfig]);

  const handleSort = (key) => {
    setSortConfig((prev) => {
      if (prev.key === key) {
        return { key, direction: prev.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: "desc" };
    });
  };

  const sortIndicator = (key) => {
    if (sortConfig.key !== key) return "";
    return sortConfig.direction === "asc" ? " ▲" : " ▼";
  };

  const formatValue = (value, decimals = 3) => {
    if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
    if (typeof value === 'number') return value.toFixed(decimals);
    return value;
  };

  return (
    <section className={`rankings-section ${type}`}>
      <h2 className={`section-title ${type}`}>
        {type === "active" && "🟢 Active Teams (8+ Games)"}
        {type === "provisional" && "⚪ Provisional Teams (<8 Games)"}
        {type === "inactive" && "⚫ Inactive Teams (No games in 6 months)"}
      </h2>

      {/* Desktop Table */}
      <table className="rankings-table">
        <thead>
          <tr>
            <th onClick={() => handleSort("Rank")}>
              Rank {sortIndicator("Rank")}
            </th>
            <th onClick={() => handleSort("Team")}>
              Team {sortIndicator("Team")}
            </th>
            <th onClick={() => handleSort("PowerScore_adj")}>
              Power {sortIndicator("PowerScore_adj")}
            </th>
            <th onClick={() => handleSort("SAO_norm")}>
              Off {sortIndicator("SAO_norm")}
            </th>
            <th onClick={() => handleSort("SAD_norm")}>
              Def {sortIndicator("SAD_norm")}
            </th>
            <th onClick={() => handleSort("SOS_display")}>
              SOS {sortIndicator("SOS_display")}
            </th>
            <th onClick={() => handleSort("GamesPlayed")}>
              GP {sortIndicator("GamesPlayed")}
            </th>
            <th>W-L-T</th>
          </tr>
        </thead>
        <tbody>
          {sortedTeams.map((team, i) => (
            <tr key={team.Team}>
              <td>{type === "active" ? team.Rank || (i + 1) : ""}</td>
              <td className="team-name">
                <button
                  onClick={() => onTeamClick(team.Team)}
                  className="team-link"
                >
                  {team.Team}
                </button>
              </td>
              <td>{formatValue(team.PowerScore_adj)}</td>
              <td>{formatValue(team.SAO_norm)}</td>
              <td>{formatValue(team.SAD_norm)}</td>
              <td>{formatValue(team.SOS_display)}</td>
              <td>{team.GamesPlayed || 'N/A'}</td>
              <td>{team.WL || 'N/A'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile Card View */}
      <div className="card-container">
        {teams.map((team, i) => (
          <div key={team.Team} className="team-card">
            {type === "active" && (
              <div className="rank">#{team.Rank || (i + 1)}</div>
            )}
            <h3>
              <button
                onClick={() => onTeamClick(team.Team)}
                className="team-link-mobile"
              >
                {team.Team}
              </button>
            </h3>
            <p>
              <span>Power Score:</span> {formatValue(team.PowerScore_adj)}
            </p>
            <p>
              <span>Off / Def / SOS:</span> {formatValue(team.SAO_norm)} / {formatValue(team.SAD_norm)} / {formatValue(team.SOS_display)}
            </p>
            <p>
              <span>Games:</span> {team.GamesPlayed || 'N/A'}  
              <span> Record:</span> {team.WL || 'N/A'}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}




