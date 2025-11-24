# Network Traffic Monitor

A real-time network traffic monitoring application based on Chrome DevTools Protocol, featuring dual-dimension visualization (IP/ISP and Domain) with live bandwidth tracking.

[中文](#中文版本) | [English](#english-version)

---

## English Version

### Overview

This application monitors network traffic by connecting to Chrome's debugging interface, capturing packet data, calculating bandwidth usage, and displaying real-time traffic curves with both ISP identification and domain-based aggregation. It uses the **Referer header** to accurately attribute CDN traffic to the originating websites.


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
3. **View Statistics**: Real-time data displayed in dual charts (left: IP/ISP, right: Domain)
4. **Pause/Resume**: Click "Pause" button to freeze the display
5. **Export Data**: Click "Export Plot" to save full traffic history with both dimensions
6. **Clear Data**: Click "Clear Data" to reset all records

#### Important Notes

- **CRITICAL**: Only monitor traffic in the automatically launched Chrome window
- The monitoring captures network requests larger than 10KB
- ISP queries are limited to 1000 requests per IP per day (sign up at ipinfo.io for more)
- Data is saved to `responses.jsonl` in the same directory
- Domain attribution uses Referer headers for accurate CDN traffic tracking

### Configuration Parameters

#### Basic Settings

```python
OUTPUT_FILE = "responses.jsonl"          # Data output file
ROLLING_SECONDS = 60                     # Time window for display (seconds)
UPDATE_INTERVAL = 16                     # UI update interval (milliseconds)
NUM_LINES = 3                            # Number of lines to display per chart
MAX_RECORDS_PER_IP = 1000                # Maximum records per IP/domain (memory management)
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

#### Utility Functions

##### `extract_domain(url)`
Extracts the primary domain from a URL.

**Parameters**:
- `url` (str): Full URL string

**Returns**: Domain name (str) with "www." prefix removed, or "unknown" on error

**Example**:
```python
extract_domain("https://www.youtube.com/watch?v=xxx")  # Returns: "youtube.com"
extract_domain("https://rr1---sn-juh.googlevideo.com/video")  # Returns: "googlevideo.com"
```

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
Attaches to a Chrome tab for network monitoring with enhanced domain tracking.

**Parameters**:
- `tab`: Chrome tab object from pychrome

**Returns**: None

**Key Internal Handlers**:
- `handle_request_will_be_sent`: **NEW** - Captures request headers including Referer for accurate domain attribution
- `handle_response_received`: Captures response metadata and IP addresses
- `handle_loading_finished`: Calculates bandwidth and saves records with domain information

**Domain Attribution Logic**:
1. **Priority 1**: Extract domain from Referer header (for CDN resources)
2. **Priority 2**: Extract domain from request URL (for direct requests)

**Example Scenarios**:
```python
# YouTube video playback
Request URL: https://rr1---sn-juh-h4hd.googlevideo.com/videoplayback?...
Referer: https://www.youtube.com/watch?v=xxx
→ Attributed to: youtube.com

# Facebook image loading
Request URL: https://scontent.xx.fbcdn.net/v/t1.0-9/image.jpg
Referer: https://www.facebook.com/
→ Attributed to: facebook.com

# Direct website access
Request URL: https://www.google.com/
Referer: (none)
→ Attributed to: google.com
```

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
Enhanced statistics dashboard widget with domain tracking.

**Methods**:
- `init_ui()`: Initializes the panel layout with 6 statistics cards
- `update_stats(current_speed, peak_speed, total_mb, active_ips, active_domains)`: **UPDATED** - Now includes active domains count

**Statistics Displayed**:
1. Current Speed (Mbps)
2. Peak Speed (Mbps)
3. Total Traffic (MB)
4. Active IP (count)
5. **Active Domains** (count) - NEW
6. Monitor Time (HH:MM:SS)

**Customization**:
```python
# Modify statistics in init_ui()
stats = [
    ("key", "Display Name", "Default Value"),
    # Add more statistics here
]
```

##### `NetworkMonitorApp(QtWidgets.QWidget)`
Main application window with dual-chart visualization.

**Key Methods**:

###### `init_ui()`
Initializes the main user interface with dual charts.

**Layout Structure**:
- Top: Title bar with control buttons
- Middle: Statistics panel (6 cards)
- Bottom: **Dual-chart area**
  - **Left Chart**: Traffic by IP/ISP
  - **Right Chart**: Traffic by Domain (NEW)
- Footer: Status label

**Customizable Elements**:
- Window size: `self.setGeometry(100, 100, 1600, 900)` (increased width for dual charts)
- Font family: Modify stylesheet `font-family` property
- Button labels: Change text in QPushButton constructors

###### `update_plot()`
Core update loop - reads data, processes records for both dimensions, and updates dual visualization.

**Process Flow**:
1. Read new records from `OUTPUT_FILE`
2. Parse JSON and store in both `record_data` (IP) and `domain_record_data` (Domain)
3. Calculate top N entries for each dimension
4. Aggregate data per second for both charts
5. Update both chart lines and statistics

**Dual Data Structure**:
```python
# IP dimension
record_data[ip] = deque([{"time": dt, "speed_mbps": x}, ...])

# Domain dimension (NEW)
domain_record_data[domain] = deque([{"time": dt, "speed_mbps": x}, ...])
```

**Performance Tuning**:
```python
# Adjust time window
window_start = now - datetime.timedelta(seconds=ROLLING_SECONDS)

# Modify data aggregation
per_second[t_sec] = max(per_second[t_sec], r["speed_mbps"])  # Use max
# OR
per_second[t_sec] += r["speed_mbps"]  # Use sum
```

###### `update_chart(data_dict, lines, plot, labels, window_start, now, use_isp=True)`
**NEW** - Unified chart update function for both IP and Domain dimensions.

**Parameters**:
- `data_dict`: Record data dictionary (IP or Domain)
- `lines`: Chart line objects
- `plot`: Plot widget
- `labels`: Label tracking list
- `window_start`: Start of time window
- `now`: Current timestamp
- `use_isp`: Boolean flag (True for IP chart with ISP names, False for Domain chart)

**Features**:
- Generic implementation for code reusability
- Automatic Y-axis scaling
- Time window synchronization across charts

###### `toggle_monitoring()`
Pauses/resumes monitoring without closing Chrome.

###### `clear_data()`
Clears all records (both IP and Domain data) with confirmation dialog.

###### `export_full_plot()`
**ENHANCED** - Exports complete traffic history as dual-chart matplotlib figure.

**Output Format**:
- **Top subplot**: Traffic by IP/ISP
- **Bottom subplot**: Traffic by Domain
- Combined into single PNG file

**Customization**:
```python
# Modify chart style
plt.style.use('dark_background')  # Change to 'seaborn', 'ggplot', etc.

# Adjust figure size
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))  # Width, Height in inches

