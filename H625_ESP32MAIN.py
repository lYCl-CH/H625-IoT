from machine import ADC, Pin
from memory_config import check_system,clean_memory,adjust_freq
from umqtt.simple import MQTTClient
import network
import socket
import dht
import time
import _thread
import ujson  # MicroPython 的 JSON 模組
import machine
import ntptime
import urequests
import json
import wifi_connect
# 設置 DHT22 傳感器
dht_sensor = dht.DHT22(machine.Pin(33))
esp32_led = machine.Pin(2, machine.Pin.OUT)
#光敏感測
ao_pin = ADC(Pin(36))  # AO 連接到 GPIO34（ESP32 ADC 腳位）
ao_pin.atten(ADC.ATTN_11DB)  # 設定 ADC 讀取範圍 0~3.3V


adjust_freq(100)




# 連接 WiFi
# wifi = network.WLAN(network.STA_IF)
# wifi.active(True)
# wifi.connect('SSID', 'password')

# while not wifi.isconnected():
#     pass
# 
# print('Wi-Fi 連接成功，IP 地址:', wifi.ifconfig()[0])
# wifi.config(pm=network.WLAN.PM_POWERSAVE)
# 獲取 IP
if wifi_connect.ip()!= None:
    ntptime.host = "time.windows.com"
    ip_address = wifi_connect.ip()
    

    # 創建 Web 伺服器
    addr = socket.getaddrinfo(ip_address, 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print('Web 伺服器運行於 http://%s' % ip_address)
   
API_KEY = '71P6WEEY0ZP7J7V0'
THINGSPEAK_URL = 'http://api.thingspeak.com/update'

SERVER = "broker.emqx.io"
PORT = 1883
CLIENT_ID = 'micropython-client-{ip_address}'
USERNAME = 'dormitory_H625'
PASSWORD = 'H625741'
TOPIC = "ESP32_sensor"

def connect():
    client = MQTTClient(CLIENT_ID, SERVER, PORT, USERNAME, PASSWORD)
    client.connect()
    print('Connected to MQTT Broker "{server}"'.format(server = SERVER))
    return client
# 初始化溫溼度變數
client = connect()

current_temp = 0
current_hum = 0
dht_sensor.measure()
current_temp = dht_sensor.temperature()
current_hum = dht_sensor.humidity()
avg_hum=0
avg_temp=0
temp_list = []
hum_list = []
light=None



def loop_publish(client):   
    msg_count = 0
    cpu_freq,cpu_temp_celsius,all_heap, allocated_heap,flash = check_system()
    while True:
        msg_dict = {
            "cpu_freq": cpu_freq,
            "cpu_temp_celsius": round(cpu_temp_celsius, 2),
            "all_heap": round(all_heap/1000, 1),
            "allocated_heap": round(allocated_heap/1000, 1),
            "flash": round(flash/1000, 1),        
            "temp": round(current_temp, 1),
            "hum": round(current_hum, 1),
            "avg_temp": round(avg_temp, 1),
            "avg_hum": round(avg_hum, 1),
            "light":light,
        }
        msg = json.dumps(msg_dict)
        
        try:
            client.publish(TOPIC, msg)
        except Exception as e:
            print("MQTT 發佈失敗:", e)
            client = connect()
            
#         print("Send '{msg}' to topic '{topic}'".format(msg = msg, topic = TOPIC))
        time.sleep(60)
def send_to_thingspeak():
    while True:
        cpu_freq,cpu_temp_celsius,all_heap, allocated_heap,flash = check_system()
        url = "{}?api_key={}&field1={}&field2={}&field3={}&field4={}&field5={}&field6={}&field7={}".format(THINGSPEAK_URL, API_KEY,cpu_freq,round(cpu_temp_celsius, 2),round(all_heap/1000, 1),round(allocated_heap/1000, 1),round(flash/1000, 1),round(current_temp, 1), round(current_hum, 1))
        try:
            response = urequests.get(url)
            print("資料已送出，回應:", response.text)
            response.close()
        except Exception as e:
            print("送出資料失敗:", e)
#         print(THINGSPEAK_URL, API_KEY,cpu_freq,cpu_temp_celsius,all_heap,allocated_heap,flash,current_temp, current_hum)
        time.sleep(60)

# **讀取 DHT22 並計算 1 小時內的平均值**
def DIY_LIGHT_SENSOR():
    global  light
    io=0
    age=0
    while True:
        for i in range(10):
            light_value = ao_pin.read()  # 讀取 ADC 數值（0~4095）
#             print("光線強度:", light_value)
            age=(age+light_value)
            time.sleep(0.1)
#         print('ts=',age/10)
        if (2950<age/10 and io==1):
           light="light off"
        elif (2950<age/10 ):
            io=1
        elif(2950>age/10 ):
            light="Light on"
            io=0
        age=0
#         print('-------')
        time.sleep(5)
def read_dht22():
    global current_temp, current_hum, temp_list, hum_list, timestamp
    while True:
        try:

            dht_sensor.measure()
            current_temp = dht_sensor.temperature()
            current_hum = dht_sensor.humidity()

            # 每分鐘記錄一次
            temp_list.append(current_temp)
            hum_list.append(current_hum)
            
            
            formatted_time = f"{timestamp[0]:04d}{timestamp[1]:02d}{timestamp[2]:02d} {timestamp[3]:02d}:00"            
            # 限制只存 60 筆數據（1 小時）
            if len(temp_list) > 60:
                temp_list.pop(0)
                hum_list.pop(0)

            print(f'時間: {formatted_time},溫度: {current_temp}°C, 濕度: {current_hum}%')
        
        except OSError:
            print("讀取 DHT22 失敗")
        
        time.sleep(58)  # 每分鐘讀取一次
        esp32_led.value(1)
        time.sleep(1)
        esp32_led.value(0)
        time.sleep(1)

# **每小時存儲平均值**
def store_hourly_avg():
    global temp_list, hum_list,avg_hum,avg_temp
    while True:
        if temp_list and hum_list:
            avg_temp = sum(temp_list) / len(temp_list)
            avg_hum = sum(hum_list) / len(hum_list)
            
            timestamp = time.localtime()
            formatted_time = f"{timestamp[0]:04d}{timestamp[1]:02d}{timestamp[2]:02d} {timestamp[3]:02d}:{timestamp[4]:02d}"
       
            # 清空每分鐘記錄
            temp_list.clear()
            hum_list.clear()
            
            print(f'記錄時間: {formatted_time}, 平均溫度: {avg_temp}°C, 平均濕度: {avg_hum}%')
            
        time.sleep(3600)  # 每小時執行一次


# 啟動 DHT22 讀取執行緒
timestamp = time.localtime()
_thread.start_new_thread(read_dht22, ())
_thread.start_new_thread(store_hourly_avg, ())
_thread.start_new_thread(DIY_LIGHT_SENSOR, ())
_thread.start_new_thread(clean_memory, (1,))
_thread.start_new_thread(loop_publish,(connect(),))


cpu_freq=None
cpu_temp_celsius=None
all_heap=None
allocated_heap=None
flash=None
# **處理 API 請求時排序**
cpu_freq,cpu_temp_celsius,all_heap, allocated_heap,flash = check_system()
_thread.start_new_thread(send_to_thingspeak,())

while True:
    try:
        
        cl, addr = s.accept()
        print('客戶端連線來自:', addr)
 
        # 讀取請求內容
        request = cl.recv(1024).decode()
       
        
        # **處理 JSON API 請求**
        if "GET /data_dht22" in request:
            avg_temp = sum(temp_list) / len(temp_list) if temp_list else 0
            avg_hum = sum(hum_list) / len(hum_list) if hum_list else 0
            json_response = ujson.dumps({
                "temp": round(current_temp, 1),
                "hum": round(current_hum, 1),
                "avg_temp": round(avg_temp, 1),
                "avg_hum": round(avg_hum, 1),
                
            })
            cl.sendall("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n".encode())
            cl.sendall(json_response.encode())
        elif "GET /data_light" in request:
            json_response = ujson.dumps({
                "light": light
                })
            cl.sendall("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n".encode())
            cl.sendall(json_response.encode())
        elif "GET /data_system" in request:
            cpu_freq,cpu_temp_celsius,all_heap, allocated_heap,flash = check_system()
            json_response = ujson.dumps({
                "cpu_freq": cpu_freq,
                "cpu_temp_celsius": round(cpu_temp_celsius, 2),
                "all_heap": round(all_heap/1000, 1),
                "allocated_heap": round(allocated_heap/1000, 1),
                "flash": round(flash/1000, 1),             
                
                })
            cl.sendall("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n".encode())
            cl.sendall(json_response.encode())
               
        else:
            
            # **回傳 HTML 頁面**
            html_response = '''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>ESP32 宿舍監測器</title>
    <style>
        *{
            box-sizing: border-box;
        }
        body {
            width: 80%;
            margin: 0 auto;
            background: rgba(134, 134, 134, 0.205);
            height: 80%;
            
        }
        h1{
            font-size: 40px;
            text-align: center;
            font-weight: 700;
            font-family : Noto Sans;
        }
        h2{
            font-family:Noto Sans;
            font-size: 25px;
            font-weight:600;

        }
        p{
            
            font-weight:100;


        }
        .tybe{
            font-size:18px;
            font-weight:300;
            margin-left:20px;



        }
        .senser_box{
            max-width:100%;
            min-width:33%;
            height: 250px; ;
            background-color: rgba(255, 255, 255, 0.7);
            float: left;
        }
        #light_led{
            margin-left: 5px;
            position:relative;
            justify-content: space-between;
        }
        #temperature_h2{
            margin-left: 5px;
            position:relative;
            justify-content: space-between ;




        }
        #age_1h{
            margin-left: 5px;
            justify-content: space-between



        }
        #system_info_panel {
            position: fixed;
            top: 50px;
            right: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 16px;
            z-index: 1000;
        }

        #system_info_panel p {
            display: flex;
            justify-content: space-between;
            margin: 0;
        }

        #current_time {
            position: fixed;
            top: 10px;
            right: 10px;
            font-size: 18px;
            font-weight: bold;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
        }
    </style>

    <script>
        function updateTime() {
            const now = new Date();
            const formattedTime = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ` +
                `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
            document.getElementById("current_time").innerText = formattedTime;
        }

        function updateDHT22() {
            fetch('/data_dht22')
                .then(response => response.json())
                .then(data => {
                    document.getElementById("current_temp").innerText = `${data.temp}°C`;
                    document.getElementById("current_hum").innerText = `${data.hum}%`;
                    document.getElementById("avg_temp").innerText = `${data.avg_temp}°C`;
                    document.getElementById("avg_hum").innerText = `${data.avg_hum}%`;
                })
                .catch(error => console.error("無法獲取溫濕度數據:", error));
        }

        function updateLight() {
            fetch('/data_light')
                .then(response => response.json())
                .then(data => {
                    document.getElementById("light").innerText = data.light;
                })
                .catch(error => console.error("無法獲取亮度數據:", error));
        }

        function updateSystem() {
            fetch('/data_system')
                .then(response => {
                    if (!response.ok) throw new Error("HTTP 錯誤: " + response.status);
                    return response.json();
                })
                .then(data => {
                    document.getElementById("system_info_panel").innerHTML = `
                        <p><strong>CPU 頻率:</strong> <span>${data.cpu_freq} MHz</span></p>
                        <p><strong>CPU 溫度:</strong> <span>${data.cpu_temp_celsius}°C</span></p>
                        <p><strong>RAM:</strong> <span>${data.all_heap} KB</span></p>
                        <p><strong>RAM(use):</strong> <span>${data.allocated_heap} KB</span></p>
                        <p><strong>Flash:</strong> <span>${data.flash} KB</span></p>
                    `;
                })
                .catch(error => console.error("無法獲取系統數據:", error));
        }

        window.onload = function () {
            updateTime();
            updateDHT22();
            updateLight();
            updateSystem();
        };

        setInterval(updateTime, 1000);
        setInterval(updateSystem, 1000);
        setInterval(updateDHT22, 60000);
        setInterval(updateLight, 5000);
    </script>
</head>

<body>
    <dvi id="esp32">
    <h1>ESP32 宿舍監測器</h1>

    
    <div id="current_time">載入中...</div>

    <div id="system_info_panel">
        <p><strong>CPU 頻率:</strong> <span id="cpu_freq">載入中...</span></p>
        <p><strong>CPU 溫度:</strong> <span id="cpu_temp_celsius">載入中...</span></p>
        <p><strong>RAM:</strong> <span id="all_heap">載入中...</span></p>
        <p><strong>RAM(use):</strong> <span id="allocated_heap">載入中...</span></p>
        <p><strong>Flash:</strong> <span id="flash">載入中...</span></p>
    </div>

    </dvi>
    <div class="senser">
        <div class="senser_box">
            <h2 id="light_led">ESP32 亮度監測</h2>
             <p class="tybe"><strong>亮度狀況:</strong> <span id="light">載入中...</span></p>
        </div>     
        <div class="senser_box">  
            <h2 id="temperature_h2">ESP32 目前溫度</h2>
            <p class="tybe"><strong>目前溫度:</strong> <span id="current_temp">載入中...</span></p>
            <p class="tybe"><strong>目前濕度:</strong> <span id="current_hum">載入中...</span></p>
         </div>
        <div class="senser_box">
             <h2 id="age_1h">過去 1 小時的平均值</h2>
             <p class="tybe"><strong>平均溫度:</strong> <span id="avg_temp">載入中...</span></p>
            <p class="tybe"><strong>平均濕度:</strong> <span id="avg_hum">載入中...</span></p>
         </div>
    </div>
</body>
</html>

'''
            cl.sendall("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\n\r\n".encode())
            cl.sendall(html_response.encode())
        
    except OSError as e:
        print("錯誤:", e)
    
    finally:
        cl.close()

