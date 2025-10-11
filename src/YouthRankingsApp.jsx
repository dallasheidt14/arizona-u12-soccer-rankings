import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Search, ChevronRight, Users, Table as TableIcon, ArrowLeft, Info } from "lucide-react";
import RankingsTable from "./RankingsTable";
import SelectorPage from "./SelectorPage";
import StickyHeader from "./StickyHeader";
import RankingsPage from "./RankingsPage";
import TeamHistoryPage from "./TeamHistoryPage";
import SelectorHero from "./SelectorHero";

/**
 * Single-file React UI for your desired flow:
 * 1) Landing selector: Gender (Boys/Girls) → Age Group (2018-2009) → State
 * 2) Clicking "View Rankings" loads Team Rankings for that slice.
 * 3) Clicking a Team name loads that Team's Game History (drilldown).
 *
 * Data fetching contract (plug your backend):
 *   GET /api/slices -> { slices: [{state, gender, year, rankings, histories, teams, games}, ...] }
 *   GET /api/rankings?state=AZ&gender=MALE&year=2014 -> [{ Team, Rank, PowerScore, Off_norm, Def_norm, SOS_norm, ... }]
 *   GET /api/team/{encodeURIComponent(team)}?state=AZ&gender=MALE&year=2014 -> team game history rows
 *
 * If these endpoints are not yet available in your environment, this component
 * will fall back to small mocked data so the UI is navigable immediately.
 */

// --- Tooltip Component ---
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

// --- Helpers: mock data fallbacks ---
const mockSlices = {
  slices: [
    { state: "AZ", gender: "MALE", year: 2014, rankings: "Rankings_AZ_MALE_2014.csv", histories: "Team_Game_Histories_AZ_MALE_2014.csv", teams: 153, games: 4718 },
    { state: "AZ", gender: "FEMALE", year: 2014, rankings: "Rankings_AZ_FEMALE_2014.csv", histories: "Team_Game_Histories_AZ_FEMALE_2014.csv", teams: 130, games: 3901 },
  ],
};

const mockRankings = [
  { Rank: 1, Team: "2014 Elite", PowerScore: 0.877, Off_norm: 0.92, Def_norm: 0.88, SOS_norm: 0.74, GamesPlayed: 10, WL: "8-1-1" },
  { Rank: 2, Team: "AZ Arsenal 2014B", PowerScore: 0.861, Off_norm: 0.89, Def_norm: 0.86, SOS_norm: 0.73, GamesPlayed: 43, WL: "26-12-5" },
];

const mockHistory = (team) => [
  { Date: "2025-09-28", Opponent: "Rival FC 2014B", GoalsFor: 2, GoalsAgainst: 1, expected_gd: 0.4, gd_delta: 0.6, impact_bucket: "good", Opponent_BaseStrength: 0.78 },
  { Date: "2025-09-14", Opponent: "Phoenix United 2014B", GoalsFor: 1, GoalsAgainst: 1, expected_gd: 0.1, gd_delta: -0.1, impact_bucket: "neutral", Opponent_BaseStrength: 0.66 },
  { Date: "2025-09-07", Opponent: "Desert SC 2014B", GoalsFor: 0, GoalsAgainst: 2, expected_gd: 0.2, gd_delta: -2.2, impact_bucket: "weak", Opponent_BaseStrength: 0.71 },
];

async function fetchJSON(url) {
  try {
    console.log('fetchJSON: Fetching', url);
    const r = await fetch(url);
    console.log('fetchJSON: Response status', r.status, r.ok);
    if (!r.ok) {
      console.log('fetchJSON: Bad status, response text:', await r.text());
      throw new Error("bad status");
    }
    const data = await r.json();
    console.log('fetchJSON: Success, data length:', data?.length);
    return data;
  } catch (e) {
    console.log('fetchJSON: Error:', e);
    return null;
  }
}

