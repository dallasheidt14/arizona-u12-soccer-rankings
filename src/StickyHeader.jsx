import React, { useState, useEffect } from "react";
import "./StickyHeader.css";

export default function StickyHeader({ 
  title, 
  subtitle, 
  onBack, 
  searchQuery, 
  onSearchChange, 
  sortBy, 
  onSortChange 
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

  return (
    <div className={`page-header ${isScrolled ? 'scrolled' : ''}`}>
      <div className="header-top">
        <button className="back-btn" onClick={onBack}>
          ← Back to Selector
        </button>
        <h1>{title}</h1>
      </div>

      <p className="subtitle">{subtitle}</p>

      <div className="filter-bar">
        <h2 className="ranking-title">{title}</h2>
        <div className="search-box">
          <i className="search-icon">🔍</i>
          <input 
            type="text" 
            placeholder="Search teams..." 
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
          <select value={sortBy} onChange={(e) => onSortChange(e.target.value)}>
            <option value="PowerScore_adj">Power Score</option>
            <option value="Off_norm">Offense</option>
            <option value="Def_norm">Defense</option>
            <option value="SOS_norm">SOS</option>
            <option value="GamesPlayed">Games Played</option>
          </select>
        </div>
      </div>
    </div>
  );
}




