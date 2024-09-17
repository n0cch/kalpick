import sys, os, val_client, requests, time, tkinter as tk, threading
from tkinter import ttk
import webbrowser
from PIL import Image, ImageTk

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_agents():
    try:
        r = requests.get('https://valorant-api.com/v1/agents')
        return [a['displayName'] for a in r.json()['data'] if a['isPlayableCharacter']]
    except Exception as e:
        return f"Error fetching agents: {str(e)}"

def get_maps():
    try:
        r = requests.get('https://valorant-api.com/v1/maps')
        return {m['mapUrl'].split('/')[-1]: m['displayName'] for m in r.json()['data']}
    except Exception as e:
        return f"Error fetching maps: {str(e)}"

root = tk.Tk()
root.title('KalPick')

try:
    root.iconbitmap(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kalpick.ico'))
except tk.TclError:
    pass

frame = ttk.Frame(root, padding='10')
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

agent_var = tk.StringVar()
ttk.Label(frame, text='Default Agent:').grid(row=0, column=0, sticky=tk.W, pady=5)
agent_cb = ttk.Combobox(frame, textvariable=agent_var)
agents = get_agents()
if isinstance(agents, str):
    ttk.Label(frame, text=agents).grid(row=6, column=0, columnspan=2, pady=5)
    agent_cb['values'] = []
else:
    agent_cb['values'] = agents
agent_cb.grid(row=0, column=1, sticky=tk.W, pady=5)
agent_cb.set(agent_cb['values'][0] if agent_cb['values'] else '')

delay_var = tk.StringVar(value='0')
ttk.Label(frame, text='Delay:').grid(row=1, column=0, sticky=tk.W, pady=5)
ttk.Entry(frame, textvariable=delay_var).grid(row=1, column=1, sticky=tk.W, pady=5)

map_based_var = tk.BooleanVar(value=False)
ttk.Checkbutton(frame, text='Map-based Agent Picking', variable=map_based_var, command=lambda: toggle_map_selection()).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

map_frame = ttk.Frame(frame)
map_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
map_frame.grid_remove()

map_agents = {}
maps = get_maps()
if isinstance(maps, str):
    ttk.Label(frame, text=maps).grid(row=6, column=0, columnspan=2, pady=5)
    map_frame.grid_remove()
else:
    for i, (map_id, map_name) in enumerate(maps.items()):
        ttk.Label(map_frame, text=f'{map_name}:').grid(row=i, column=0, sticky=tk.W, pady=2)
        map_cb = ttk.Combobox(map_frame, values=['Default Agent'] + list(agent_cb['values']))
        map_cb.grid(row=i, column=1, sticky=tk.W, pady=2)
        map_cb.set('Default Agent')
        map_agents[map_id] = map_cb

run_var = tk.BooleanVar(value=False)
run_btn = ttk.Checkbutton(frame, text='Run Agent Picking', variable=run_var, command=lambda: toggle_run())
run_btn.grid(row=4, column=0, columnspan=2, pady=10)

ttk.Button(frame, text='Open GitHub', command=lambda: webbrowser.open('https://github.com/MonkeySp1n/kalpick')).grid(row=5, column=0, columnspan=2, pady=5)

status_label = ttk.Label(frame, text='')
status_label.grid(row=6, column=0, columnspan=2, pady=5)

stop_event = threading.Event()

def toggle_map_selection():
    if map_based_var.get():
        map_frame.grid()
    else:
        map_frame.grid_remove()

def toggle_run():
    if run_var.get():
        stop_event.clear()
        threading.Thread(target=watch_for_match, daemon=True).start()
    else:
        stop_event.set()

def update_status(text):
    status_label.config(text=text)
    root.update()

def watch_for_match():
    while run_var.get() and not stop_event.is_set():
        try:
            client_info = val_client.info()
            if client_info['status'] == 'success':
                data = client_info['data']
                headers = {
                    'X-Riot-ClientPlatform': data['client_platform'],
                    'X-Riot-ClientVersion': data['client_version'],
                    'X-Riot-Entitlements-JWT': data['entitlements_token'],
                    'Authorization': f'Bearer {data["access_token"]}'
                }
                url = f'https://glz-{data["region"]}-1.{data["shard"]}.a.pvp.net/pregame/v1/players/{data["puuid"]}'
                
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    pregame_info = response.json()
                    if 'MatchID' in pregame_info:
                        agent_picking(data, headers, pregame_info['MatchID'])
                        time.sleep(5)
                        update_status('working' + '.' * (int(time.time()) % 4))
                else:
                    update_status('working' + '.' * (int(time.time()) % 4))
            else:
                update_status(f"Error: {client_info.get('message', 'Unknown error')}")
        except Exception as e:
            update_status(f'Error: {str(e)}')
        time.sleep(1)

def agent_picking(data, headers, match_id):
    delay = int(delay_var.get())
    
    try:
        match_url = f'https://glz-{data["region"]}-1.{data["shard"]}.a.pvp.net/pregame/v1/matches/{match_id}'
        match_response = requests.get(match_url, headers=headers)
        match_data = match_response.json()
        map_id = match_data['MapID'].split('/')[-1]
        
        if map_based_var.get() and map_id in map_agents:
            selected_agent = map_agents[map_id].get()
            agent_name = agent_var.get() if selected_agent == 'Default Agent' else selected_agent
        else:
            agent_name = agent_var.get()
        
        update_status(f'Map: {maps.get(map_id, "Unknown")}, Agent: {agent_name}, Delay: {delay} seconds')
        time.sleep(delay)

        agent_response = requests.get('https://valorant-api.com/v1/agents')
        agent_id = next((agent['uuid'] for agent in agent_response.json()['data'] 
                        if agent['displayName'].lower() == agent_name.lower()), None)

        if agent_id:
            lock_url = f'https://glz-{data["region"]}-1.{data["shard"]}.a.pvp.net/pregame/v1/matches/{match_id}/lock/{agent_id}'
            lock_response = requests.post(lock_url, headers=headers)

            if lock_response.status_code == 200:
                update_status(f'Locked {agent_name} on {maps.get(map_id, "Unknown")}')
            else:
                update_status(f'Failed to lock {agent_name}')
        else:
            update_status('Agent not found')
    except Exception as e:
        update_status(f'Error during agent picking: {str(e)}')

if __name__ == '__main__':
    root.mainloop()
