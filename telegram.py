
#SI SE ROMPE, TUTORIAL: https://www.youtube.com/watch?v=ps1yeWwd6iA
from config_futures import CHAT_ID, TELE_BOT

def send_telegram(message):
    import requests
    chatId = CHAT_ID
    teleBot = TELE_BOT
    url = 'https://api.telegram.org/'+teleBot+'/sendMessage?chat_id='+chatId+'&text="{}"'.format(message)
    requests.get(url)
    return

