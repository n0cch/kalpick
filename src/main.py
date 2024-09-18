import sys, os, val_client, requests, time, tkinter as tk, threading
from tkinter import ttk
import webbrowser
from PIL import Image, ImageTk
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = 'kalpick_config.json'

def get_agents():
    try:
        r = requests.get('https://valorant-api.com/v1/agents')
        return [a['displayName'] for a in r.json()['data'] if a['isPlayableCharacter']]
    except Exception as e:
        return f"Error fetching agents: {str(e)}"

def get_maps():
    try:
        r = requests.get('https://valorant-api.com/v1/maps')
        maps = {}
        for m in r.json()['data']:
            map_id = m['mapUrl'].split('/')[-1]
            if 'Range' in map_id:
                maps['Range'] = 'The Range'
            else:
                maps[map_id] = m['displayName']
        return maps
    except Exception as e:
        return f"Error fetching maps: {str(e)}"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"default_agent": "", "delay": "0", "map_based": False, "map_agents": {}}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

root = tk.Tk()
root.title('KalPick')

try:
    root.iconbitmap(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kalpick.ico'))
except tk.TclError:
    pass

frame = ttk.Frame(root, padding='10')
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

config = load_config()

agent_var = tk.StringVar(value=config["default_agent"])
ttk.Label(frame, text='Default Agent:').grid(row=0, column=0, sticky=tk.W, pady=5)
agent_cb = ttk.Combobox(frame, textvariable=agent_var)
agents = get_agents()
if isinstance(agents, str):
    ttk.Label(frame, text=agents).grid(row=6, column=0, columnspan=2, pady=5)
    agent_cb['values'] = []
else:
    agent_cb['values'] = agents
agent_cb.grid(row=0, column=1, sticky=tk.W, pady=5)
agent_cb.set(config["default_agent"] if config["default_agent"] in agents else (agent_cb['values'][0] if agent_cb['values'] else ''))

delay_var = tk.StringVar(value=config["delay"])
ttk.Label(frame, text='Delay:').grid(row=1, column=0, sticky=tk.W, pady=5)
ttk.Entry(frame, textvariable=delay_var).grid(row=1, column=1, sticky=tk.W, pady=5)

map_based_var = tk.BooleanVar(value=config["map_based"])
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
        map_cb = ttk.Combobox(map_frame, values=['Default Agent', 'Manual Pick'] + list(agent_cb['values']))
        map_cb.grid(row=i, column=1, sticky=tk.W, pady=2)
        if map_id == 'Range' or map_name == 'The Range' or map_name == 'Basic Training':
            default_value = 'Manual Pick'
        else:
            default_value = config["map_agents"].get(map_id, 'Default Agent')
        map_cb.set(default_value)
        map_agents[map_id] = map_cb

run_var = tk.BooleanVar(value=False)
run_btn = ttk.Checkbutton(frame, text='Run Agent Picking', variable=run_var, command=lambda: toggle_run())
run_btn.grid(row=4, column=0, columnspan=2, pady=10)

ttk.Button(frame, text='Open GitHub', command=lambda: webbrowser.open('https://github.com/stark7k/valorant-instalock')).grid(row=5, column=0, columnspan=2, pady=5)

status_label = ttk.Label(frame, text='')
status_label.grid(row=6, column=0, columnspan=2, pady=5)

stop_event = threading.Event()
last_locked_match_id = None

def toggle_map_selection():
    if map_based_var.get():
        map_frame.grid()
    else:
        map_frame.grid_remove()
    save_current_config()

def toggle_run():
    if run_var.get():
        stop_event.clear()
        threading.Thread(target=watch_for_match, daemon=True).start()
    else:
        stop_event.set()

def update_status(text):
    status_label.config(text=text)
    root.update()

def save_current_config():
    config = {
        "default_agent": agent_var.get(),
        "delay": delay_var.get(),
        "map_based": map_based_var.get(),
        "map_agents": {map_id: cb.get() for map_id, cb in map_agents.items()}
    }
    save_config(config)

def watch_for_match():
    global last_locked_match_id
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
                        if pregame_info['MatchID'] != last_locked_match_id:
                            agent_picking(data, headers, pregame_info['MatchID'])
                            last_locked_match_id = pregame_info['MatchID']
                        else:
                            update_status('Agent already locked for this match')
                    else:
                        update_status('working' + '.' * (int(time.time()) % 4))
                        last_locked_match_id = None
                else:
                    update_status('working' + '.' * (int(time.time()) % 4))
                    last_locked_match_id = None
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
        if 'Range' in map_id:
            map_id = 'Range'
        
        if map_based_var.get() and map_id in map_agents:
            selected_agent = map_agents[map_id].get()
            if selected_agent == 'Manual Pick':
                update_status(f'Manual Pick selected for {maps.get(map_id, "Unknown")}. Waiting for user to pick.')
                return
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

def on_closing():
    save_current_config()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

if __name__ == '__main__':
    if config["map_based"]:
        map_frame.grid()
    root.mainloop()
