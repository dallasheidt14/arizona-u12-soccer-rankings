"""
Alias Operations UI
Streamlit interface for managing team name aliases and low-confidence matches
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_aliases() -> Dict[str, List[str]]:
    """Load team aliases from JSON file."""
    aliases_path = Path("team_aliases.json")
    if aliases_path.exists():
        with open(aliases_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_aliases(aliases: Dict[str, List[str]]) -> bool:
    """Save team aliases to JSON file."""
    try:
        aliases_path = Path("team_aliases.json")
        with open(aliases_path, 'w', encoding='utf-8') as f:
            json.dump(aliases, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Failed to save aliases: {e}")
        return False

def load_review_queue() -> pd.DataFrame:
    """Load team resolution review queue."""
    review_path = Path("data_ingest/silver/team_resolution_review.csv")
    if review_path.exists():
        return pd.read_csv(review_path)
    return pd.DataFrame()

def load_master_teams() -> List[str]:
    """Load master team list."""
    master_path = Path("AZ MALE U12 MASTER TEAM LIST.csv")
    if master_path.exists():
        df = pd.read_csv(master_path)
        return df["Team Name"].tolist()
    return []

def main():
    st.set_page_config(
        page_title="Team Alias Operations",
        page_icon="⚽",
        layout="wide"
    )
    
    st.title("⚽ Team Alias Operations")
    st.markdown("Manage team name aliases and resolve low-confidence matches")
    
    # Load data
    aliases = load_aliases()
    review_df = load_review_queue()
    master_teams = load_master_teams()
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Select Page", [
        "View Aliases",
        "Manage Review Queue", 
        "Add New Alias",
        "Bulk Operations"
    ])
    
    if page == "View Aliases":
        view_aliases_page(aliases)
    elif page == "Manage Review Queue":
        manage_review_queue_page(review_df, master_teams, aliases)
    elif page == "Add New Alias":
        add_alias_page(master_teams, aliases)
    elif page == "Bulk Operations":
        bulk_operations_page(aliases)

def view_aliases_page(aliases: Dict[str, List[str]]):
    """Display current aliases."""
    st.header("Current Team Aliases")
    
    if not aliases:
        st.info("No aliases configured yet.")
        return
    
    # Summary stats
    total_aliases = sum(len(variants) for variants in aliases.values())
    st.metric("Total Aliases", total_aliases)
    st.metric("Master Teams", len(aliases))
    
    # Search and filter
    search_term = st.text_input("Search aliases", placeholder="Enter team name...")
    
    # Display aliases
    filtered_aliases = {}
    for master_team, variants in aliases.items():
        if not search_term or search_term.lower() in master_team.lower():
            filtered_aliases[master_team] = variants
    
    if filtered_aliases:
        for master_team, variants in filtered_aliases.items():
            with st.expander(f"**{master_team}** ({len(variants)} variants)"):
                for i, variant in enumerate(variants):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"• {variant}")
                    with col2:
                        if st.button("Remove", key=f"remove_{master_team}_{i}"):
                            aliases[master_team].remove(variant)
                            if not aliases[master_team]:
                                del aliases[master_team]
                            save_aliases(aliases)
                            st.rerun()
    else:
        st.info("No aliases match your search criteria.")

def manage_review_queue_page(review_df: pd.DataFrame, master_teams: List[str], aliases: Dict[str, List[str]]):
    """Manage the review queue for low-confidence matches."""
    st.header("Team Resolution Review Queue")
    
    if review_df.empty:
        st.info("No items in review queue.")
        return
    
    st.info(f"Found {len(review_df)} items requiring review")
    
    # Group by team for easier review
    unique_teams = review_df["home_team_raw"].dropna().unique()
    
    for team in unique_teams:
        team_matches = review_df[review_df["home_team_raw"] == team]
        
        with st.expander(f"**{team}** ({len(team_matches)} occurrences)"):
            st.write("**Suggested matches:**")
            
            # Show fuzzy match suggestions
            from rapidfuzz import process, fuzz
            
            suggestions = process.extract(team, master_teams, scorer=fuzz.WRatio, limit=5)
            
            for suggestion, score, _ in suggestions:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"• {suggestion} (confidence: {score:.1f}%)")
                with col2:
                    if st.button("Accept", key=f"accept_{team}_{suggestion}"):
                        # Add to aliases
                        if suggestion not in aliases:
                            aliases[suggestion] = []
                        if team not in aliases[suggestion]:
                            aliases[suggestion].append(team)
                        save_aliases(aliases)
                        st.success(f"Added '{team}' as alias for '{suggestion}'")
                        st.rerun()
                with col3:
                    if st.button("Reject", key=f"reject_{team}_{suggestion}"):
                        st.info(f"Rejected '{team}' -> '{suggestion}'")
            
            # Manual entry option
            st.write("**Manual entry:**")
            manual_match = st.selectbox(
                "Select master team",
                [""] + master_teams,
                key=f"manual_{team}"
            )
            
            if manual_match and st.button("Add Manual Alias", key=f"manual_add_{team}"):
                if manual_match not in aliases:
                    aliases[manual_match] = []
                if team not in aliases[manual_match]:
                    aliases[manual_match].append(team)
                save_aliases(aliases)
                st.success(f"Added '{team}' as alias for '{manual_match}'")
                st.rerun()

def add_alias_page(master_teams: List[str], aliases: Dict[str, List[str]]):
    """Add new team aliases manually."""
    st.header("Add New Team Alias")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Master Team")
        master_team = st.selectbox(
            "Select master team",
            master_teams,
            key="new_master_team"
        )
    
    with col2:
        st.subheader("Alias Variants")
        alias_input = st.text_area(
            "Enter alias variants (one per line)",
            placeholder="FC Arizona 2014 Boys\nFC AZ 2014B\nArizona FC 14B",
            key="new_aliases"
        )
    
    if st.button("Add Aliases"):
        if master_team and alias_input:
            variants = [line.strip() for line in alias_input.split('\n') if line.strip()]
            
            if master_team not in aliases:
                aliases[master_team] = []
            
            added_count = 0
            for variant in variants:
                if variant not in aliases[master_team]:
                    aliases[master_team].append(variant)
                    added_count += 1
            
            if save_aliases(aliases):
                st.success(f"Added {added_count} new aliases for '{master_team}'")
                st.rerun()
        else:
            st.error("Please select a master team and enter alias variants")

def bulk_operations_page(aliases: Dict[str, List[str]]):
    """Bulk operations on aliases."""
    st.header("Bulk Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Export Aliases")
        if st.button("Download Aliases JSON"):
            aliases_json = json.dumps(aliases, indent=2, ensure_ascii=False)
            st.download_button(
                label="Download team_aliases.json",
                data=aliases_json,
                file_name="team_aliases.json",
                mime="application/json"
            )
    
    with col2:
        st.subheader("Import Aliases")
        uploaded_file = st.file_uploader(
            "Upload aliases JSON file",
            type=['json'],
            key="import_aliases"
        )
        
        if uploaded_file and st.button("Import Aliases"):
            try:
                new_aliases = json.load(uploaded_file)
                if isinstance(new_aliases, dict):
                    aliases.update(new_aliases)
                    if save_aliases(aliases):
                        st.success("Aliases imported successfully")
                        st.rerun()
                else:
                    st.error("Invalid JSON format")
            except Exception as e:
                st.error(f"Import failed: {e}")
    
    # Statistics
    st.subheader("Alias Statistics")
    total_aliases = sum(len(variants) for variants in aliases.values())
    avg_aliases_per_team = total_aliases / len(aliases) if aliases else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Master Teams", len(aliases))
    with col2:
        st.metric("Total Aliases", total_aliases)
    with col3:
        st.metric("Avg Aliases/Team", f"{avg_aliases_per_team:.1f}")
    
    # Cleanup operations
    st.subheader("Cleanup Operations")
    
    if st.button("Remove Duplicate Aliases"):
        cleaned_count = 0
        for master_team, variants in aliases.items():
            original_count = len(variants)
            aliases[master_team] = list(set(variants))  # Remove duplicates
            cleaned_count += original_count - len(aliases[master_team])
        
        if cleaned_count > 0:
            save_aliases(aliases)
            st.success(f"Removed {cleaned_count} duplicate aliases")
            st.rerun()
        else:
            st.info("No duplicate aliases found")

if __name__ == "__main__":
    main()
