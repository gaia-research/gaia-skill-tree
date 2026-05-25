import json
import os
from datetime import datetime, timedelta

def generate_timeline():
    with open('registry/gaia.json', 'r') as f:
        gaia = json.load(f)

    skills = gaia.get('skills', [])
    
    # Start and end dates for May 2026
    start_date = datetime(2026, 5, 1)
    end_date = datetime(2026, 5, 25)
    
    days = []
    curr = start_date
    while curr <= end_date:
        days.append(curr.strftime('%Y-%m-%d'))
        curr += timedelta(days=1)

    # We want to track the state of every skill on every day.
    # To do this accurately, we'd need to replay the whole history.
    # Simplification: Find the latest state on or before each day for each skill.
    
    ranks = ["0★", "1★", "2★", "3★", "4★", "5★", "6★"]
    dataset = {rank: [0] * len(days) for rank in ranks}

    for i, day_str in enumerate(days):
        day_limit = datetime.strptime(day_str + "T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
        
        for skill in skills:
            # Determine rank of skill on this day
            current_rank = "0★" # Default floor
            
            # Replay timeline
            timeline = skill.get('timeline', [])
            # Sort timeline by timestamp
            sorted_timeline = sorted(timeline, key=lambda x: x.get('timestamp', ''))
            
            for event in sorted_timeline:
                ts = datetime.strptime(event.get('timestamp', '2026-01-01T00:00:00Z'), "%Y-%m-%dT%H:%M:%SZ")
                if ts > day_limit:
                    break
                
                action = event.get('action', '')
                details = event.get('details', '')
                
                # Try to infer rank from details or action
                # Most rank_up/demote events say "Calibrated to X★" or similar
                if '★' in details:
                    # Extract rank from details
                    import re
                    match = re.search(r'(\d★)', details)
                    if match:
                        current_rank = match.group(1)
                elif action == 'add':
                    # Initial adds are often 0★ or 1★
                    current_rank = "1★" if skill.get('type') == 'basic' else "0★"
            
            if current_rank in dataset:
                dataset[current_rank][i] += 1

    output = {
        "labels": days,
        "datasets": [
            {
                "label": rank,
                "data": dataset[rank],
                "color": gaia['meta']['levelColors'][rank]['hex']
            } for rank in ranks
        ]
    }

    os.makedirs('docs/meta/reports', exist_ok=True)
    with open('docs/meta/reports/may-2026-timeline.json', 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    generate_timeline()
