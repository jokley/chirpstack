from datetime import datetime, timedelta,timezone
import pytz


timeNow = datetime.now().astimezone(pytz.timezone("Europe/Berlin")).strftime("%H:%M")

if timeNow >= '20:56' and timeNow <= '20:59':
    print (timeNow )
else:
    print('huhu')