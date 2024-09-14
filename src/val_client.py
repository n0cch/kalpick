import requests
import base64
import os
import re
import warnings
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def info():
    try:
        path = os.path.join(os.getenv('LOCALAPPDATA'), R'Riot Games\Riot Client\Config\lockfile')
        if not os.path.isfile(path):
            return {'status': 'failed', 'message': 'Please make sure Valorant is running and logged in.'}

        with open(path, 'r') as lockfile:
            data = lockfile.read().split(':')
            port, password = data[2], data[3]

        local_headers = {
            'Authorization': 'Basic ' + base64.b64encode(f'riot:{password}'.encode()).decode()
        }
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(f'https://127.0.0.1:{port}/entitlements/v1/token',
                                    headers=local_headers, verify=False)
        
        entitlements = response.json()

        access_token = entitlements['accessToken']
        entitlements_token = entitlements['token']
        user_id = entitlements['subject']

        shooter_log_path = os.path.join(os.getenv('LOCALAPPDATA'), R'VALORANT\Saved\Logs\ShooterGame.log')
        region = shard = client_version = 'Unknown'
        if os.path.isfile(shooter_log_path):
            with open(shooter_log_path, 'r', encoding='utf-8') as log_file:
                log_content = log_file.read()
                region_shard_match = re.search(r'https://glz-(.+?)-1.(.+?).a.pvp.net', log_content)
                if region_shard_match:
                    region, shard = region_shard_match.group(1), region_shard_match.group(2)
                
                version_match = re.search(r'CI server version: (.+)', log_content)
                if version_match:
                    client_version = version_match.group(1)

        client_platform = 'ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9'

        return {
            'status': 'success',
            'data': {
                'access_token': access_token,
                'entitlements_token': entitlements_token,
                'puuid': user_id,
                'region': region,
                'shard': shard,
                'client_platform': client_platform,
                'client_version': client_version
            }
        }
    except Exception as e:
        return {'status': 'failed', 'message': 'Please make sure Valorant is running and logged in.'}