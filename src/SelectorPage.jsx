import React, { useState } from "react";
import "./SelectorPage.css";

export default function SelectorPage({ onSelect }) {
  const [gender, setGender] = useState("");
  const [age, setAge] = useState("");
  const [state, setState] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (gender && age && state) {
      onSelect({ gender, age, state });
    } else {
      alert("Please select gender, age group, and state to continue.");
    }
  };

  return (
    <div className="selector-container">
      <header className="selector-header">
        <h1>Youth Soccer Rankings</h1>
        <p>Choose your division to view team rankings and game histories.</p>
      </header>

      <form className="selector-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Gender</label>
          <div className="option-row">
            <button
              type="button"
              className={`option ${gender === "boys" ? "active" : ""}`}
              onClick={() => setGender("boys")}
            >
              ⚽ Boys
            </button>
            <button
              type="button"
              className={`option ${gender === "girls" ? "active" : ""}`}
              onClick={() => setGender("girls")}
            >
              🏆 Girls
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>Age Group</label>
          <select
            value={age}
            onChange={(e) => setAge(e.target.value)}
            className="dropdown"
          >
            <option value="">Select Year</option>
            {[...Array(10)].map((_, i) => {
              const year = 2018 - i;
              return (
                <option key={year} value={year}>
                  {year}
                </option>
              );
            })}
          </select>
        </div>

        <div className="form-group">
          <label>State</label>
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="dropdown"
          >
            <option value="">Select State</option>
            {[
              "AZ",
              "CA", 
              "CO",
              "FL",
              "GA",
              "ID",
              "MI",
              "MN",
              "VA",
              "MD",
            ].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <button type="submit" className="go-btn">
          View Rankings →
        </button>
      </form>
    </div>
  );
}




