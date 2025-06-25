#PART 1 : url_scraper.py --> scrapes for the player urls and stores into player_urls.csv

import time
import pandas as pd
import requests
import json
import os


def search_player_api(player_name, sport="Football"):
    """
    API-based player search using Rivals API endpoint
    """
    print(f"🚀 API Search for: {player_name} (Sport: {sport})")

    # API endpoint
    api_url = "https://n.rivals.com/api/v2/people"

    # Headers to mimic the curl request
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }

    # Request payload - try different search approaches
    payloads_to_try = [
        # Original payload
        {
            "search": {
                "member": "Prospect",
                "sport": sport
            }
        },
        # Try with name parameter
        {
            "search": {
                "member": "Prospect",
                "sport": sport,
                "name": player_name
            }
        },
        # Try with query parameter
        {
            "search": {
                "member": "Prospect",
                "sport": sport,
                "query": player_name
            }
        },
        # Try with q parameter
        {
            "search": {
                "member": "Prospect",
                "sport": sport,
                "q": player_name
            }
        }
    ]

    try:
        # Try different payload approaches
        for i, payload in enumerate(payloads_to_try):
            print(f"\n🔄 Attempt {i+1}: Trying payload variation")
            print(f"📡 Making API request to: {api_url}")
            print(f"📋 Payload: {json.dumps(payload, indent=2)}")

            response = requests.post(api_url, headers=headers, json=payload, timeout=30)

            print(f"📊 API Response Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ API call successful!")

                    # Search through the results for matching player
                    player_matches = find_matching_players(data, player_name)

                    if player_matches:
                        print(f"🎯 Found {len(player_matches)} potential matches with payload {i+1}")
                        # Return the best match
                        best_match = player_matches[0]
                        player_url = build_player_profile_url(best_match)
                        return player_url, best_match
                    else:
                        print(f"❌ No matches found with payload {i+1}")
                        if i == 0:  # Show structure only for first attempt
                            print(f"📄 Raw response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")

                            # Pretty print the first few items to understand structure
                            if isinstance(data, dict):
                                for key, value in data.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        print(f"📋 {key}: Found {len(value)} items")
                                        print(f"📋 Sample item: {json.dumps(value[0], indent=2)}")
                                    else:
                                        print(f"📋 {key}: {value}")
                        continue  # Try next payload

                except json.JSONDecodeError as e:
                    print(f"⚠️ Failed to parse JSON response: {e}")
                    continue
            else:
                print(f"⚠️ API request failed with status {response.status_code}")
                print(f"📄 Response content: {response.text[:200]}...")
                continue

        # If we get here, all payloads failed
        print("❌ All payload variations failed to find matches")
        return None, None

    except requests.exceptions.Timeout:
        print("⚠️ API request timed out")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ API request error: {e}")
        return None, None
    except Exception as e:
        print(f"⚠️ Unexpected API error: {e}")
        return None, None


def find_matching_players(api_response, target_name):
    """
    Find players that match the target name from API results
    """
    target_name_lower = target_name.lower().strip()
    target_parts = target_name_lower.split()

    matches = []

    # Handle different response structures
    players_data = []

    if isinstance(api_response, dict):
        # Try common keys where player data might be stored
        possible_keys = ['data', 'results', 'players', 'prospects', 'items', 'content']
        for key in possible_keys:
            if key in api_response and isinstance(api_response[key], list):
                players_data = api_response[key]
                print(f"📋 Using data from key: {key}")
                break

        # If no list found in common keys, try all keys
        if not players_data:
            for key, value in api_response.items():
                if isinstance(value, list) and len(value) > 0:
                    players_data = value
                    print(f"📋 Using data from key: {key}")
                    break
    elif isinstance(api_response, list):
        players_data = api_response
        print(f"📋 Using direct list response")

    print(f"📊 Searching through {len(players_data)} players...")

    for i, player in enumerate(players_data):
        if i < 5:  # Show first 5 players for debugging
            print(f"📋 Player {i+1}: {json.dumps(player, indent=2)}")

        # Extract player information
        player_name = ""
        if isinstance(player, dict):
            # Try different possible name fields
            name_fields = ['name', 'full_name', 'display_name', 'player_name', 'title', 'firstName', 'lastName', 'displayName']
            for field in name_fields:
                if field in player and player[field]:
                    if field in ['firstName', 'lastName']:
                        # Combine first and last name
                        first_name = player.get('firstName', '')
                        last_name = player.get('lastName', '')
                        player_name = f"{first_name} {last_name}".strip()
                    else:
                        player_name = str(player[field]).strip()
                    break
        elif isinstance(player, str):
            player_name = player

        if not player_name:
            continue

        player_name_lower = player_name.lower()

        # Calculate match score
        score = 0

        # Exact match gets highest score
        if player_name_lower == target_name_lower:
            score = 100
        # Check if all target name parts are in player name
        elif all(part in player_name_lower for part in target_parts):
            score = 80
        # Check if most target name parts are in player name
        elif sum(1 for part in target_parts if part in player_name_lower) >= len(target_parts) // 2:
            score = 60
        # Partial match
        elif any(part in player_name_lower for part in target_parts):
            score = 40

        if score > 0:
            matches.append({
                'player_data': player,
                'player_name': player_name,
                'score': score
            })

    # Sort by score (highest first)
    matches.sort(key=lambda x: x['score'], reverse=True)

    # Print matches for debugging
    if matches:
        print(f"🎯 Player matches found:")
        for i, match in enumerate(matches[:5]):  # Show top 5 matches
            print(f"  {i+1}. {match['player_name']} (Score: {match['score']})")

    return matches