// --- Main App Component ---
export default function YouthRankingsApp() {
  const [view, setView] = useState("select"); // "select" | "rankings" | "team"
  const [gender, setGender] = useState("MALE");
  const [ageGroup, setAgeGroup] = useState("U12");
  const [state, setState] = useState("AZ");

  const [slices, setSlices] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [activeTeams, setActiveTeams] = useState([]);
  const [provisionalTeams, setProvisionalTeams] = useState([]);
  const [rankingsMeta, setRankingsMeta] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTeam, setActiveTeam] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("PowerScore");
  const [sortOrder, setSortOrder] = useState("desc");

  // Load slice index on mount (for states/availability)
  useEffect(() => {
    (async () => {
      const data = await fetchJSON("/api/slices");
      if (data && Array.isArray(data.slices)) setSlices(data.slices);
      else setSlices(mockSlices.slices);
    })();
  }, []);

  const statesFromIndex = useMemo(() => {
    const vals = Array.from(new Set(slices.map((s) => s.state).filter(Boolean))).sort();
    return vals.length ? vals : ["AZ"];
  }, [slices]);

  const years = useMemo(() => Array.from({ length: 2018 - 2009 + 1 }, (_, i) => String(2018 - i)), []);

  async function goRankings(customGender = null, customAgeGroup = null, customState = null) {
    setLoading(true); setError("");
    
    // Use passed values or current state
    const useGender = customGender || gender;
    const useAgeGroup = customAgeGroup || ageGroup;
    const useState = customState || state;
    
    // Route to appropriate API based on age group
    let url;
    if (useAgeGroup === "U11") {
      // Use new ID-based API for U11
      url = `/api/v1/az/m/u11/rankings`;
    } else {
      // Use legacy API for U12 and others
      url = `/api/rankings?state=${encodeURIComponent(useState)}&gender=${encodeURIComponent(useGender)}&age_group=${encodeURIComponent(useAgeGroup)}&sort=${sortBy}&order=${sortOrder}${searchQuery ? `&q=${encodeURIComponent(searchQuery)}` : ''}`;
    }
    console.log('Fetching URL:', url);
    const response = await fetchJSON(url);
    console.log('API Response:', response);
    
    // Handle new API format: {meta: {...}, data: [...], active: [...], provisional: [...]}
    let data = [];
    let active = [];
    let provisional = [];
    let meta = null;
    
    if (response && response.data && Array.isArray(response.data)) {
      console.log('Using API data (new format), setting rankings');
      console.log('Response data length:', response.data.length);
      console.log('Response active length:', response.active?.length || 0);
      console.log('Response provisional length:', response.provisional?.length || 0);
      data = response.data;
      active = response.active || [];
      provisional = response.provisional || [];
      meta = response.meta;
      
      // If active/provisional arrays are empty but we have data, put all data in active
      if (active.length === 0 && provisional.length === 0 && data.length > 0) {
        active = data;
        console.log('No active/provisional split found, using all data as active');
      }
      
      console.log('Final active length:', active.length);
      console.log('Final provisional length:', provisional.length);
    } else if (Array.isArray(response) && response.length) {
      console.log('Using API data (legacy format), setting rankings');
      data = response;
      active = response; // Use all data as active for legacy format
    } else {
      console.log('Using mock data');
      data = mockRankings;
      active = mockRankings;
    }
    
    setRankings(data);
    // Normalize data for U11/U12 compatibility
    const normalizeTeamData = (teams) => {
      return teams.map(team => ({
        ...team,
        Team: team.Team || team.display_name, // U11 uses display_name, U12 uses Team
        team_id: team.team_id || null // Ensure team_id exists for U11
      }));
    };
    
    setActiveTeams(normalizeTeamData(active));
    setProvisionalTeams(normalizeTeamData(provisional));
    setRankingsMeta(meta);
    
    console.log('State updated:', {
      rankingsLength: data.length,
      activeTeamsLength: active.length,
      provisionalTeamsLength: provisional.length
    });
    
    setView("rankings");
    setLoading(false);
  }

  async function openTeam(teamIdentifier, teamId = null) {
    setLoading(true); setError("");
    setActiveTeam(teamIdentifier);
    
    let url;
    if (ageGroup === "U11" && teamId) {
      // Use new ID-based API for U11
      url = `/api/v1/az/m/u11/teams/${teamId}/history`;
    } else {
      // Use legacy name-based API for U12
      url = `/api/team/${encodeURIComponent(teamIdentifier)}?state=${encodeURIComponent(state)}&gender=${encodeURIComponent(gender)}&year=${encodeURIComponent(year)}`;
    }
    
    const data = await fetchJSON(url);
    if (ageGroup === "U11") {
      // U11 API returns {team_id, display_name, games: [...]}
      if (data && data.games) {
        // Transform U11 format to match TeamHistoryPage expectations
        const transformedGames = data.games.map(game => ({
          Date: game.date,
          Opponent: game.opponent_display_name,
          GoalsFor: game.goals_for,
          GoalsAgainst: game.goals_against,
          Result: game.result,
          // Add any other fields that TeamHistoryPage might need
          performance: game.result === 'W' ? 'overperformed' : game.result === 'L' ? 'underperformed' : 'neutral'
        }));
        setHistory(transformedGames);
      } else {
        setHistory(mockHistory(teamIdentifier));
      }
    } else {
      // U12 API returns array directly
      if (Array.isArray(data) && data.length) setHistory(data);
      else setHistory(mockHistory(teamIdentifier));
    }
    
    setView("team");
    setLoading(false);
  }

  const getImpactColor = (bucket) => {
    switch (bucket) {
      case "good": return "bg-green-100 text-green-800";
      case "weak": return "bg-red-100 text-red-800";
      case "neutral": return "bg-gray-100 text-gray-800";
      default: return "bg-gray-100 text-gray-800";
    }
  };

  const getImpactIcon = (bucket) => {
    switch (bucket) {
      case "good": return "↑";
      case "weak": return "↓";
      case "neutral": return "•";
      default: return "•";
    }
  };

  return (
    <div className="min-h-screen">
      {/* Selector View */}
      {view === "select" && (
        <SelectorHero 
          onSelect={({ gender: g, ageGroup: ag, state: s }) => {
            setGender(g);
            setAgeGroup(ag);
            setState(s);
            goRankings(g, ag, s);
          }}
        />
      )}

      {/* Rankings View */}
      {view === "rankings" && (
        <RankingsPage
          activeTeams={activeTeams}
          provisionalTeams={provisionalTeams}
          onBack={() => setView("select")}
          onTeamClick={openTeam}
          title={`${gender === "MALE" ? "Boys" : "Girls"} ${ageGroup} ${state} Rankings`}
          subtitle="View team rankings, power scores, and performance summaries."
        />
      )}

      {/* Team History View */}
      {view === "team" && (
        <TeamHistoryPage
          teamName={activeTeam}
          games={history}
          onBack={() => setView("rankings")}
          onOpponentClick={openTeam}
        />
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}
    </div>
  );
}
