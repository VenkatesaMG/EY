import ollama
import pandas as pd
from geopy.distance import geodesic
from typing import List, Dict
import re
import json

def load_mock_database():
    providers = [
        {"id": "P1", "name": "Dr. Smith", "specialty": "Cardiology", "lat": 38.6270, "lon": -90.1994, "city": "St. Louis"},
        {"id": "P2", "name": "Dr. Jones", "specialty": "Cardiology", "lat": 38.6275, "lon": -90.2000, "city": "St. Louis"},
        {"id": "P3", "name": "Dr. Ray", "specialty": "Pediatrics", "lat": 38.6500, "lon": -90.3500, "city": "Clayton"},
    ]

    members = [
        {"id": "M1", "lat": 38.6272, "lon": -90.1990, "needs": ["Cardiology"]}, # Near Downtown
        {"id": "M2", "lat": 38.7900, "lon": -90.3300, "needs": ["Cardiology"]}, # Florissant (Far North)
        {"id": "M3", "lat": 38.7950, "lon": -90.3350, "needs": ["Cardiology"]}, # Florissant (Far North)
        {"id": "M4", "lat": 38.7920, "lon": -90.3320, "needs": ["Cardiology"]}, # Florissant (Far North)
    ]

    return pd.DataFrame(providers), pd.DataFrame(members)

df_providers, df_members = load_mock_database()

def parse_action(text):
    match = re.search(r"Action:\s*(\w+)\[(.*)\]", text, re.DOTALL)
    if not match:
        return None, None

    fn_name = match.group(1)
    args = json.loads(match.group(2))
    return fn_name, args

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

REACT_SYSTEM_PROMPT = """
        You are a Network Adequacy Analyst for a healthcare payer.

        You MUST strictly follow this format:

        Thought: Your reasoning
        Action: analyze_specialty_gaps[JSON arguments]
        Observation: Tool result
        Thought: Interpretation
        Final Answer: Professional summary with recommendation

        Rules:
        - Always analyze before concluding
        - Only use available actions
        - Do not hallucinate data
"""

class ReActNetworkGapAgent:
    def __init__(self):
        self.model = "llama3.1"
        self.messages = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT}
        ]

    def run(self, user_query):
        self.messages.append({"role": "user", "content": user_query})

        while True:
            response = ollama.chat(
                model=self.model,
                messages=self.messages
            )

            output = response["message"]["content"]
            print("\nLLM OUTPUT:\n", output)

            # Stop condition
            if "Final Answer:" in output:
                break

            # Parse Action
            fn_name, args = parse_action(output)

            if fn_name and fn_name in available_functions:
                result = available_functions[fn_name](**args)

                # Feed observation back to LLM
                self.messages.append({
                    "role": "user",
                    "content": f"Observation: {result}"
                })
            else:
                raise ValueError("Invalid or missing action")

if __name__ == "__main__":
    agent = ReActNetworkGapAgent()
    agent.run("Analyze the network for Cardiology gaps. Are our members covered?")