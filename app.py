import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration
st.set_page_config(page_title="🏁 F1 Historical Insights Dashboard", layout="wide")

# -------------------------------------------------------------------------
# 1. OPTIMIZED DATA LOADING
# -------------------------------------------------------------------------
@st.cache_data
def load_data():
    races = pd.read_csv('races.csv')
    drivers = pd.read_csv('drivers.csv')
    constructors = pd.read_csv('constructors.csv')
    driver_standings = pd.read_csv('driver_standings.csv')
    constructor_standings = pd.read_csv('constructor_standings.csv')
    qualifying = pd.read_csv('qualifying.csv')
    lap_times = pd.read_csv('lap_times.csv')
    pit_stops = pd.read_csv('pit_stops.csv')
    
    # Handle '\N' null representations present in Ergast datasets safely
    for df in [drivers, qualifying]:
        if 'number' in df.columns:
            df['number'] = df['number'].replace(r'\N', '0')
            
    return races, drivers, constructors, driver_standings, constructor_standings, qualifying, lap_times, pit_stops

races, drivers, constructors, driver_standings, constructor_standings, qualifying, lap_times, pit_stops = load_data()

# -------------------------------------------------------------------------
# 2. SIDEBAR CONTROLS
# -------------------------------------------------------------------------
st.sidebar.header("🏎️ Dashboard Configuration")

# Select Season (Year)
available_years = sorted(races['year'].unique(), reverse=True)
selected_year = st.sidebar.selectbox("Select Season", available_years, index=available_years.index(2023) if 2023 in available_years else 0)

# Filter races by selected season
season_races = races[races['year'] == selected_year].sort_values(by='round')
race_options = season_races['name'].tolist()
selected_race_name = st.sidebar.selectbox("Select Grand Prix", race_options)

# Get specific race details
selected_race_row = season_races[season_races['name'] == selected_race_name].iloc[0]
selected_race_id = selected_race_row['raceId']

st.title(f"🏁 {selected_year} {selected_race_name} — Insights Hub")
st.markdown("Explore comprehensive historical results, lap-by-lap pace evolution, and pit lane strategies using raw timing data.")

# Create main dashboard tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🏆 Championship Standings", 
    "⏱️ Qualifying Analysis", 
    "📈 Race Pace Tracker", 
    "🛠️ Pit Lane Strategy"
])

# -------------------------------------------------------------------------
# TAB 1: CHAMPIONSHIP STANDINGS (CUMULATIVE UP TO SELECTED GP)
# -------------------------------------------------------------------------
with tab1:
    st.subheader(f"📊 Status as of the {selected_race_name} Formula 1 Grand Prix")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 👤 Driver Championship Standings")
        ds_subset = driver_standings[driver_standings['raceId'] == selected_race_id]
        if not ds_subset.empty:
            ds_merged = ds_subset.merge(drivers, on='driverId')
            ds_merged['Driver'] = ds_merged['forename'] + " " + ds_merged['surname']
            ds_display = ds_merged.sort_values(by='position')[['position', 'Driver', 'points', 'wins']].reset_index(drop=True)
            st.dataframe(ds_display, use_container_width=True)
        else:
            st.warning("No driver standings data found for this specific event.")
            
    with col2:
        st.markdown("#### 🏢 Constructor Championship Standings")
        cs_subset = constructor_standings[constructor_standings['raceId'] == selected_race_id]
        if not cs_subset.empty:
            cs_merged = cs_subset.merge(constructors, on='constructorId')
            cs_display = cs_merged.sort_values(by='position')[['position', 'name', 'points', 'wins']].rename(columns={'name': 'Constructor'}).reset_index(drop=True)
            st.dataframe(cs_display, use_container_width=True)
        else:
            st.warning("No constructor standings data found for this specific event.")

