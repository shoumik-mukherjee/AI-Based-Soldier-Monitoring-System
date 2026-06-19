import requests
import pickle
import time

# Load trained model
model = pickle.load(open("model_large.pkl", "rb"))

# ThingSpeak details
CHANNEL_ID = "3358625"
READ_API = "OQXIONJMGF8PIUUY"

while True:
    try:
        url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={READ_API}&results=1"
        response = requests.get(url)
        data = response.json()

        feeds = data.get('feeds', [])

        if not feeds:
            print("No data available yet...")
        else:
            feed = feeds[0]

            hr = float(feed['field1'])
            spo2 = float(feed['field2'])
            temp = float(feed['field3'])
            acc = float(feed['field4'])

            prediction = model.predict([[hr, spo2, temp, acc]])

            print("------ LIVE DATA ------")
            print(f"HR: {hr}, Temp: {temp}, Acc: {acc}, SpO2: {spo2}")
            print("Prediction:", prediction[0])

    except Exception as e:
        print("Error:", e)

    time.sleep(10)