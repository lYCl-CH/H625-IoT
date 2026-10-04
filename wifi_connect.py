import network
import time
sta = network.WLAN(network.STA_IF)  # 建立 STA（client）模式
sta.active(True)                    # 啟用 Wi-Fi

nets = sta.scan()  # 搜尋附近 Wi-Fi 熱點

def read_txt_to_dict(filename):
    data_dict = {}
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if ',' in line:
                    key, value = line.split(',', 1)
                    data_dict[key] = value
    except Exception as e:
        print("讀取錯誤:", e)
    return data_dict

my_dict = read_txt_to_dict('ssid.txt')
ssid_keys = list(my_dict.keys())
 
for net in nets:
    ssid = net[0].decode('utf-8')
    bssid = ':'.join('%02x' % b for b in net[1])
    channel = net[2]
    rssi = net[3]
    security = net[4]
    hidden = net[5]
    print(f"SSID: {ssid} \nBSSID: {bssid}\nChannel: {channel}\nRSSI: {rssi} dBm\nSecurity: {security}\n Hidden: {hidden}")
    print('-------------------')
    
    if ssid in my_dict:
        password = my_dict[ssid]
        print(ssid, password)
        sta.connect(ssid, password)
        # 等待連線完成
        for _ in range(20):
            if sta.isconnected():
                print('Wi-Fi 連接成功，IP 地址:', sta.ifconfig()[0])
#                 sta.config(pm=network.WLAN.PM_POWERSAVE)
                break
            time.sleep(0.5)

        if sta.isconnected():
            print('Wi-Fi 連接成功，IP 地址:', sta.ifconfig()[0])
            break
        else:
            print('Wi-Fi 連接失敗')
        
def ip():
    return sta.ifconfig()[0]