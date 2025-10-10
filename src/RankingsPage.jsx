import React, { useEffect, useState } from "react";
import { ChevronUp, ChevronDown, Info } from "lucide-react";
import "./RankingsPage.css";

// Tooltip Component
const Tooltip = ({ children, content }) => {
  const [isVisible, setIsVisible] = useState(false);
  
  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        className="cursor-help"
      >
        {children}
      </div>
      {isVisible && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg shadow-lg z-50 max-w-xs">
          <div className="text-center">{content}</div>
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
        </div>
      )}
    </div>
  );
};

export default function RankingsPage({ 
  activeTeams = [], 
  provisionalTeams = [], 
  onBack, 
  onTeamClick,
  title = "Youth Soccer Rankings",
  subtitle = "Interactive rankings with sortable columns & live filters."
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState("PowerScore_adj");
  const [sortOrder, setSortOrder] = useState("desc");

  // Filter teams based on search
  const filteredActive = activeTeams.filter((team) =>
    team.Team.toLowerCase().includes(searchTerm.toLowerCase())
  );
  const filteredProvisional = provisionalTeams.filter((team) =>
    team.Team.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort logic
  const sortTeams = (teams) =>
    [...teams].sort((a, b) => {
      const valA = parseFloat(a[sortField]) || 0;
      const valB = parseFloat(b[sortField]) || 0;
      return sortOrder === "asc" ? valA - valB : valB - valA;
    });

  const handleSort = (field) => {
    if (field === sortField) {
      // Toggle asc/desc
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 10) {
        document.body.classList.add("scrolled");
      } else {
        document.body.classList.remove("scrolled");
      }
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="rankings-wrapper">
      {/* Sticky Header */}
      <header className="page-header">
        <button className="back-btn" onClick={onBack}>
          ← Back to Selector
        </button>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </header>

      <main className="rankings-main fade-in-up">
        {/* Summary Banner */}
        <div className="summary-banner">
          <p>
            📊 Showing <strong>{filteredActive.length}</strong> active teams and{" "}
            <strong>{filteredProvisional.length}</strong> provisional teams.  
            <Tooltip content="Only teams with ≥1 game in the past 365 days are currently ranked. Teams inactive for 180+ days are filtered out.">
              <Info className="inline w-4 h-4 ml-2 text-gray-500 hover:text-gray-700" />
            </Tooltip>
            <br />
            <span className="text-sm text-gray-600">
              Updated automatically from match data (last 12 months).
            </span>
          </p>
        </div>

        <div className="filter-bar">
          <input
            type="text"
            placeholder="🔍 Search teams..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-box"
          />
          <div className="stats-summary">
            <span className="stat-chip">
              <strong>{filteredActive.length}</strong> Active Teams
            </span>
            <span className="stat-chip">
              <strong>{filteredProvisional.length}</strong> Provisional Teams
            </span>
          </div>
        </div>

        {/* Active Teams Section */}
        <RankSection
          title="🟢 Active Teams"
          subtitle="8+ Games Played"
          teams={sortTeams(filteredActive)}
          sortField={sortField}
          sortOrder={sortOrder}
          onSort={handleSort}
          onTeamClick={onTeamClick}
          type="active"
        />

        {/* Provisional Teams Section */}
        {filteredProvisional.length > 0 && (
          <RankSection
            title="⚪ Provisional Teams"
            subtitle="Fewer than 8 Games"
            teams={sortTeams(filteredProvisional)}
            sortField={sortField}
            sortOrder={sortOrder}
            onSort={handleSort}
            onTeamClick={onTeamClick}
            type="provisional"
          />
        )}
      </main>
    </div>
  );
}

function RankSection({ title, subtitle, teams, sortField, sortOrder, onSort, onTeamClick, type }) {
  if (teams.length === 0) {
    return (
      <section className="rank-section">
        <h2 className={`section-title ${type === "active" ? "active" : "provisional"}`}>
          {title} <span>({subtitle})</span>
        </h2>
        <div className="empty-state">
          <p>No teams found matching your criteria.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="rank-section">
      <h2 className={`section-title ${type === "active" ? "active" : "provisional"}`}>
        {title} <span>({subtitle})</span>
      </h2>
      <div className="table-container fade-in-up">
        <table className="rankings-table">
          <thead>
            <tr>
              <SortableHeader field="Rank" label="Rank" onSort={onSort} sortField={sortField} sortOrder={sortOrder} />
              <SortableHeader field="Team" label="Team" onSort={onSort} sortField={sortField} sortOrder={sortOrder} />
              <SortableHeader field="PowerScore_adj" label="Power" onSort={onSort} sortField={sortField} sortOrder={sortOrder} />
              <SortableHeader field="SAO_norm" label="Off" onSort={onSort} sortField={sortField} sortOrder={sortOrder} />
              <SortableHeader field="SAD_norm" label="Def" onSort={onSort} sortField={sortField} sortOrder={sortOrder} />
              <SortableHeader field="SOS_norm" label="SOS" onSort={onSort} sortField={sortField} sortOrder={sortOrder} />
              <SortableHeader field="GamesPlayed" label="GP" onSort={onSort} sortField={sortField} sortOrder={sortOrder} />
              <th>W-L-T</th>
            </tr>
          </thead>
          <tbody className="fade-in-up">
            {teams.map((team, i) => (
              <tr key={team.Team} className="table-row">
                <td className="rank-cell">
                  {type === "active" ? team.Rank || i + 1 : ""}
                </td>
                <td className="team-cell">
                  <button 
                    className="team-link"
                    onClick={() => onTeamClick(team.Team)}
                  >
                    {team.Team}
                  </button>
                </td>
                <td className="power-cell">
                  <PowerScoreCell value={team.PowerScore_adj} />
                </td>
                <td className="off-cell">
                  {team.SAO_norm ? team.SAO_norm.toFixed(3) : 'N/A'}
                </td>
                <td className="def-cell">
                  {team.SAD_norm ? team.SAD_norm.toFixed(3) : 'N/A'}
                </td>
                <td className="sos-cell">
                  {team.SOS_norm ? team.SOS_norm.toFixed(3) : 'N/A'}
                </td>
                <td className="gp-cell">
                  {team.GamesPlayed || 'N/A'}
                </td>
                <td className="record-cell">
                  {team.WL || 'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SortableHeader({ field, label, onSort, sortField, sortOrder }) {
  const isActive = sortField === field;
  return (
    <th
      onClick={() => onSort(field)}
      className={`sortable ${isActive ? "active" : ""}`}
    >
      {label}
      {isActive && (
        sortOrder === "asc" ? (
          <ChevronUp size={14} className="sort-icon" />
        ) : (
          <ChevronDown size={14} className="sort-icon" />
        )
      )}
    </th>
  );
}

function PowerScoreCell({ value }) {
  if (!value) return <span className="power-score-na">N/A</span>;
  
  // Enhanced color gradient based on power score
  const getPowerColor = (score) => {
    if (score > 0.65) return "#16a34a"; // 🟩 Green (elite)
    if (score > 0.45) return "#f59e0b"; // 🟨 Yellow (competitive) 
    return "#dc2626"; // 🟥 Red (developing)
  };
  
  const getPowerLabel = (score) => {
    if (score > 0.65) return "elite";
    if (score > 0.45) return "competitive";
    return "developing";
  };
  
  const color = getPowerColor(value);
  const label = getPowerLabel(value);
  
  return (
    <span 
      className="power-score"
      style={{ 
        color,
        fontWeight: 600,
        background: `${color}15`, // 15% opacity background
        padding: '0.25rem 0.5rem',
        borderRadius: '6px',
        border: `1px solid ${color}30` // 30% opacity border
      }}
      title={`${label.charAt(0).toUpperCase() + label.slice(1)} performance`}
    >
      {value.toFixed(3)}
    </span>
  );
}
