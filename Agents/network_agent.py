import ollama
import json
import pandas as pd
from geopy.distance import geodesic
from typing import List, Dict

def load_mock_database():
    providers = [
        {"id": "P1", "name": "Dr. Smith", "specialty": "Cardiology", "lat": 38.6270, "lon": -90.1994, "city": "St. Louis"}, # Downtown
        {"id": "P2", "name": "Dr. Jones", "specialty": "Cardiology", "lat": 38.6275, "lon": -90.2000, "city": "St. Louis"}, # Downtown
        {"id": "P3", "name": "Dr. Ray", "specialty": "Pediatrics", "lat": 38.6500, "lon": -90.3500, "city": "Clayton"},   # Suburb
    ]
    
    members = [
        {"id": "M1", "lat": 38.6272, "lon": -90.1990, "needs": ["Cardiology"]}, # Near Downtown
        {"id": "M2", "lat": 38.7900, "lon": -90.3300, "needs": ["Cardiology"]}, # Florissant (Far North)
        {"id": "M3", "lat": 38.7950, "lon": -90.3350, "needs": ["Cardiology"]}, # Florissant (Far North)
        {"id": "M4", "lat": 38.7920, "lon": -90.3320, "needs": ["Cardiology"]}, # Florissant (Far North)
    ]
    return pd.DataFrame(providers), pd.DataFrame(members)

df_providers, df_members = load_mock_database()

def analyze_specialty_gaps(specialty: str, max_distance_miles: float = 15.0):
    """
    Analyzes network adequacy for a specific specialty.
    Returns regions where members have 0 access to that specialty within max_distance_miles.
    """

    print(f"\nDEBUG: Running Geospatial Analysis for '{specialty}' within {max_distance_miles} miles...")
    
    relevant_providers = df_providers[df_providers['specialty'].str.contains(specialty, case=False, na=False)]
    relevant_members = df_members[df_members['needs'].apply(lambda x: specialty in x)]
    
    if relevant_providers.empty:
        return f"CRITICAL: No providers found for {specialty} anywhere in the network."

    gaps = []
    
    for _, member in relevant_members.iterrows():
        member_loc = (member['lat'], member['lon'])
        has_access = False
        
        for _, provider in relevant_providers.iterrows():
            provider_loc = (provider['lat'], provider['lon'])
            distance = geodesic(member_loc, provider_loc).miles
            
            if distance <= max_distance_miles:
                has_access = True
                break
        
        if not has_access:
            gaps.append({
                "member_id": member['id'],
                "location": f"{member['lat']}, {member['lon']}",
                "issue": f"No {specialty} within {max_distance_miles} miles"
            })
            
    if not gaps:
        return f"Network Adequate: All members have access to {specialty} within {max_distance_miles} miles."

    return json.dumps({
        "status": "GAP_DETECTED",
        "specialty": specialty,
        "affected_member_count": len(gaps),
        "total_demand": len(relevant_members),
        "gap_details": gaps
    }, indent = 2)

available_functions = {
    'analyze_specialty_gaps': analyze_specialty_gaps
}

class NetworkGapAgent:
    def __init__(self):
        self.model = "llama3.1"
        self.system_prompt = """
        You are a Network Adequacy Analyst for a healthcare payer.
        Your goal is to protect member health by finding "Network Gaps"—areas where members cannot find a doctor nearby.

        TOOLS:
        - `analyze_specialty_gaps(specialty, max_distance_miles)`: Calculates coverage. Standard acceptable distance is 15 miles.

        INSTRUCTIONS:
        1. Receive the user's concern (e.g., "Check Cardiology coverage").
        2. Call the tool to get the raw data.
        3. INTERPRET the data:
        - If `affected_member_count` > 0, declare a "Network Gap."
        - Suggest a recruitment strategy (e.g., "We need to recruit Cardiologists in the Northern region").
        4. Output a professional summary.
        """

    def run(self, user_query):
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': user_query}
        ]

        print(f"User: {user_query}")

        for _ in range(5):
            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=[analyze_specialty_gaps]
            )
            
            msg = response['message']
            messages.append(msg)

            if msg.get('tool_calls'):
                print(f"--> Agent is analyzing map data...")
                for tool in msg['tool_calls']:
                    fn_name = tool['function']['name']
                    args = tool['function']['arguments']

                    if fn_name in available_functions:
                        result = available_functions[fn_name](**args)
                        messages.append({'role': 'tool', 'content': str(result)})
            else:
                print(f"\nAgent Final Report:\n{msg['content']}")
                return

if __name__ == "__main__":
    agent = NetworkGapAgent()
    agent.run("Analyze the network for Cardiology gaps. Are our members covered?")