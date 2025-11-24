# Network Traffic Monitor

A real-time network traffic monitoring application based on Chrome DevTools Protocol, featuring live visualization and ISP identification.

[中文](#中文版本) | [English](#english-version)

---

## English Version

### Overview

This application monitors network traffic by connecting to Chrome's debugging interface, capturing packet data, calculating bandwidth usage, and displaying real-time traffic curves with ISP information.

### Features

- Real-time network traffic monitoring via Chrome DevTools Protocol
- Live bandwidth visualization with multi-line charts
- ISP identification for each IP address
- Statistical dashboard (current speed, peak speed, total data, active IPs, session time)
- Export full traffic history as PNG charts
- Pause/Resume monitoring functionality
- Data clearing capability

### System Requirements

- **Operating System**: Windows (can be modified for Linux/macOS)
- **Python Version**: 3.7+
- **Chrome Browser**: Installed at default location or custom path

### Installation

1. Install required Python packages:

```bash
pip install pychrome pyqtgraph PyQt5 matplotlib requests
```

2. Verify Chrome installation path (modify `CHROME_PATH` if needed)

3. Run the application:

```bash
python network_monitor.py
```

### Usage Instructions

#### Basic Operation

1. **Launch Application**: Run the script, Chrome will automatically open in debug mode
2. **Start Monitoring**: Open websites in the auto-launched Chrome window
3. **View Statistics**: Real-time data displayed in the statistics panel
4. **Pause/Resume**: Click "Pause" button to freeze the display
5. **Export Data**: Click "Export plot" to save full traffic history
6. **Clear Data**: Click "Clear data" to reset all records

#### Important Notes

- **CRITICAL**: Only monitor traffic in the automatically launched Chrome window
- The monitoring captures network requests larger than 10KB
- ISP queries are limited to 1000 requests per IP per day (sign up at ipinfo.io for more)
- Data is saved to `responses.jsonl` in the same directory

### Configuration Parameters

#### Basic Settings

```python
OUTPUT_FILE = "responses.jsonl"          # Data output file
ROLLING_SECONDS = 30                     # Time window for display (seconds)
UPDATE_INTERVAL = 16                     # UI update interval (milliseconds)
NUM_LINES = 3                            # Number of IP lines to display
MAX_RECORDS_PER_IP = 1000                # Maximum records per IP (memory management)
```

#### Color Customization

```python
FIXED_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1']  # Line colors (hex format)
```

#### Chrome Configuration

```python
CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
DEBUG_PORT = 9222                        # Chrome debug port
USER_DATA_DIR = "C:/ChromeDebug"         # Chrome user data directory
```

### Core Functions Reference

#### Network Monitoring Functions

##### `start_chrome()`
Launches Chrome browser in debug mode.

**Parameters**: None

**Returns**: None

**Usage**:
```python
threading.Thread(target=start_chrome, daemon=True).start()
```

##### `attach_tab(tab)`
Attaches to a Chrome tab for network monitoring.

**Parameters**:
- `tab`: Chrome tab object from pychrome

**Returns**: None

**Key Internal Handlers**:
- `handle_response_received`: Captures response metadata and IP addresses
- `handle_loading_finished`: Calculates bandwidth and saves records

##### `monitor_tabs()`
Continuously scans and attaches to all Chrome tabs.

**Parameters**: None

**Returns**: None

**Loop Interval**: 2 seconds

##### `get_isp(ip)`
Queries ISP information for an IP address using ipinfo.io API.

**Parameters**:
- `ip` (str): IP address to query

**Returns**: ISP organization name or IP address if query fails

**Features**:
- LRU cache with 256 entries
- Simplifies "AS" prefix format
- 3-second timeout

**Customization**:
```python
# Add API token for higher rate limits
url = f"https://ipinfo.io/{ip}/json?token=YOUR_TOKEN_HERE"
```

#### UI Component Classes

##### `SafeTimeAxis(pg.AxisItem)`
Custom time axis formatter for pyqtgraph.

**Method**:
- `tickStrings(values, scale, spacing)`: Converts timestamps to HH:MM:SS format

##### `StatisticsPanel(QtWidgets.QWidget)`
Statistics dashboard widget.

**Methods**:
- `init_ui()`: Initializes the panel layout with 5 statistics cards
- `update_stats(current_speed, peak_speed, total_mb, active_ips)`: Updates displayed values

**Customization**:
```python
# Modify statistics in init_ui()
stats = [
    ("key", "Display Name", "Default Value"),
    # Add more statistics here
]
```

##### `NetworkMonitorApp(QtWidgets.QWidget)`
Main application window.

**Key Methods**:

###### `init_ui()`
Initializes the main user interface.

**Customizable Elements**:
- Window size: `self.setGeometry(100, 100, 1400, 800)`
- Font family: Modify stylesheet `font-family` property
- Button labels: Change text in QPushButton constructors

###### `update_plot()`
Core update loop - reads data, processes records, and updates visualization.

**Process Flow**:
1. Read new records from `OUTPUT_FILE`
2. Parse JSON and store in `record_data`
3. Calculate top N IPs by total bandwidth
4. Aggregate data per second
5. Update chart lines and statistics

**Performance Tuning**:
```python
# Adjust time window
window_start = now - datetime.timedelta(seconds=ROLLING_SECONDS)

# Modify data aggregation
per_second[t_sec] = max(per_second[t_sec], r["speed_mbps"])  # Use max
# OR
per_second[t_sec] += r["speed_mbps"]  # Use sum
```

###### `toggle_monitoring()`
Pauses/resumes monitoring without closing Chrome.

###### `clear_data()`
Clears all records with confirmation dialog.

###### `export_full_plot()`
Exports complete traffic history as matplotlib chart.

**Customization**:
```python
# Modify chart style
plt.style.use('dark_background')  # Change to 'seaborn', 'ggplot', etc.

# Adjust figure size
fig, ax = plt.subplots(figsize=(14, 7))  # Width, Height in inches

# Change export DPI
plt.savefig(filename, dpi=150, facecolor='#1E1E1E')  # Increase for higher quality
```

### Data Structure

#### JSON Record Format
```json
{
  "time": "14:30:45",
  "size_kb": 1024.5,
  "duration_s": 0.152,
  "speed_mbps": 53.8,
  "ip": "192.168.1.100"
}
```

#### In-Memory Data Structure
```python
record_data = {
    "192.168.1.100": deque([
        {"time": datetime.datetime(...), "speed_mbps": 53.8},
        {"time": datetime.datetime(...), "speed_mbps": 61.2},
        # ... (max MAX_RECORDS_PER_IP entries)
    ], maxlen=1000)
}
```

### Traffic Filtering

The application filters network requests to reduce noise:

```python
# Minimum packet size filter
if encoded_length < 10*1024:  # Skip packets < 10KB
    return

# Anomaly filter
if speed_mbps >= 500 and duration == 0.03:  # Skip likely timing errors
    return
```

**Customization**:
```python
# Change minimum size to 1KB
if encoded_length < 1024:
    return

# Adjust anomaly threshold
if speed_mbps >= 1000 and duration < 0.01:
    return
```

---

## 中文版本

### 概述

本應用程式透過連接 Chrome 的除錯介面來監控網路流量，擷取封包資料、計算頻寬使用情況，並以即時流量曲線顯示各 IP 的 ISP 資訊。

### 功能特色

- 透過 Chrome DevTools Protocol 進行即時網路流量監控
- 多線即時頻寬視覺化圖表
- 自動識別各 IP 位址的 ISP 資訊
- 統計資訊面板（當前速度、峰值速度、總流量、活躍 IP、會話時長）
- 匯出完整流量歷史記錄為 PNG 圖表
- 暫停/繼續監控功能
- 資料清除功能

### 系統需求

- **作業系統**：Windows（可修改為 Linux/macOS）
- **Python 版本**：3.7+
- **Chrome 瀏覽器**：安裝於預設位置或自訂路徑

### 安裝步驟

1. 安裝所需的 Python 套件：

```bash
pip install pychrome pyqtgraph PyQt5 matplotlib requests
```

2. 確認 Chrome 安裝路徑（必要時修改 `CHROME_PATH`）

3. 執行應用程式：

```bash
python network_monitor.py
```

### 使用說明

#### 基本操作

1. **啟動應用程式**：執行腳本，Chrome 將自動以除錯模式開啟
2. **開始監控**：在自動啟動的 Chrome 視窗中開啟網站
3. **查看統計**：即時資料顯示在統計面板中
4. **暫停/繼續**：點擊「Pause」按鈕凍結顯示
5. **匯出資料**：點擊「Export plot」儲存完整流量歷史
6. **清除資料**：點擊「Clear data」重置所有記錄

#### 重要注意事項

- **關鍵**：僅監控自動啟動的 Chrome 視窗中的流量
- 監控會擷取大於 10KB 的網路請求
- ISP 查詢每個 IP 每天限制 1000 次請求（在 ipinfo.io 註冊可獲得更多次數）
- 資料儲存在同目錄下的 `responses.jsonl` 檔案中

### 設定參數

#### 基本設定

```python
OUTPUT_FILE = "responses.jsonl"          # 資料輸出檔案
ROLLING_SECONDS = 30                     # 顯示時間窗口（秒）
UPDATE_INTERVAL = 16                     # UI 更新間隔（毫秒）
NUM_LINES = 3                            # 顯示的 IP 線條數量
MAX_RECORDS_PER_IP = 1000                # 每個 IP 的最大記錄數（記憶體管理）
```

#### 顏色自訂

```python
FIXED_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1']  # 線條顏色（十六進位格式）
```

#### Chrome 設定

```python
CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"
DEBUG_PORT = 9222                        # Chrome 除錯埠
USER_DATA_DIR = "C:/ChromeDebug"         # Chrome 使用者資料目錄
```

### 核心函數參考

#### 網路監控函數

##### `start_chrome()`
以除錯模式啟動 Chrome 瀏覽器。

**參數**：無

**返回值**：無

**使用方式**：
```python
threading.Thread(target=start_chrome, daemon=True).start()
```

##### `attach_tab(tab)`
附加到 Chrome 分頁進行網路監控。

**參數**：
- `tab`：來自 pychrome 的 Chrome 分頁物件

**返回值**：無

**關鍵內部處理器**：
- `handle_response_received`：擷取回應元資料和 IP 位址
- `handle_loading_finished`：計算頻寬並儲存記錄

##### `monitor_tabs()`
持續掃描並附加到所有 Chrome 分頁。

**參數**：無

**返回值**：無

**循環間隔**：2 秒

##### `get_isp(ip)`
使用 ipinfo.io API 查詢 IP 位址的 ISP 資訊。

**參數**：
- `ip` (str)：要查詢的 IP 位址

**返回值**：ISP 組織名稱，查詢失敗時返回 IP 位址

**特性**：
- 具有 256 個條目的 LRU 快取
- 簡化「AS」前綴格式
- 3 秒逾時

**客製化**：
```python
# 新增 API 令牌以提高速率限制
url = f"https://ipinfo.io/{ip}/json?token=YOUR_TOKEN_HERE"
```

#### UI 元件類別

##### `SafeTimeAxis(pg.AxisItem)`
pyqtgraph 的自訂時間軸格式化器。

**方法**：
- `tickStrings(values, scale, spacing)`：將時間戳記轉換為 HH:MM:SS 格式

##### `StatisticsPanel(QtWidgets.QWidget)`
統計資訊儀表板元件。

**方法**：
- `init_ui()`：初始化包含 5 個統計卡片的面板佈局
- `update_stats(current_speed, peak_speed, total_mb, active_ips)`：更新顯示值

**客製化**：
```python
# 在 init_ui() 中修改統計項目
stats = [
    ("key", "顯示名稱", "預設值"),
    # 在此新增更多統計項目
]
```

##### `NetworkMonitorApp(QtWidgets.QWidget)`
主應用程式視窗。

**主要方法**：

###### `init_ui()`
初始化主使用者介面。

**可自訂元素**：
- 視窗大小：`self.setGeometry(100, 100, 1400, 800)`
- 字型家族：修改樣式表中的 `font-family` 屬性
- 按鈕標籤：變更 QPushButton 建構函數中的文字

###### `update_plot()`
核心更新迴圈 - 讀取資料、處理記錄並更新視覺化。

**處理流程**：
1. 從 `OUTPUT_FILE` 讀取新記錄
2. 解析 JSON 並儲存到 `record_data`
3. 依總頻寬計算前 N 個 IP
4. 每秒聚合資料
5. 更新圖表線條和統計資訊

**效能調整**：
```python
# 調整時間窗口
window_start = now - datetime.timedelta(seconds=ROLLING_SECONDS)

# 修改資料聚合方式
per_second[t_sec] = max(per_second[t_sec], r["speed_mbps"])  # 使用最大值
# 或者
per_second[t_sec] += r["speed_mbps"]  # 使用總和
```

###### `toggle_monitoring()`
暫停/繼續監控而不關閉 Chrome。

###### `clear_data()`
清除所有記錄（附確認對話框）。

###### `export_full_plot()`
將完整流量歷史匯出為 matplotlib 圖表。

**客製化**：
```python
# 修改圖表樣式
plt.style.use('dark_background')  # 變更為 'seaborn'、'ggplot' 等

# 調整圖形大小
fig, ax = plt.subplots(figsize=(14, 7))  # 寬度、高度（英吋）

# 變更匯出 DPI
plt.savefig(filename, dpi=150, facecolor='#1E1E1E')  # 提高以獲得更高品質
```

### 資料結構

#### JSON 記錄格式
```json
{
  "time": "14:30:45",
  "size_kb": 1024.5,
  "duration_s": 0.152,
  "speed_mbps": 53.8,
  "ip": "192.168.1.100"
}
```

#### 記憶體內資料結構
```python
record_data = {
    "192.168.1.100": deque([
        {"time": datetime.datetime(...), "speed_mbps": 53.8},
        {"time": datetime.datetime(...), "speed_mbps": 61.2},
        # ... (最多 MAX_RECORDS_PER_IP 個條目)
    ], maxlen=1000)
}
```

### 流量過濾

應用程式會過濾網路請求以減少雜訊：

```python
# 最小封包大小過濾
if encoded_length < 10*1024:  # 跳過 < 10KB 的封包
    return

# 異常過濾
if speed_mbps >= 500 and duration == 0.03:  # 跳過可能的計時錯誤
    return
```

**客製化**：
```python
# 將最小大小變更為 1KB
if encoded_length < 1024:
    return

# 調整異常閾值
if speed_mbps >= 1000 and duration < 0.01:
    return
```
