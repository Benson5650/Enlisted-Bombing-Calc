import json
import math
import tkinter as tk
import os
import easyocr
import numpy as np
import pyautogui
import re
import pygetwindow as gw
import threading
import time

# 初始化全局變量
x, y = 0, 0
def_ocr_lang = ['ch_sim', 'en'] #default language
selection = None 
reader = None
ocr_running = False
failure_count = 10

def start_move_label(event):
    global x, y
    x = event.x
    y = event.y

def stop_move_label(event):
    global x, y
    x, y = None, None

def do_move_label(event, top: tk.Toplevel):
    global x, y
    deltax = event.x - x
    deltay = event.y - y
    new_x = top.winfo_x() + deltax
    new_y = top.winfo_y() + deltay
    top.geometry(f"+{new_x}+{new_y}")

def load_config(): 
    config = {} 
    if os.path.exists("appsetting.json"): 
        with open("appsetting.json", "r") as config_file: 
            config = json.load(config_file)
    return config

def save_config(top): 
    global selection
    new_x = top.winfo_x() 
    new_y = top.winfo_y() 
    config = {
        "label_position": f"{new_x},{new_y}",
        "ocr_language": ocr_lang,
        "selection_region": selection
    }
    with open("appsetting.json", "w") as config_file: 
        json.dump(config, config_file)

def on_closing(root, top): 
    save_config(top) 
    root.destroy()

def capture_region(left, top, width, height): 
    # 抓取指定區域 
    screenshot = pyautogui.screenshot(region=(left, top, width, height)) 
    return screenshot

def ocr():
    global root, selection, reader, failure_count
    if selection is None:
        return
    
    label = root.winfo_children()[0].winfo_children()[0]
    left, top, width, height = selection["left"], selection["top"], selection["width"], selection["height"]    

    image = capture_region(left, top, width, height)
    result = reader.readtext(np.array(image), detail = 0, paragraph=True)
    # 移除空白 
    text = ''.join(result).replace(' ', '')

    # 判斷是否包含所需的關鍵字
    if any(keyword in text for keyword in ["空速", "高度", "TAS", "ALT"]):
        # 提取空速、高度、TAS、ALT的數值
        numbers = re.findall(r'\d+', text) 
        if len(numbers) >= 2: 
            tas = int(numbers[0]) 
            alt = int(numbers[1])
            # 計算公式
            result_value = math.sqrt(0.015747 * alt * tas * tas + alt * alt)
        
            # 顯示結果
            # 假設只有一個子元件，即 Label，直接更新其文本
            label.config(text=f"結果: {int(result_value)}")
            print(f"結果: {result_value}")

            failure_count = 0
        else:
            failure_count += 1
            print(f"無法判斷:{failure_count}")
    else:
        failure_count += 1
        print(f"無法判斷:{failure_count}")
    
    if failure_count >= 3:
        label.config(text="無法判斷")

def run_ocr():
    global ocr_running, failure_count
    while ocr_running:
        ocr()
        if failure_count < 10:  # 根據失敗次數設置間隔時間
            time.sleep(1)
        else:
            time.sleep(5)

def toggle_ocr(): 
    global ocr_running 
    if ocr_switch_var.get():
        select_button.config(state=tk.DISABLED)
    else:
        select_button.config(state=tk.NORMAL) 
    if ocr_running: 
        ocr_running = False 
    else: 
        ocr_running = True 
        threading.Thread(target=run_ocr).start()    # 使用執行序來執行run_ocr

def select_region():
    global selection
    selection = {}

    # 獲取所有螢幕的總解析度
    all_windows = gw.getAllWindows()
    min_x = min([window.left for window in all_windows])
    min_y = min([window.top for window in all_windows])
    max_x = max([window.right for window in all_windows])
    max_y = max([window.bottom for window in all_windows])
    screen_width = max_x - min_x
    screen_height = max_y - min_y

    selection_win = tk.Toplevel(root)
    selection_win.geometry(f"{screen_width}x{screen_height}+{min_x}+{min_y}")
    selection_win.attributes("-fullscreen", True)
    selection_win.attributes("-topmost", True)
    selection_win.config(cursor="cross")
    selection_win.attributes("-alpha", 0.3)

    def on_drag(event):
        canvas.delete("selection")
        selection['end'] = (event.x_root, event.y_root)
        canvas.create_rectangle(selection['start'][0], selection['start'][1], selection['end'][0], selection['end'][1], outline='red', tag="selection")
    
    def on_release(event):
        selection['end'] = (event.x_root, event.y_root)
        left = min(selection['start'][0], selection['end'][0])
        top = min(selection['start'][1], selection['end'][1])
        width = abs(selection['start'][0] - selection['end'][0])
        height = abs(selection['start'][1] - selection['end'][1])
        selection['left'] = left
        selection['top'] = top
        selection['width'] = width
        selection['height'] = height
        print(f"選取區域: {selection}")
        region_label.config(text=f"x: {left}\ny: {top}\nwidth: {width}\nheight: {height}")
        selection_win.destroy()

    def on_start(event):
        selection['start'] = (event.x_root, event.y_root)
        selection_win.bind("<B1-Motion>", on_drag)
        selection_win.bind("<ButtonRelease-1>", on_release)

    selection_win.bind("<Button-1>", on_start)

    canvas = tk.Canvas(selection_win, bg='gray')
    canvas.pack(fill=tk.BOTH, expand=True)

def main():
    global root, region_label, reader, selection, ocr_lang, ocr_switch_var, select_button

    appsetting = load_config()

    # 初始化 easyOCR 
    if "ocr_language" in appsetting: 
        ocr_lang = appsetting['ocr_language'] 
        
    else:
        ocr_lang = def_ocr_lang #use default language
    reader = easyocr.Reader(ocr_lang)
    root = tk.Tk()
    root.geometry("300x200")

    top = tk.Toplevel(root)
    top.overrideredirect(True)
    top.attributes("-transparentcolor", top["bg"])
    top.wm_attributes("-topmost", 1)
        
    if "label_position" in appsetting:
        position = tuple(map(int, appsetting["label_position"].split(",")))
        top.geometry(f"+{position[0]}+{position[1]}") 
    else: 
        top.geometry("+100+10")

    top.update_idletasks()

    lbldistance = tk.Label(top, text="無法計算", font=("Arial", 20, "bold"), fg="#fff")
    lbldistance.pack()

    # 綁定事件到 Label
    top.bind("<Button-1>", start_move_label)
    top.bind("<ButtonRelease-1>", stop_move_label)
    top.bind("<B1-Motion>", lambda event: do_move_label(event, top))

    # 添加選取區域按鈕
    select_button = tk.Button(root, text="設定偵測區域", command=select_region)
    select_button.pack()

    # 添加顯示選取區域的 Label
    region_label = tk.Label(root, text="選取區域: 無")
    region_label.pack()
    if "selection_region" in appsetting: 
        selection = appsetting["selection_region"] 
        region_label.config(text=f"選取區域:\nx={selection['left']} y={selection['top']}\nwidth={selection['width']} height={selection['height']}")
    else: 
        selection = None

    # 添加開關按鈕 
    ocr_switch_var = tk.BooleanVar() 
    ocr_switch = tk.Checkbutton(root, text="啟動OCR", variable=ocr_switch_var, onvalue=True, offvalue=False, command=toggle_ocr) 
    ocr_switch.pack()

    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root, top))
    root.mainloop()

main()