# -------------------------------------------------------------------------
# TAB 2: QUALIFYING PERFORMANCE
# -------------------------------------------------------------------------
with tab2:
    st.subheader("⏱️ Starting Grid & Timings")
    quali_subset = qualifying[qualifying['raceId'] == selected_race_id]
    
    if not quali_subset.empty:
        quali_merged = quali_subset.merge(drivers, on='driverId').merge(constructors, on='constructorId')
        quali_merged['Driver'] = quali_merged['forename'] + " " + quali_merged['surname']
        
        # Sort and clean up display columns
        quali_display = quali_merged.sort_values(by='position')[['position', 'Driver', 'name', 'q1', 'q2', 'q3']].rename(columns={'name': 'Team'}).reset_index(drop=True)
        st.dataframe(quali_display, use_container_width=True)
        
        # Visualizing Q3 gaps
        q3_drivers = quali_merged[quali_merged['q3'].notna() & (quali_merged['q3'] != r'\N')]
        if not q3_drivers.empty:
            # Quick string conversion function for time tracking: '1:30.123' -> 90.123
            def time_to_seconds(t_str):
                try:
                    if ':' in str(t_str):
                        parts = str(t_str).split(':')
                        return float(parts[0]) * 60 + float(parts[1])
                    return float(t_str)
                except ValueError:
                    return None
            
            q3_drivers['q3_sec'] = q3_drivers['q3'].apply(time_to_seconds)
            q3_drivers = q3_drivers.dropna(subset=['q3_sec']).sort_values(by='q3_sec')
            
            if not q3_drivers.empty:
                fig_quali = px.bar(
                    q3_drivers, 
                    x='q3_sec', 
                    y='Driver', 
                    orientation='h', 
                    color='name',
                    title='Top Shootout: Ultimate Q3 Times Compared',
                    labels={'q3_sec': 'Lap Time (Seconds)', 'Driver': 'Driver'},
                    range_x=[q3_drivers['q3_sec'].min() - 1, q3_drivers['q3_sec'].max() + 1]
                )
                fig_quali.update_layout(yaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig_quali, use_container_width=True)
    else:
        st.info("Qualifying timing metrics are unavailable for this race row entry.")

# -------------------------------------------------------------------------
# TAB 3: RACE PACE TRACKER (LAP TIMES OVER TIME)
# -------------------------------------------------------------------------
with tab3:
    st.subheader("📈 Inter-Driver Pace & Stated Evolution")
    race_laps = lap_times[lap_times['raceId'] == selected_race_id]
    
    if not race_laps.empty:
        race_laps_merged = race_laps.merge(drivers, on='driverId')
        race_laps_merged['Driver'] = race_laps_merged['forename'] + " " + race_laps_merged['surname']
        race_laps_merged['Lap Time (s)'] = race_laps_merged['milliseconds'] / 1000.0
        
        # Selection window for focusing on specific drivers to clean up charts
        driver_list = sorted(race_laps_merged['Driver'].unique())
        selected_drivers = st.multiselect("Select Drivers to Compare", driver_list, default=driver_list[:3])
        
        if selected_drivers:
            filtered_laps = race_laps_merged[race_laps_merged['Driver'].isin(selected_drivers)]
            
            fig_pace = px.line(
                filtered_laps, 
                x='lap', 
                y='Lap Time (s)', 
                color='Driver',
                title="Lap-by-Lap Stated Execution Over the Race Duration",
                labels={'lap': 'Lap Number', 'Lap Time (s)': 'Time in Seconds'}
            )
            # Clip outlier times (e.g., pit stops or safety cars) to make normal pace differences visible
            median_time = filtered_laps['Lap Time (s)'].median()
            fig_pace.update_layout(yaxis_range=[median_time - 5, median_time + 15])
            st.plotly_chart(fig_pace, use_container_width=True)
        else:
            st.info("Please select at least one driver above to render the live chart timeline.")
    else:
        st.warning("Lap-by-lap raw time tracking metrics are empty or missing for this historical event record.")

# -------------------------------------------------------------------------
# TAB 4: PIT LANE STRATEGY ANALYSIS
# -------------------------------------------------------------------------
with tab4:
    st.subheader("🛠️ Fast pit crews and execution windows")
    race_pits = pit_stops[pit_stops['raceId'] == selected_race_id]
    
    if not race_pits.empty:
        race_pits_merged = race_pits.merge(drivers, on='driverId')
        race_pits_merged['Driver'] = race_pits_merged['forename'] + " " + race_pits_merged['surname']
        race_pits_merged['Duration (s)'] = race_pits_merged['milliseconds'] / 1000.0
        
        # Remove massive structural outliers like red-flag stops if any
        clean_pits = race_pits_merged[race_pits_merged['Duration (s)'] < 50.0]
        
        fig_pit = px.scatter(
            clean_pits,
            x='lap',
            y='Duration (s)',
            color='Driver',
            size='stop',
            title='Pit Stop Execution Window Index vs. Out-of-Car Duration',
            labels={'lap': 'Lap Position Trigger', 'Duration (s)': 'Time Spent in Pit Lane (s)'}
        )
        st.plotly_chart(fig_pit, use_container_width=True)
        
        # Rankings summary metrics
        st.markdown("#### ⏱️ Quickest Pit Visits (Stationary + Lane Limit Duration)")
        rankings = clean_pits.sort_values(by='Duration (s)')[['stop', 'lap', 'Driver', 'Duration (s)']].reset_index(drop=True)
        st.dataframe(rankings.head(10), use_container_width=True)
    else:
        st.info("Pit stop transaction metric logs were not recorded for this specific race era.")