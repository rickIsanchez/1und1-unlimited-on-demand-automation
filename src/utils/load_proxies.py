import requests, os
from src.config import API_KEY_WEBSHARE, USE_WEBSHARE

def fetch_proxies(api_url, token):
    headers = {
        "Authorization": f"Token {token}"
    }
    
    proxies = []
    try:
        while True:
            try:
                response = requests.get(api_url, headers=headers, timeout=(5,5))
                if response.status_code == 200:break
            except:
                pass
        if response.status_code == 200:
            data = response.json()
            for result in data.get("results", []):
                ip = result["proxy_address"]
                port = result["port"]
                username = result["username"]
                password = result["password"]
                # Hier wird das IP:Port Format erstellt
                proxies.append(f"{ip}:{port}:{username}:{password}")
            return proxies
        else:
            print(f"Fehler beim Abrufen der Proxydaten: {response.status_code}")
    except Exception as e:
        print(f"Fehler beim Abrufen der Proxydaten: {e}")

    return [{}]

def load_proxies_all(proxies):
    proxies_list = []
    for proxy in proxies:
        proxy_data = proxy.strip().split(':')
        if len(proxy_data) >= 2:
            ip = proxy_data[0]
            port = proxy_data[1]
            username = proxy_data[2]
            password = proxy_data[3]
            proxy = {
                'https': f'http://{username}:{password}@{ip}:{port}'
            }
            proxies_list.append(proxy)
    
    return proxies_list

def load_proxies():
    if USE_WEBSHARE == 'true':
        api_url = "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=100"
        proxies = fetch_proxies(api_url, API_KEY_WEBSHARE)
        # Proxydaten in das richtige Format umwandeln
        loaded_proxies = load_proxies_all(proxies)
        return loaded_proxies if loaded_proxies else [{}]
    else:
        # Prüft, ob die Datei existiert
        filename = "proxies.txt"
        # Falls du sicherstellen möchtest, dass der Pfad relativ zum Skript ist:
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Ordner des aktuellen Skripts
        file_path = os.path.join(script_dir, filename)
        proxies_list = []
        try:
            with open(file_path, 'r') as file:
                for line in file:
                    proxy_data = line.strip().split(':')
                    if len(proxy_data) >= 2:
                        ip = proxy_data[0]
                        port = proxy_data[1]
                        username = proxy_data[2]
                        password = proxy_data[3]
                        proxy = {
                            'https': f'http://{username}:{password}@{ip}:{port}'
                        }
                        proxies_list.append(proxy)
        except FileNotFoundError:
            print(f"Die Datei {file_path} wurde nicht gefunden.")
            return [{}]
        except Exception as e:
            print(f"Ein Fehler ist aufgetreten: {e}")
            return [{}]

        return proxies_list if proxies_list else [{}]
    
proxies = load_proxies()

if __name__ == '__main__':
    loaded_proxies = load_proxies()
    print(loaded_proxies)