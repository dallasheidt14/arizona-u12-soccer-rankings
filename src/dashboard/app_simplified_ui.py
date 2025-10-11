"""
Simplified Frontend Component - Remove Division Field
Keep: Gender, Age Group (Birth Year), State
Remove: Division (auto-generate from selections)
"""
import streamlit as st

# Page setup
st.set_page_config(page_title="Arizona Soccer Rankings", layout="wide")

st.title("🏆 Arizona Soccer Rankings")
st.caption("Select gender, age group, and state to view rankings")

# Create columns for better layout
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Gender")
    gender = st.radio(
        "Choose Gender",
        ["Boys", "Girls"],
        format_func=lambda x: f"⚽ {x}" if x == "Boys" else f"🏆 {x}",
        horizontal=True
    )

with col2:
    st.subheader("Age Group (Birth Year)")
    birth_years = ["2012", "2013", "2014", "2015", "2016"]
    age_labels = {
        "2012": "U14 (2012)",
        "2013": "U13 (2013)", 
        "2014": "U12 (2014)",
        "2015": "U11 (2015)",
        "2016": "U10 (2016)"
    }
    
    birth_year = st.selectbox(
        "Birth Year",
        birth_years,
        format_func=lambda x: age_labels[x],
        index=2  # Default to 2014 (U12)
    )

with col3:
    st.subheader("State")
    state = st.selectbox(
        "State",
        ["AZ", "CA", "TX", "FL", "NY"],
        index=0  # Default to AZ
    )

# Auto-generate division from selections
division = f"Arizona {gender} {age_labels[birth_year]}"

st.markdown("---")
st.markdown(f"**Selected:** {division}")

# Show rankings button
if st.button("Show Rankings →", type="primary"):
    # Convert to API parameters
    gender_code = "boys" if gender == "Boys" else "girls"
    age_group = age_labels[birth_year].split()[0]  # Extract U12, U13, etc.
    
    st.success(f"Loading rankings for {division}")
    st.info(f"API Call: /api/rankings?gender={gender_code}&age_group={age_group}&state={state}")
    
    # Here you would make the actual API call and display results
    st.markdown("**Rankings would be displayed here...**")

# Footer
st.markdown("---")
st.caption("Data window: last 12 months, up to 30 most recent matches (reduced weight for 26-30)")
