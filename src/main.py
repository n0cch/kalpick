import val_client as val_client
import requests

client_info = val_client.info()

if client_info['status'] == 'success':
    data = client_info['data']
    access_token = data['access_token']
    entitlements_token = data['entitlements_token']
    puuid = data['puuid']
    region = data['region']
    shard = data['shard']
    client_platform = data['client_platform']
    client_version = data['client_version']

    headers = {
        'X-Riot-ClientPlatform': client_platform,
        'X-Riot-ClientVersion': client_version,
        'X-Riot-Entitlements-JWT': entitlements_token,
        'Authorization': f'Bearer {access_token}'
    }

    url = f'https://glz-{region}-1.{shard}.a.pvp.net/pregame/v1/players/{puuid}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        pregame_info = response.json()

        if 'MatchID' in pregame_info:
            match_id = pregame_info['MatchID']

            agent_name = 'TARGET AGENT'

            agent_response = requests.get('https://valorant-api.com/v1/agents')
            agent_id = None
            if agent_response.status_code == 200:
                agents = agent_response.json()['data']
                for agent in agents:
                    if agent['displayName'].lower() == agent_name.lower():
                        agent_id = agent['uuid']
                        break

            if agent_id:
                lock_url = f'https://glz-{region}-1.{shard}.a.pvp.net/pregame/v1/matches/{match_id}/lock/{agent_id}'
                lock_response = requests.post(lock_url, headers=headers)

                if lock_response.status_code == 200:
                    print('Lock successful')
                else:
                    print('Lock failed')
            else:
                print('Agent not found')
        else:
            print('Not in pregame')
    else:
        print('Failed to get info')
else:
    print(client_info['message'])