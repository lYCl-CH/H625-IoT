import gc
import time
import _thread
import esp
import esp32
import machine


def adjust_freq(load=60):
        """根據負載動態調整 CPU 頻率"""
        if load > 80:
            machine.freq(240000000)  # 高效能模式 240MHz
        elif load > 50:
            machine.freq(160000000)  # 中等模式 160MHz
        else:
            machine.freq(80000000)   # 省電模式 80MHz
        print(f"CPU 負載: {machine.freq() / 1000} KHz")
        time.sleep(1)
def check_system():
        # 取得總可用 Heap 記憶體
        all_heap = gc.mem_free() + gc.mem_alloc()
        # 取得記憶體分配情況
        allocated_heap = gc.mem_alloc()
        # MicroPython 沒有內建 API 來查看 DMA RAM，但可以測試 Wi-Fi 啟動時的影響
        Flash = esp.flash_size()
#         print("==============================")
#         print(f"總 Heap 記憶體: {free_heap} bytes")
#         print(f"已使用 Heap 記憶體: {allocated_heap} bytes")
#         print(f"Flash 記憶體大小: {esp32_info} bytes")  # 確保 Flash 記憶體沒問題
#         print("==============================\n")
        cpu_temp = esp32.raw_temperature()  # 取得原始溫度數據
        cup_temp_celsius = (cpu_temp - 32) / 1.8  # 近似轉換為攝氏溫度
        cpu_freq = (machine.freq()/1000000)
        return cpu_freq,cup_temp_celsius,all_heap, allocated_heap,Flash      
def clean_memory(s=5):
    while True:
       gc.collect()
       time.sleep(s)



