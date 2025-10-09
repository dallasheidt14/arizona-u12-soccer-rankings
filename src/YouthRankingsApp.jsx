import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Search, ChevronRight, Users, Table as TableIcon, ArrowLeft } from "lucide-react";

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
  const [year, setYear] = useState("2025");
  const [state, setState] = useState("AZ");

  const [slices, setSlices] = useState([]);
  const [rankings, setRankings] = useState([]);
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

  async function goRankings() {
    setLoading(true); setError("");
    // Prefer API JSON; fallback to mock
    const url = `/api/rankings?state=${encodeURIComponent(state)}&gender=${encodeURIComponent(gender)}&year=${encodeURIComponent(year)}&sort=${sortBy}&order=${sortOrder}${searchQuery ? `&q=${encodeURIComponent(searchQuery)}` : ''}`;
    console.log('Fetching URL:', url);
    const data = await fetchJSON(url);
    console.log('API Response:', data);
    console.log('Data type:', typeof data);
    console.log('Is array:', Array.isArray(data));
    console.log('Data length:', data?.length);
    if (Array.isArray(data) && data.length) {
      console.log('Using API data, setting rankings');
      setRankings(data);
    } else {
      console.log('Using mock data');
      setRankings(mockRankings);
    }
    setView("rankings");
    setLoading(false);
  }

  async function openTeam(teamName) {
    setLoading(true); setError("");
    setActiveTeam(teamName);
    const url = `/api/team/${encodeURIComponent(teamName)}?state=${encodeURIComponent(state)}&gender=${encodeURIComponent(gender)}&year=${encodeURIComponent(year)}`;
    const data = await fetchJSON(url);
    if (Array.isArray(data) && data.length) setHistory(data);
    else setHistory(mockHistory(teamName));
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
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Youth Soccer Rankings</h1>
          <p className="text-lg text-gray-600">Select your criteria to view team rankings and game histories</p>
        </div>

        {/* Selector View */}
        {view === "select" && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto"
          >
            <div className="bg-white rounded-lg shadow-lg p-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center">Select Rankings Criteria</h2>
              
              <div className="space-y-6">
                {/* Gender Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">Gender</label>
                  <div className="grid grid-cols-2 gap-4">
                    <button
                      onClick={() => setGender("MALE")}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        gender === "MALE" 
                          ? "border-blue-500 bg-blue-50 text-blue-700" 
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <Users className="w-6 h-6 mx-auto mb-2" />
                      <div className="font-medium">Boys</div>
                    </button>
                    <button
                      onClick={() => setGender("FEMALE")}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        gender === "FEMALE" 
                          ? "border-blue-500 bg-blue-50 text-blue-700" 
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <Users className="w-6 h-6 mx-auto mb-2" />
                      <div className="font-medium">Girls</div>
                    </button>
                  </div>
                </div>

                {/* Year Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">Birth Year</label>
                  <select
                    value={year}
                    onChange={(e) => setYear(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {years.map(y => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>

                {/* State Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">State</label>
                  <select
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {statesFromIndex.map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>

                {/* View Rankings Button */}
                <button
                  onClick={goRankings}
                  disabled={loading}
                  className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <>
                      <TableIcon className="w-5 h-5 mr-2" />
                      View Rankings
                      <ChevronRight className="w-5 h-5 ml-2" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Rankings View */}
        {view === "rankings" && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            {/* Header with Back Button */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => setView("select")}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Back to Selector
              </button>
              <h2 className="text-2xl font-semibold text-gray-900">
                {gender === "MALE" ? "Boys" : "Girls"} {year} {state} Rankings
              </h2>
            </div>

            {/* Search and Sort Controls */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                      type="text"
                      placeholder="Search teams..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="PowerScore">Power Score</option>
                    <option value="Off_norm">Offense</option>
                    <option value="Def_norm">Defense</option>
                    <option value="SOS_norm">SOS</option>
                    <option value="GamesPlayed">Games Played</option>
                  </select>
                  <button
                    onClick={() => setSortOrder(sortOrder === "desc" ? "asc" : "desc")}
                    className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    {sortOrder === "desc" ? "↓" : "↑"}
                  </button>
                  <button
                    onClick={goRankings}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Apply
                  </button>
                </div>
              </div>
            </div>

            {/* Rankings Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rank</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Team</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Power Score</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Offense</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Defense</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SOS</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Games</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">W-L-T</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {rankings.map((team, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {team.Rank}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <button
                            onClick={() => openTeam(team.Team)}
                            className="text-sm font-medium text-blue-600 hover:text-blue-900 transition-colors"
                          >
                            {team.Team}
                          </button>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {team.PowerScore ? team.PowerScore.toFixed(3) : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {team.Off_norm ? team.Off_norm.toFixed(3) : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {team.Def_norm ? team.Def_norm.toFixed(3) : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {team.SOS_norm ? team.SOS_norm.toFixed(3) : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {team.GamesPlayed || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {team.WL || 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}

        {/* Team History View */}
        {view === "team" && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            {/* Header with Back Button */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => setView("rankings")}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                Back to Rankings
              </button>
              <h2 className="text-2xl font-semibold text-gray-900">
                {activeTeam} - Game History
              </h2>
            </div>

            {/* Game History Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Opponent</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expected GD</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Performance</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Opponent Strength</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {history.map((game, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {game.Date}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {game.Opponent}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {game.GoalsFor} - {game.GoalsAgainst}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {game.expected_gd ? game.expected_gd.toFixed(2) : 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {game.impact_bucket && (
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getImpactColor(game.impact_bucket)}`}>
                              {getImpactIcon(game.impact_bucket)} {game.gd_delta ? game.gd_delta.toFixed(2) : 'N/A'}
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {game.Opponent_BaseStrength && (
                            <div className="flex items-center">
                              <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                <div 
                                  className="bg-blue-600 h-2 rounded-full" 
                                  style={{ width: `${Math.min(100, game.Opponent_BaseStrength * 100)}%` }}
                                ></div>
                              </div>
                              <span className="text-xs text-gray-500">
                                {(game.Opponent_BaseStrength * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