def build_player_profile_url(player_match):
    """
    Build the full profile URL from player data
    """
    player_data = player_match['player_data']

    print(f"🔗 Building URL from player data: {json.dumps(player_data, indent=2)}")

    # Try to find URL components
    possible_url_fields = ['url', 'profile_url', 'link', 'href', 'path', 'slug', 'id', 'profileUrl', 'canonicalUrl']

    profile_url = None

    for field in possible_url_fields:
        if field in player_data and player_data[field]:
            url_part = str(player_data[field])
            print(f"🔍 Checking field '{field}': {url_part}")

            if url_part.startswith('http'):
                profile_url = url_part
                print(f"✅ Found full URL: {profile_url}")
                break
            elif url_part.startswith('/'):
                profile_url = f"https://n.rivals.com{url_part}"
                print(f"✅ Built URL from path: {profile_url}")
                break

    # If no direct URL found, try to construct one
    if not profile_url:
        # Try different ID fields
        id_fields = ['id', 'playerId', 'prospectId', 'memberId']
        for id_field in id_fields:
            if id_field in player_data and player_data[id_field]:
                player_id = player_data[id_field]
                profile_url = f"https://n.rivals.com/content/prospects/{player_id}"
                print(f"✅ Constructed URL from {id_field}: {profile_url}")
                break

    if not profile_url:
        print("❌ Could not build profile URL from player data")

    return profile_url


def save_url_to_csv(player_name, player_url, player_data=None):
    """Save URL to CSV file"""
    try:
        safe_url = player_url if player_url else "NOT_FOUND"

        url_data = {
            'player_name': player_name,
            'profile_url': safe_url,
            'method_used': 'api',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'found' if player_url else 'not_found'
        }

        # Add extra data from API if available
        if player_data:
            url_data['api_player_name'] = player_data.get('player_name', '')
            url_data['match_score'] = player_data.get('score', '')

        df = pd.DataFrame([url_data])
        output_file = 'player_urls.csv'

        if os.path.exists(output_file):
            try:
                existing_df = pd.read_csv(output_file)
                combined_df = pd.concat([existing_df, df], ignore_index=True, sort=False)
                combined_df = combined_df.drop_duplicates(subset=['player_name'], keep='last')
                combined_df.to_csv(output_file, index=False)
                print(f"✅ URL added to existing {output_file}")
            except Exception as e:
                print(f"⚠️ Error appending to CSV: {e}")
                df.to_csv(output_file, index=False)
                print(f"✅ Created new {output_file}")
        else:
            df.to_csv(output_file, index=False)
            print(f"✅ Created new {output_file}")

    except Exception as e:
        print(f"⚠️ CSV save error (non-critical): {e}")
        print(f"📝 Would have saved: {player_name} -> {player_url or 'NOT_FOUND'}")


def main():
    """API-only main function with detailed debugging"""
    try:
        print("🚀 Rivals Player API Search (API Only)")
        print("=" * 50)

        player_name = input("Enter player name: ").strip()

        if not player_name:
            print("❌ No player name entered")
            return

        # Optional: Ask for sport (defaults to Football)
        sport_input = input("Enter sport (Football/Basketball) [default: Football]: ").strip()
        sport = sport_input if sport_input else "Football"

        start_time = time.time()

        # Use only API method
        player_url, player_data = search_player_api(player_name, sport)

        end_time = time.time()
        print(f"⏱️ API search time: {end_time - start_time:.2f} seconds")

        if player_url:
            print(f"✅ SUCCESS! Found URL: {player_url}")
            if player_data:
                print(f"📊 Match Score: {player_data.get('score', 'N/A')}")
                print(f"🏷️ API Player Name: {player_data.get('player_name', 'N/A')}")
            save_url_to_csv(player_name, player_url, player_data)
        else:
            print(f"❌ Could not find URL for: {player_name}")
            save_url_to_csv(player_name, None, None)

        print("🎯 API search completed!")

    except KeyboardInterrupt:
        print("\n⚠️ Script interrupted by user")
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
