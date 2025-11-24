import os
import subprocess
import time
import json
import datetime
from collections import defaultdict, deque
import threading
import requests
from functools import lru_cache

import pychrome
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# ==================== 配置區 ====================
OUTPUT_FILE = "responses.jsonl"
ROLLING_SECONDS = 30
UPDATE_INTERVAL = 16
NUM_LINES = 3
FIXED_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1']
MAX_RECORDS_PER_IP = 1000

# Chrome配置
CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
DEBUG_PORT = 9222
USER_DATA_DIR = "C:/ChromeDebug"

# ==================== 全局變量 ====================
position = 0
record_data = defaultdict(lambda: deque(maxlen=MAX_RECORDS_PER_IP))
ip_to_isp_cache = {}
tab_listeners = {}
request_start_times = {}
request_ips = {}
is_monitoring = True
total_data_transferred = 0
session_start_time = datetime.datetime.now()

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    pass

def start_chrome():
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)
    subprocess.Popen([
        CHROME_PATH,
        f'--remote-debugging-port={DEBUG_PORT}',
        f'--user-data-dir={USER_DATA_DIR}'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def attach_tab(tab):
    if tab.id in tab_listeners:
        return
    
    try:
        tab.start()
        tab.call_method("Network.enable")
        tab.call_method("Page.enable")

        def handle_response_received(**kwargs):
            request_id = kwargs.get("requestId")
            timestamp = kwargs.get("timestamp", time.time())
            request_start_times[request_id] = timestamp
            response = kwargs.get("response", {})
            
            if response.get("fromDiskCache") or response.get("fromMemoryCache"):
                return
            
            ip = response.get("remoteIPAddress", "")
            request_ips[request_id] = ip

        def handle_loading_finished(**kwargs):
            global total_data_transferred
            try:
                request_id = kwargs.get("requestId")
                encoded_length = kwargs.get("encodedDataLength", 0)
                
                if encoded_length < 10*1024:
                    return
                
                start_time = request_start_times.get(request_id, kwargs.get("timestamp", time.time()))
                end_time = kwargs.get("timestamp", time.time())
                duration = max(end_time - start_time, 0.03)
                
                size_kb = encoded_length / 1024
                speed_mbps = encoded_length * 8 / (1024*1024) / duration
                ip = request_ips.get(request_id, "")
                
                """
                Traffic fillter
                * tune the speed and duration if ness
                """
                if speed_mbps >= 500 and duration == 0.03:
                    return
                
                total_data_transferred += encoded_length
                
                record = {
                    "time": time.strftime("%H:%M:%S", time.localtime()),
                    "size_kb": round(size_kb, 2),
                    "duration_s": round(duration, 3),
                    "speed_mbps": round(speed_mbps, 2),
                    "ip": ip
                }
                
                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
                    f.flush()
                    
            except Exception as e:
                print(f"Fail to process responce: {e}")

        tab.set_listener("Network.responseReceived", handle_response_received)
        tab.set_listener("Network.loadingFinished", handle_loading_finished)
        tab_listeners[tab.id] = tab
    except Exception as e:
        print(f"Fail to lable: {e}")

def monitor_tabs():
    browser = pychrome.Browser(url=f"http://127.0.0.1:{DEBUG_PORT}")
    while is_monitoring:
        try:
            tabs = browser.list_tab()
            for tab in tabs:
                attach_tab(tab)
        except Exception:
            pass
        time.sleep(2)

# ==================== ISP Request ====================
@lru_cache(maxsize=256)
def get_isp(ip):
    """
    Check the isp using ipinfo json api.
    *each ip has 1000 request limit.
    sign up and use auth key for more.
    """
    if not ip or ip == "unknown":
        return "Unknown"
    
    try:
        url = f"https://ipinfo.io/{ip}/json"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            org = data.get("org", ip)
            if org.startswith("AS"):
                parts = org.split(" ", 1)
                if len(parts) > 1:
                    org = parts[1]
            return org
    except Exception as e:
        print(f"Fail to get isp {ip}: {e}")
    
    return ip

class SafeTimeAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strs = []
        for v in values:
            try:
                if isinstance(v, (int, float)) and v > 0:
                    strs.append(datetime.datetime.fromtimestamp(v).strftime("%H:%M:%S"))
                else:
                    strs.append("")
            except Exception:
                strs.append("")
        return strs

class StatisticsPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QtWidgets.QGridLayout(self)
        layout.setSpacing(10)
        
        self.labels = {}
        stats = [
            ("current_speed", "Current Sprrd ", "0 Mbps"),
            ("peak_speed", "Peak Speed ", "0 Mbps"),
            ("total_data", "Total traffic ", "0 MB"),
            ("active_ips", "Active IP", "0"),
            ("session_time", "Mointor time ", "00:00:00")
        ]
        
        for idx, (key, title, default) in enumerate(stats):
            row = idx // 3
            col = idx % 3
            
            frame = QtWidgets.QFrame()
            frame.setFrameStyle(QtWidgets.QFrame.StyledPanel)
            frame.setStyleSheet("""
                QFrame {
                    background-color: #2C3E50;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            
            frame_layout = QtWidgets.QVBoxLayout(frame)
            frame_layout.setSpacing(5)
            
            title_label = QtWidgets.QLabel(title)
            title_label.setStyleSheet("color: #95A5A6; font-size: 30px;")
            title_label.setAlignment(QtCore.Qt.AlignCenter)
            
            value_label = QtWidgets.QLabel(default)
            value_label.setStyleSheet("color: #ECF0F1; font-size: 20px; font-weight: bold;")
            value_label.setAlignment(QtCore.Qt.AlignCenter)
            
            frame_layout.addWidget(title_label)
            frame_layout.addWidget(value_label)
            
            layout.addWidget(frame, row, col)
            self.labels[key] = value_label
    
    def update_stats(self, current_speed, peak_speed, total_mb, active_ips):
        self.labels["current_speed"].setText(f"{current_speed:.1f} Mbps")
        self.labels["peak_speed"].setText(f"{peak_speed:.1f} Mbps")
        self.labels["total_data"].setText(f"{total_mb:.1f} MB")
        self.labels["active_ips"].setText(str(active_ips))
        
        elapsed = datetime.datetime.now() - session_start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.labels["session_time"].setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

class NetworkMonitorApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.position = 0
        self.peak_speed = 0
        self.line_labels = [""] * NUM_LINES
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Network traffic mointor")
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #ECF0F1;
                font-family: 'Microsoft JhengHei', 'Segoe UI', Arial;
            }
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #21618C;
            }
        """)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        title_layout = QtWidgets.QHBoxLayout()
        title_label = QtWidgets.QLabel("Network traffic mointor")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #3498DB;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        self.btn_pause = QtWidgets.QPushButton("Pause")
        self.btn_pause.clicked.connect(self.toggle_monitoring)
        self.btn_export = QtWidgets.QPushButton("Export plot")
        self.btn_export.clicked.connect(self.export_full_plot)
        self.btn_clear = QtWidgets.QPushButton("Clear data")
        self.btn_clear.clicked.connect(self.clear_data)
        
        title_layout.addWidget(self.btn_pause)
        title_layout.addWidget(self.btn_export)
        title_layout.addWidget(self.btn_clear)
        
        main_layout.addLayout(title_layout)
        
        self.stats_panel = StatisticsPanel()
        main_layout.addWidget(self.stats_panel)
        
        time_axis = SafeTimeAxis(orientation='bottom')
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground('#2C3E50')
        
        self.plot = self.plot_widget.addPlot(
            title="<span style='color: #ECF0F1; font-size: 20px; font-family: Microsoft JhengHei '>Traffic curve</span>",
            axisItems={'bottom': time_axis}
        )
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel('left', '<span style="color: #ECF0F1;font-family: Microsoft JhengHei" >Mbps</span>')
        self.plot.setLabel('bottom', '<span style="color: #ECF0F1; font-family: Microsoft JhengHei ">Time</span>')
        self.plot.addLegend(offset=(10, 10))
        
        self.lines = []
        for idx, color in enumerate(FIXED_COLORS):
            line = self.plot.plot([], [], pen=pg.mkPen(color, width=3), name="")
            self.lines.append(line)
        
        main_layout.addWidget(self.plot_widget)
        
        self.status_label = QtWidgets.QLabel("Mointoring...")
        self.status_label.setStyleSheet("color: #2ECC71; font-size: 12px; padding: 5px; font-family: Microsoft JhengHei;")
        main_layout.addWidget(self.status_label)
        
        # 定時器
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(UPDATE_INTERVAL)
    
    def toggle_monitoring(self):
        """Switch"""
        if self.timer.isActive():
            self.timer.stop()
            self.btn_pause.setText("Continue")
            self.status_label.setText("Pause")
            self.status_label.setStyleSheet("color: #F39C12; font-size: 20px; padding: 5px; font-family: Microsoft JhengHei;")
        else:
            self.timer.start()
            self.btn_pause.setText("Pause")
            self.status_label.setText("Monitoring...")
            self.status_label.setStyleSheet("color: #2ECC71; font-size: 20px; padding: 5px; font-family: Microsoft JhengHei;")
    
    def clear_data(self):
        reply = QtWidgets.QMessageBox.question(
            self, 'Confirm', 'You sure to clear all data?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            global record_data, total_data_transferred, session_start_time
            record_data.clear()
            total_data_transferred = 0
            session_start_time = datetime.datetime.now()
            self.position = 0
            self.peak_speed = 0
            
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                pass
            
            QtWidgets.QMessageBox.information(self, 'Complete', 'Data deleted')
    
    def update_plot(self):
        now = datetime.datetime.now()
        
        # read data
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                f.seek(self.position)
                lines_read = f.readlines()
                self.position = f.tell()
        except FileNotFoundError:
            return
        
        # data process
        for line in lines_read:
            try:
                record = json.loads(line.strip())
                ip = record.get("ip", "unknown")
                dt = datetime.datetime.combine(
                    datetime.date.today(),
                    datetime.datetime.strptime(record["time"], "%H:%M:%S").time()
                )
                record_data[ip].append({"time": dt, "speed_mbps": record["speed_mbps"]})
            except Exception:
                continue
        
        if not record_data:
            return
        
        total_speeds = {
            ip: sum(r["speed_mbps"] for r in records) 
            for ip, records in record_data.items()
        }
        top_ips = sorted(total_speeds, key=total_speeds.get, reverse=True)[:NUM_LINES]

        window_start = now - datetime.timedelta(seconds=ROLLING_SECONDS)
        max_value = 1
        current_total_speed = 0
        
        for idx in range(NUM_LINES):
            line = self.lines[idx]
            
            if idx < len(top_ips):
                ip = top_ips[idx]
                
                record_data[ip] = deque(
                    [r for r in record_data[ip] if r["time"] >= window_start],
                    maxlen=MAX_RECORDS_PER_IP
                )
                
                per_second = defaultdict(float)
                for r in record_data[ip]:
                    t_sec = int(r["time"].timestamp())
                    per_second[t_sec] = max(per_second[t_sec], r["speed_mbps"])

                times = []
                values = []
                current = int(window_start.timestamp())
                end_time = int(now.timestamp())
                
                while current <= end_time:
                    times.append(current)
                    speed = per_second.get(current, 0)
                    values.append(speed)
                    if current == end_time:
                        current_total_speed += speed
                    current += 1
                
                line.setData(times, values)
                
                isp_name = get_isp(ip)
                label = f"{isp_name[:30]} {ip}"
                if self.line_labels[idx] != label:
                    self.plot.legend.items[idx][1].setText(label)
                    self.line_labels[idx] = label
                
                if values:
                    max_value = max(max_value, max(values) * 1.2)
            else:
                line.setData([], [])
                if self.line_labels[idx] != "":
                    self.line_labels[idx] = ""
        
        """
        Peak speed:
        *for ref only.
        just the maximum number in data.

        """
        self.peak_speed = max(self.peak_speed, current_total_speed)
        
        self.plot.setXRange(int(window_start.timestamp()), int(now.timestamp()))
        self.plot.setYRange(0, max_value)
        
        total_mb = total_data_transferred / (1024 * 1024)
        active_ips = len([ip for ip, records in record_data.items() if records])
        self.stats_panel.update_stats(current_total_speed, self.peak_speed, total_mb, active_ips)
    
    def export_full_plot(self):
        """Export"""
        self.timer.stop()
        
        full_record_data = defaultdict(list)
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        ip = record.get("ip", "unknown")
                        dt = datetime.datetime.combine(
                            datetime.date.today(),
                            datetime.datetime.strptime(record["time"], "%H:%M:%S").time()
                        )
                        full_record_data[ip].append({"time": dt, "speed_mbps": record["speed_mbps"]})
                    except Exception:
                        continue
        except FileNotFoundError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Null')
            self.timer.start()
            return
        
        if not full_record_data:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Null')
            self.timer.start()
            return
        
        total_speeds = {
            ip: sum(r["speed_mbps"] for r in records) 
            for ip, records in full_record_data.items()
        }
        top_ips = sorted(total_speeds, key=total_speeds.get, reverse=True)[:NUM_LINES]
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(14, 7))
        fig.patch.set_facecolor('#1E1E1E')
        ax.set_facecolor('#2C3E50')
        
        for idx, ip in enumerate(top_ips):
            records = full_record_data[ip]
            per_second = defaultdict(float)
            
            for r in records:
                t_sec = r["time"].replace(microsecond=0)
                per_second[t_sec] = max(per_second[t_sec], r["speed_mbps"])
            
            if not per_second:
                continue
            
            start_time = min(per_second.keys())
            end_time = max(per_second.keys())
            times = []
            values = []
            current = start_time
            
            while current <= end_time:
                times.append(current)
                values.append(per_second.get(current, 0))
                current += datetime.timedelta(seconds=1)
            
            isp_name = get_isp(ip)
            ax.plot(times, values, 
                   label=f"{isp_name[:25]}", 
                   color=FIXED_COLORS[idx % len(FIXED_COLORS)],
                   linewidth=2)
        
        ax.set_xlabel("Time", fontsize=12, color='#ECF0F1')
        ax.set_ylabel("Mbps", fontsize=12, color='#ECF0F1')
        ax.set_title("Network traffic", fontsize=16, fontweight='bold', color='#3498DB', pad=20)
        ax.legend(loc='upper left', framealpha=0.9, fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        
        filename = f"network_traffic_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=150, facecolor='#1E1E1E')
        
        plt.show()
        QtWidgets.QMessageBox.information(self, 'Complete', f'Save as: {filename}')
        self.timer.start()

# ==================== 主程序 ====================
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setStyle('Fusion')
    
    threading.Thread(target=start_chrome, daemon=True).start()
    threading.Thread(target=monitor_tabs, daemon=True).start()
    
    window = NetworkMonitorApp()
    window.show()
    
    app.exec_()