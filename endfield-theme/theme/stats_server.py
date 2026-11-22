"""ZCode 终末地工业主题 - 本地数据服务

静态托管主题页(index.html),并提供 /api/stats 实时硬件数据:
  - gpuTemp / gpuName : nvidia-smi 读取 GPU 温度与名称(无显卡时为 null)
  - batteryPercent / charging / discharging / acOnline : WMI 读取电池(无电池时为 null)
结果缓存 2.5 秒,避免每次轮询都拉起子进程。仅监听 127.0.0.1。
"""
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8642

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_lock = threading.Lock()
_cache = {"ts": 0.0, "data": {}}


def _run(cmd, timeout=5):
    """运行外部命令,返回 UTF-8 文本输出;失败返回 None。"""
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout,
                           creationflags=_NO_WINDOW)
        if p.returncode != 0:
            return None
        return p.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return None


def read_gpu():
    """返回 (温度°C, 显卡名称);读取失败返回 (None, None)。"""
    out = _run(["nvidia-smi", "--query-gpu=temperature.gpu,name",
                "--format=csv,noheader,nounits"])
    if not out:
        return None, None
    parts = [x.strip() for x in out.splitlines()[0].split(",")]
    try:
        temp = float(parts[0].replace(",", ".").replace("°C", ""))
    except (ValueError, IndexError):
        return None, None
    name = parts[-1] if len(parts) > 1 else None
    return temp, name


def read_battery():
    """返回电池状态字典;无电池或读取失败返回 None。"""
    ps = (
        "$b=Get-CimInstance Win32_Battery | Select-Object -First 1;"
        "if(-not $b){Write-Output 'none';exit};"
        "$s=Get-CimInstance -Namespace root/wmi -ClassName BatteryStatus "
        "-ErrorAction SilentlyContinue | Select-Object -First 1;"
        "$ch=$false;$dis=$false;$ac=$false;"
        "if($s){$ch=[bool]$s.Charging;$dis=[bool]$s.Discharging;$ac=[bool]$s.PowerOnline}"
        "else{if($b.BatteryStatus -ge 2){$ac=$true}else{$dis=$true}};"
        "Write-Output ('charge={0};charging={1};discharging={2};ac={3}' "
        "-f $b.EstimatedChargeRemaining,$ch,$dis,$ac)"
    )
    out = _run(["powershell", "-NoProfile", "-Command", ps])
    if not out or out == "none":
        return None
    fields = dict(kv.split("=", 1) for kv in out.split(";") if "=" in kv)
    try:
        percent = int(float(fields.get("charge", "0")))
    except ValueError:
        return None
    return {
        "batteryPercent": max(0, min(100, percent)),
        "charging": fields.get("charging") == "True",
        "discharging": fields.get("discharging") == "True",
        "acOnline": fields.get("ac") == "True",
    }


def collect():
    temp, name = read_gpu()
    data = {
        "gpuTemp": temp,
        "gpuName": name,
        "batteryPercent": None,
        "charging": None,
        "discharging": None,
        "acOnline": None,
        "updatedAt": int(time.time() * 1000),
    }
    batt = read_battery()
    if batt:
        data.update(batt)
    return data


def get_stats():
    with _lock:
        now = time.time()
        if now - _cache["ts"] > 2.5 or not _cache["data"]:
            _cache["data"] = collect()
            _cache["ts"] = now
        return _cache["data"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/stats":
            body = json.dumps(get_stats(), ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        # 静态文件(限制在脚本目录内)
        rel = "index.html" if self.path in ("/", "/index.html") else self.path.lstrip("/")
        target = (ROOT / rel.split("?")[0]).resolve()
        try:
            if not str(target).startswith(str(ROOT)) or not target.is_file():
                raise FileNotFoundError(rel)
            body = target.read_bytes()
        except Exception:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }.get(target.suffix, "application/octet-stream")
        self._send(200, body, ctype)

    def log_message(self, fmt, *args):  # 静默访问日志
        pass


def main():
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        print(f"[!] 端口 {PORT} 无法监听({e});可能已有实例在运行。")
        print(f"    直接访问 http://127.0.0.1:{PORT}/ 即可。")
        return
    print(f"ZCODE 主题数据服务已启动 -> http://127.0.0.1:{PORT}/  (Ctrl+C 停止)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")


if __name__ == "__main__":
    main()
