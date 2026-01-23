import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import requests

def load_mock_database():
    """
    Creates sample data for Providers (Supply) and Members (Demand).
    """
    # Providers: 2 in St. Louis, 0 in Florissant, 0 in Chicago
    providers = [
        {"id": "P1", "name": "Dr. Smith", "specialty": "Cardiology", "city": "St. Louis", "state": "MO"},
        {"id": "P2", "name": "Dr. Jones", "specialty": "Cardiology", "city": "St. Louis", "state": "MO"},
        {"id": "P3", "name": "Dr. Ray",   "specialty": "Pediatrics",  "city": "Clayton",   "state": "MO"},
        {"id": "P4", "name": "Dr. Adams", "specialty": "Cardiology", "city": "Dallas",    "state": "TX"}, # Adequate
        {"id": "P5", "name": "Dr. Lee",   "specialty": "Cardiology", "city": "New York",  "state": "NY"}, # Adequate
    ]

    # Members: Demand exists in MO, IL, TX, NY
    members = [
        {"id": "M1", "city": "St. Louis",  "state": "MO", "needs": ["Cardiology"]},
        {"id": "M2", "city": "Florissant", "state": "MO", "needs": ["Cardiology"]}, # Gap
        {"id": "M3", "city": "Florissant", "state": "MO", "needs": ["Cardiology"]}, # Gap
        {"id": "M4", "city": "Florissant", "state": "MO", "needs": ["Cardiology"]}, # Gap
        {"id": "M5", "city": "Chicago",    "state": "IL", "needs": ["Cardiology"]}, # Gap
        {"id": "M6", "city": "Dallas",     "state": "TX", "needs": ["Cardiology"]}, # Covered
        {"id": "M7", "city": "New York",   "state": "NY", "needs": ["Cardiology"]}, # Covered
    ]

    return pd.DataFrame(providers), pd.DataFrame(members)


def analyze_network_gaps(df_providers, df_members, target_specialty):
    """
    Calculates Supply vs Demand per State and determines Status.
    """
    print(f"--- Running Analysis for: {target_specialty} ---")

    # Filter by Specialty
    rel_prov = df_providers[df_providers["specialty"].str.contains(target_specialty, case=False, na=False)]
    rel_memb = df_members[df_members["needs"].apply(lambda x: target_specialty in x)]

    # Group by State to find total Supply/Demand
    state_demand = rel_memb.groupby("state").size().reset_index(name="demand")
    state_supply = rel_prov.groupby("state").size().reset_index(name="supply")

    # Merge Data (Outer join ensures we capture states with demand but no supply)
    analysis = pd.merge(state_demand, state_supply, on="state", how="outer").fillna(0)

    # Logic: Determine Status
    def determine_status(row):
        if row['demand'] > 0 and row['supply'] == 0:
            return "Critical Gap"
        elif row['demand'] > row['supply']:
            return "Underserved"
        elif row['demand'] == 0:
            return "No Demand"
        else:
            return "Adequate"

    analysis['status'] = analysis.apply(determine_status, axis=1)
    analysis['gap_count'] = (analysis['demand'] - analysis['supply']).clip(lower=0)
    
    return analysis

def generate_us_heatmap(df_analysis):
    """
    Plots a US Map color-coded by the 'status' column.
    """
    print("--- Generating Geographical Map ---")

    # A. Load US Map Geometry (GeoJSON)
    # This URL is a standard source for US State boundaries
    url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json"
    
    try:
        usa_geo = gpd.read_file(url)
    except Exception as e:
        print(f"Error downloading map data: {e}")
        return

    # B. Merge Analysis Data with Map Geometry
    # The GeoJSON uses 'id' for state abbreviations (MO, IL, etc.)
    usa_map = usa_geo.merge(df_analysis, left_on='id', right_on='state', how='left')
    usa_map['status'] = usa_map['status'].fillna('No Data')

    # C. Define Color Scheme
    color_dict = {
        'Critical Gap': '#d62728', # Red
        'Underserved':  '#ff7f0e', # Orange
        'Adequate':     '#2ca02c', # Green
        'No Data':      '#eeeeee'  # Light Grey
    }
    
    # Map colors to the dataframe
    usa_map['color'] = usa_map['status'].map(color_dict)

    # D. Plotting
    fig, ax = plt.subplots(figsize=(15, 10))

    # Plot the states
    usa_map.plot(
        ax=ax,
        color=usa_map['color'],
        edgecolor='white',
        linewidth=0.8
    )

    # Zoom in on Mainland US (Exclude Alaska/Hawaii for cleaner view)
    ax.set_xlim([-128, -65])
    ax.set_ylim([24, 50])
    ax.set_axis_off()

    # E. Add Annotations (Gap Counts)
    # Only label states that have a gap
    gap_states = usa_map[usa_map['gap_count'] > 0]
    
    for _, row in gap_states.iterrows():
        # Get center of the state polygon
        centroid = row.geometry.centroid
        plt.text(
            centroid.x, centroid.y, 
            f"{row['id']}\n-{int(row['gap_count'])}", 
            fontsize=10, 
            ha='center', va='center', 
            color='white', fontweight='bold',
            bbox=dict(facecolor='black', alpha=0.3, edgecolor='none', pad=1)
        )

    # F. Add Legend
    patches = [mpatches.Patch(color=color, label=label) for label, color in color_dict.items()]
    plt.legend(handles=patches, loc='lower right', title="Network Status", frameon=True)

    plt.title('Network Adequacy Heatmap: Cardiology', fontsize=18, fontweight='bold')
    
    # Save and Show
    output_file = 'network_adequacy_map.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Map saved to {output_file}")
    plt.show()

if __name__ == "__main__":
    # 1. Load Data
    providers, members = load_mock_database()
    
    # 2. Run Analysis
    # We are looking for Cardiologists
    results = analyze_network_gaps(providers, members, "Cardiology")
    
    print("\n--- ANALYSIS RESULTS ---")
    print(results[['state', 'demand', 'supply', 'status', 'gap_count']])
    
    # 3. Create Map
    generate_us_heatmap(results)