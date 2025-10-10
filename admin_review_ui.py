"""
Admin Review UI - Phase C
Enhanced interface for managing team aliases and missing sources
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def load_aliases() -> Dict[str, List[str]]:
    """Load team aliases from JSON file."""
    aliases_path = Path("team_aliases.json")
    if aliases_path.exists():
        with open(aliases_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_aliases(aliases: Dict[str, List[str]]) -> bool:
    """Save team aliases to JSON file with audit log."""
    try:
        aliases_path = Path("team_aliases.json")
        
        # Create backup
        if aliases_path.exists():
            backup_path = Path(f"team_aliases_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            aliases_path.rename(backup_path)
        
        # Save new aliases
        with open(aliases_path, 'w', encoding='utf-8') as f:
            json.dump(aliases, f, indent=2, ensure_ascii=False)
        
        # Log to audit file
        audit_path = Path("admin_audit.log")
        with open(audit_path, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - Aliases updated by admin\n")
        
        return True
    except Exception as e:
        st.error(f"Failed to save aliases: {e}")
        return False

def create_audit_log(action: str, details: str):
    """Create audit log entry."""
    audit_path = Path("admin_audit.log")
    with open(audit_path, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().isoformat()} - {action}: {details}\n")

def main():
    """Main admin interface."""
    st.set_page_config(
        page_title="Admin Review Interface",
        page_icon="⚙️",
        layout="wide"
    )
    
    st.title("⚙️ Admin Review Interface")
    st.markdown("Manage team aliases and missing sources")
    
    # Authentication check (simple for now)
    if "admin_authenticated" not in st.session_state:
        password = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if password == "admin123":  # Change this in production
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Invalid password")
        return
    
    # Load data
    review_df = load_review_queue()
    master_teams = load_master_teams()
    aliases = load_aliases()
    
    # Sidebar navigation
    st.sidebar.title("Admin Navigation")
    page = st.sidebar.selectbox("Select Page", [
        "Team Resolution Review",
        "Alias Management", 
        "Missing Sources",
        "Audit Log"
    ])
    
    if page == "Team Resolution Review":
        team_resolution_review_page(review_df, master_teams, aliases)
    elif page == "Alias Management":
        alias_management_page(aliases)
    elif page == "Missing Sources":
        missing_sources_page()
    elif page == "Audit Log":
        audit_log_page()

def team_resolution_review_page(review_df: pd.DataFrame, master_teams: List[str], aliases: Dict[str, List[str]]):
    """Team resolution review interface."""
    st.header("Team Resolution Review")
    
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
                    if st.button("Approve", key=f"approve_{team}_{suggestion}"):
                        # Add to aliases
                        if suggestion not in aliases:
                            aliases[suggestion] = []
                        if team not in aliases[suggestion]:
                            aliases[suggestion].append(team)
                        save_aliases(aliases)
                        create_audit_log("ALIAS_APPROVED", f"{team} -> {suggestion}")
                        st.success(f"Added '{team}' as alias for '{suggestion}'")
                        st.rerun()
                with col3:
                    if st.button("Reject", key=f"reject_{team}_{suggestion}"):
                        create_audit_log("ALIAS_REJECTED", f"{team} -> {suggestion}")
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
                create_audit_log("MANUAL_ALIAS_ADDED", f"{team} -> {manual_match}")
                st.success(f"Added '{team}' as alias for '{manual_match}'")
                st.rerun()

def alias_management_page(aliases: Dict[str, List[str]]):
    """Alias management interface."""
    st.header("Alias Management")
    
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
                            create_audit_log("ALIAS_REMOVED", f"{variant} from {master_team}")
                            st.rerun()
    else:
        st.info("No aliases match your search criteria.")

def missing_sources_page():
    """Missing sources management."""
    st.header("Missing Sources")
    
    st.markdown("### Add Missing Source")
    
    with st.form("add_source_form"):
        source_name = st.text_input("Source Name", placeholder="e.g., Tournament XYZ")
        source_url = st.text_input("Source URL", placeholder="https://example.com/results")
        source_type = st.selectbox("Source Type", ["HTML", "JSON", "CSV"])
        notes = st.text_area("Notes", placeholder="Additional information about this source")
        
        if st.form_submit_button("Queue for Scraper"):
            # Create source request
            source_request = {
                "name": source_name,
                "url": source_url,
                "type": source_type.lower(),
                "notes": notes,
                "requested_at": datetime.now().isoformat(),
                "status": "pending"
            }
            
            # Save to queue file
            queue_path = Path("missing_sources_queue.json")
            queue_data = []
            
            if queue_path.exists():
                with open(queue_path, 'r') as f:
                    queue_data = json.load(f)
            
            queue_data.append(source_request)
            
            with open(queue_path, 'w') as f:
                json.dump(queue_data, f, indent=2)
            
            create_audit_log("SOURCE_REQUESTED", f"{source_name} - {source_url}")
            st.success(f"Source '{source_name}' queued for scraper adapter development")
    
    # Show pending requests
    queue_path = Path("missing_sources_queue.json")
    if queue_path.exists():
        with open(queue_path, 'r') as f:
            queue_data = json.load(f)
        
        if queue_data:
            st.markdown("### Pending Source Requests")
            
            for i, request in enumerate(queue_data):
                with st.expander(f"**{request['name']}** - {request['status']}"):
                    st.write(f"**URL:** {request['url']}")
                    st.write(f"**Type:** {request['type']}")
                    st.write(f"**Notes:** {request['notes']}")
                    st.write(f"**Requested:** {request['requested_at']}")
                    
                    if st.button("Mark Complete", key=f"complete_{i}"):
                        queue_data[i]['status'] = 'completed'
                        with open(queue_path, 'w') as f:
                            json.dump(queue_data, f, indent=2)
                        create_audit_log("SOURCE_COMPLETED", f"{request['name']}")
                        st.rerun()

def audit_log_page():
    """Audit log viewer."""
    st.header("Audit Log")
    
    audit_path = Path("admin_audit.log")
    if audit_path.exists():
        with open(audit_path, 'r') as f:
            log_content = f.read()
        
        st.text_area("Audit Log", log_content, height=400)
        
        if st.button("Clear Log"):
            audit_path.unlink()
            st.success("Audit log cleared")
            st.rerun()
    else:
        st.info("No audit log found.")

if __name__ == "__main__":
    main()
