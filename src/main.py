import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import val_client
import requests
import time
import tkinter as tk
from tkinter import ttk
import webbrowser
import threading
from PIL import Image, ImageTk

root = tk.Tk()
root.title('KalPick')

frame = ttk.Frame(root, padding='10')
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

agent_var = tk.StringVar()
agent_label = ttk.Label(frame, text='Select Agent:')
agent_label.grid(row=0, column=0, sticky=tk.W, pady=5)
agent_combobox = ttk.Combobox(frame, textvariable=agent_var)
agent_combobox['values'] = ('Jett', 'Raze', 'Breach', 'Omen', 'Brimstone', 'Phoenix', 'Sage', 'Sova', 'Viper', 'Cypher', 'Reyna', 'Killjoy', 'Skye', 'Yoru', 'Astra', 'KAY/O', 'Chamber', 'Neon', 'Fade', 'Harbor', 'Gekko', 'Deadlock')
agent_combobox.grid(row=0, column=1, sticky=tk.W, pady=5)
agent_combobox.set('Jett')

pick_button = ttk.Button(frame, text='Agent Picking')
pick_button.grid(row=1, column=0, columnspan=2, pady=10)

github_button = ttk.Button(frame, text='Open GitHub', command=lambda: webbrowser.open('https://github.com/MonkeySp1n/kalpick'))
github_button.grid(row=2, column=0, columnspan=2, pady=5)

waiting_label = ttk.Label(frame, text='')
waiting_label.grid(row=3, column=0, columnspan=2, pady=5)

is_running = False
stop_event = threading.Event()

def pick_button_aa():
    global is_running
    if not is_running:
        is_running = True
        stop_event.clear()
        pick_button.config(text='Stop')
        threading.Thread(target=agent_picking, daemon=True).start()
    else:
        is_running = False
        stop_event.set()
        pick_button.config(text='Agent Picking')
        waiting_label.config(text='')

pick_button.config(command=pick_button_aa)

def agent_picking():
    agent_name = agent_var.get()
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

        while not stop_event.is_set():
            try:
                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    pregame_info = response.json()

                    if 'MatchID' in pregame_info:
                        match_id = pregame_info['MatchID']

                        agent_response = requests.get('https://valorant-api.com/v1/agents')
                        agent_id = next((agent['uuid'] for agent in agent_response.json()['data'] 
                                        if agent['displayName'].lower() == agent_name.lower()), None)

                        if agent_id:
                            lock_url = f'https://glz-{data["region"]}-1.{data["shard"]}.a.pvp.net/pregame/v1/matches/{match_id}/lock/{agent_id}'
                            lock_response = requests.post(lock_url, headers=headers)

                            if lock_response.status_code == 200:
                                waiting_label.config(text=f'Locked {agent_name}')
                            else:
                                waiting_label.config(text=f'Failed to lock {agent_name}')
                        else:
                            waiting_label.config(text='Agent not found')
                        break

            except Exception as e:
                waiting_label.config(text=f'Error: {str(e)}')

            for i in range(4):
                if stop_event.is_set():
                    break
                waiting_label.config(text='Wait' + '.' * i)
                root.update()
                time.sleep(0.5)

    else:
        error_message = f'{client_info["message"]}\nIf you see this message while Valorant is running, try running Valorant again.'
        waiting_label.config(text=error_message)

    global is_running
    is_running = False
    pick_button.config(text='Agent Picking')

if __name__ == '__main__':
    root.mainloop()
