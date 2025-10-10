// Frontend integration example for the updated API
// This shows how to handle the new meta/data response structure

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

// Updated rankings fetch with new response structure
export const fetchRankings = async (state, gender, year, options = {}) => {
  const params = new URLSearchParams({
    state: state || '',
    gender: gender || '',
    year: year || '',
    limit: options.limit || 500,
    include_inactive: options.includeInactive || false,
    sort: options.sort || 'PowerScore',
    order: options.order || 'desc'
  });

  try {
    const response = await fetch(`${API_BASE}/api/rankings?${params}`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const payload = await response.json();
    
    // Handle new meta/data structure
    return {
      teams: Array.isArray(payload?.data) ? payload.data : [],
      meta: payload?.meta || {},
      error: null
    };
  } catch (error) {
    return {
      teams: [],
      meta: {},
      error: error.message
    };
  }
};

// Example React component usage
export const RankingsComponent = () => {
  const [rankings, setRankings] = useState([]);
  const [meta, setMeta] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadRankings = async (state = 'AZ', gender = 'MALE', year = '2014') => {
    setLoading(true);
    setError(null);
    
    const result = await fetchRankings(state, gender, year, {
      includeInactive: false,
      limit: 100
    });
    
    if (result.error) {
      setError(result.error);
    } else {
      setRankings(result.teams);
      setMeta(result.meta);
    }
    
    setLoading(false);
  };

  useEffect(() => {
    loadRankings();
  }, []);

  return (
    <div>
      <h2>Team Rankings</h2>
      
      {/* Show meta information */}
      {meta.slice && (
        <div className="meta-info">
          <span>Showing: {meta.slice.state} {meta.slice.gender} {meta.slice.year}</span>
          <span>Records: {meta.records}</span>
          {meta.hidden_inactive > 0 && (
            <span className="inactive-badge">
              ({meta.hidden_inactive} hidden inactive)
            </span>
          )}
        </div>
      )}
      
      {/* Loading state */}
      {loading && <div>Loading...</div>}
      
      {/* Error state */}
      {error && <div className="error">Error: {error}</div>}
      
      {/* Rankings table */}
      {rankings.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Team</th>
              <th>Power Score</th>
              <th>Adjusted Score</th>
              <th>Games Played</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((team) => (
              <tr key={team.Team}>
                <td>{team.Rank}</td>
                <td>{team.Team}</td>
                <td>{team.PowerScore?.toFixed(3)}</td>
                <td>{team.PowerScore_adj?.toFixed(3)}</td>
                <td>{team.GamesPlayed}</td>
                <td>
                  <span className={`status ${team.Status?.toLowerCase()}`}>
                    {team.Status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

// CSS for status badges
const statusStyles = `
.status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
}

.status.active {
  background-color: #d4edda;
  color: #155724;
}

.status.provisional {
  background-color: #fff3cd;
  color: #856404;
}

.inactive-badge {
  background-color: #f8d7da;
  color: #721c24;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.8em;
  margin-left: 8px;
}

.meta-info {
  margin-bottom: 16px;
  padding: 8px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.meta-info span {
  margin-right: 16px;
}
`;

export default RankingsComponent;

