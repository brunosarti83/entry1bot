
#SI SE ROMPE, TUTORIAL: https://www.youtube.com/watch?v=ps1yeWwd6iA
from config_futures import CHAT_ID

def send_telegram(message):
    import requests
    chatId = CHAT_ID
    url = 'https://api.telegram.org/bot1700277460:AAG4YdeSJZ0iZEYmambFKZN5pZTEVMb-YQ8/sendMessage?chat_id='+chatId+'&text="{}"'.format(message)
    requests.get(url)
    return