# Change export DPI
plt.savefig(filename, dpi=150, facecolor='#1E1E1E')  # Increase for higher quality
```

###### `plot_export_chart(data_dict, ax, title, use_isp=True)`
**NEW** - Helper function for plotting export charts.

**Parameters**:
- `data_dict`: Record data dictionary
- `ax`: Matplotlib axes object
- `title`: Chart title
- `use_isp`: Boolean flag for label formatting

### Data Structure

#### JSON Record Format (Enhanced)
```json
{
  "time": "14:30:45",
  "size_kb": 1024.5,
  "duration_s": 0.152,
  "speed_mbps": 53.8,
  "ip": "192.168.1.100",
  "domain": "youtube.com",
  "as": "Google LLC"
}
```

**NEW Fields**:
- `domain`: Attributed domain name (from Referer or URL)
- `as`: ISP organization name

#### In-Memory Data Structure
```python
# IP dimension
record_data = {
    "192.168.1.100": deque([
        {"time": datetime.datetime(...), "speed_mbps": 53.8},
        {"time": datetime.datetime(...), "speed_mbps": 61.2},
    ], maxlen=1000)
}

# Domain dimension (NEW)
domain_record_data = {
    "youtube.com": deque([
        {"time": datetime.datetime(...), "speed_mbps": 120.5},
        {"time": datetime.datetime(...), "speed_mbps": 98.3},
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

本應用程式透過連接 Chrome 的除錯介面來監控網路流量，擷取封包資料、計算頻寬使用情況，並以雙維度（IP/ISP 與網域）即時流量曲線顯示。使用 **Referer 標頭**準確地將 CDN 流量歸屬至來源網站。


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
3. **查看統計**：雙圖表即時顯示（左：IP/ISP，右：域名）
4. **暫停/繼續**：點擊「Pause」按鈕凍結顯示
5. **匯出資料**：點擊「Export Plot」儲存包含兩個維度的完整流量歷史
6. **清除資料**：點擊「Clear Data」重置所有記錄

#### 重要注意事項

- **關鍵**：僅監控自動啟動的 Chrome 視窗中的流量
- 監控會擷取大於 10KB 的網路請求
- ISP 查詢每個 IP 每天限制 1000 次請求（在 ipinfo.io 註冊可獲得更多次數）
- 資料儲存在同目錄下的 `responses.jsonl` 檔案中
- 域名歸屬使用 Referer 標頭來精確追蹤 CDN 流量

### 設定參數

#### 基本設定

```python
OUTPUT_FILE = "responses.jsonl"          # 資料輸出檔案
ROLLING_SECONDS = 60                     # 顯示時間窗口（秒）
UPDATE_INTERVAL = 16                     # UI 更新間隔（毫秒）
NUM_LINES = 3                            # 每個圖表顯示的線條數量
MAX_RECORDS_PER_IP = 1000                # 每個 IP/域名的最大記錄數（記憶體管理）
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

#### 實用工具函數

##### `extract_domain(url)`
從 URL 提取主域名。

**參數**：
- `url` (str)：完整 URL 字串

**返回值**：移除 "www." 前綴的域名（str），錯誤時返回 "unknown"

**範例**：
```python
extract_domain("https://www.youtube.com/watch?v=xxx")  # 返回：youtube.com
extract_domain("https://rr1---sn-juh.googlevideo.com/video")  # 返回：googlevideo.com
```

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
附加到 Chrome 分頁進行增強域名追蹤的網路監控。

**參數**：
- `tab`：來自 pychrome 的 Chrome 分頁物件

**返回值**：無

**關鍵內部處理器**：
- `handle_request_will_be_sent`：**新增** - 擷取包含 Referer 的請求標頭以進行精確域名歸屬
- `handle_response_received`：擷取回應元資料和 IP 位址
- `handle_loading_finished`：計算頻寬並儲存包含域名資訊的記錄

**域名歸屬邏輯**：
1. **優先級 1**：從 Referer 標頭提取域名（用於 CDN 資源）
2. **優先級 2**：從請求 URL 提取域名（用於直接請求）

**範例情境**：
```python
# YouTube 影片播放
請求 URL: https://rr1---sn-juh-h4hd.googlevideo.com/videoplayback?...
Referer: https://www.youtube.com/watch?v=xxx
→ 歸屬至：youtube.com

# Facebook 圖片載入
請求 URL: https://scontent.xx.fbcdn.net/v/t1.0-9/image.jpg
Referer: https://www.facebook.com/
→ 歸屬至：facebook.com

# 直接訪問網站
請求 URL: https://www.google.com/
Referer: (無)
→ 歸屬至：google.com
```

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
增強的統計資訊儀表板元件，包含域名追蹤。

**方法**：
- `init_ui()`：初始化包含 6 個統計卡片的面板佈局
- `update_stats(current_speed, peak_speed, total_mb, active_ips, active_domains)`：**已更新** - 現在包含活躍域名計數

**顯示的統計資訊**：
1. Current Speed（當前速度）(Mbps)
2. Peak Speed（峰值速度）(Mbps)
3. Total Traffic（總流量）(MB)
4. Active IP（活躍 IP）(數量)
5. **Active Domains**（活躍域名）(數量) - 新增
6. Monitor Time（監控時間）(HH:MM:SS)

**客製化**：
```python
# 在 init_ui() 中修改統計項目
stats = [
    ("key", "顯示名稱", "預設值"),
    # 在此新增更多統計項目
]
```

##### `NetworkMonitorApp(QtWidgets.QWidget)`
具有雙圖表視覺化的主應用程式視窗。

**主要方法**：

###### `init_ui()`
初始化包含雙圖表的主使用者介面。

**佈局結構**：
- 頂部：帶控制按鈕的標題列
- 中間：統計面板（6 個卡片）
- 底部：**雙圖表區域**
  - **左側圖表**：依 IP/ISP 的流量
  - **右側圖表**：依域名的流量（新增）
- 頁尾：狀態標籤

**可自訂元素**：
- 視窗大小：`self.setGeometry(100, 100, 1600, 900)`（為雙圖表增加寬度）
- 字型家族：修改樣式表中的 `font-family` 屬性
- 按鈕標籤：變更 QPushButton 建構函數中的文字

###### `update_plot()`
核心更新迴圈 - 讀取資料、處理兩個維度的記錄並更新雙視覺化。

**處理流程**：
1. 從 `OUTPUT_FILE` 讀取新記錄
2. 解析 JSON 並儲存到 `record_data`（IP）和 `domain_record_data`（域名）
3. 計算每個維度的前 N 個條目
4. 為兩個圖表每秒聚合資料
5. 更新兩個圖表線條和統計資訊

**雙資料結構**：
```python
# IP 維度
record_data[ip] = deque([{"time": dt, "speed_mbps": x}, ...])

# 域名維度（新增）
domain_record_data[domain] = deque([{"time": dt, "speed_mbps": x}, ...])
```

**效能調整**：
```python
# 調整時間窗口
window_start = now - datetime.timedelta(seconds=ROLLING_SECONDS)

# 修改資料聚合方式
per_second[t_sec] = max(per_second[t_sec], r["speed_mbps"])  # 使用最大值
# 或者
per_second[t_sec] += r["speed_mbps"]  # 使用總和
```

###### `update_chart(data_dict, lines, plot, labels, window_start, now, use_isp=True)`
**新增** - 用於 IP 和域名兩個維度的統一圖表更新函數。

**參數**：
- `data_dict`：記錄資料字典（IP 或域名）
- `lines`：圖表線條物件
- `plot`：繪圖元件
- `labels`：標籤追蹤列表
- `window_start`：時間窗口開始
- `now`：當前時間戳記
- `use_isp`：布林標誌（True 表示帶 ISP 名稱的 IP 圖表，False 表示域名圖表）

**特性**：
- 通用實作以實現程式碼重用
- 自動 Y 軸縮放
- 跨圖表的時間窗口同步

###### `toggle_monitoring()`
暫停/繼續監控而不關閉 Chrome。

###### `clear_data()`
清除所有記錄（IP 和域名資料）（附確認對話框）。

###### `export_full_plot()`
**增強** - 將完整流量歷史匯出為雙圖表 matplotlib 圖形。

**輸出格式**：
- **上方子圖**：依 IP/ISP 的流量
- **下方子圖**：依域名的流量
- 合併為單一 PNG 檔案

**客製化**：
```python
# 修改圖表樣式
plt.style.use('dark_background')  # 變更為 'seaborn'、'ggplot' 等

# 調整圖形大小
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))  # 寬度、高度（英吋）

# 變更匯出 DPI
plt.savefig(filename, dpi=150, facecolor='#1E1E1E')  # 提高以獲得更高品質
```

###### `plot_export_chart(data_dict, ax, title, use_isp=True)`
**新增** - 用於繪製匯出圖表的輔助函數。

**參數**：
- `data_dict`：記錄資料字典
- `ax`：Matplotlib 軸物件
- `title`：圖表標題
- `use_isp`：標籤格式化的布林標誌

### 資料結構

#### JSON 記錄格式（增強）
```json
{
  "time": "14:30:45",
  "size_kb": 1024.5,
  "duration_s": 0.152,
  "speed_mbps": 53.8,
  "ip": "192.168.1.100",
  "domain": "youtube.com",
  "as": "Google LLC"
}
```

**新增欄位**：
- `domain`：歸屬的域名（來自 Referer 或 URL）
- `as`：ISP 組織名稱

#### 記憶體內資料結構
```python
# IP 維度
record_data = {
    "192.168.1.100": deque([
        {"time": datetime.datetime(...), "speed_mbps": 53.8},
        {"time": datetime.datetime(...), "speed_mbps": 61.2},
    ], maxlen=1000)
}

# 域名維度（新增）
domain_record_data = {
    "youtube.com": deque([
        {"time": datetime.datetime(...), "speed_mbps": 120.5},
        {"time": datetime.datetime(...), "speed_mbps": 98.3},
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