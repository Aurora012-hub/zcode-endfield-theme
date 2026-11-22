---
name: endfield-theme
description: 终末地工业风格 ZCode 主题页的启动、预览与迭代指南。当用户要求打开/运行/修改/更新 endfield 主题、终末地主题、工业风格主题页,或询问该主题的设计令牌与结构时使用。
---

# ZCode 终末地工业主题 (endfield-theme)

单文件主题页 `theme/index.html` + 本地数据服务 `theme/stats_server.py`(stdlib 实现,无第三方依赖)。
琥珀橙 #ff9e1b × 浅色切角面板 × 警示斜纹 × 双语标注 × 等宽字排印。

## 启动与预览

1. 检查 `http://127.0.0.1:8642/` 是否已在运行(有响应则跳过启动)。
2. 未运行时,在 `theme/` 目录后台执行:`python stats_server.py`(或 `py -3 stats_server.py`)。
   该服务静态托管主题页,并提供 `/api/stats` 实时数据:
   - `gpuTemp` / `gpuName`:nvidia-smi 读取(无 NVIDIA 显卡时为 null)
   - `batteryPercent` / `charging` / `acOnline`:WMI 读取(无电池设备为 null)
   - 结果缓存 2.5s,页面每 3s 拉取一次
3. 用浏览器打开 `http://127.0.0.1:8642/`,体验三阶段:开屏自检 → 按住 1.8s 授权 → 主操作台。

调试钩子:`window.__goto('auth')` / `window.__goto('main')` 可跳过动画直达某阶段(在页面控制台或 evaluate 中调用)。

## 目录结构

```text
theme/index.html       主题页全部内容(样式/脚本内联)
theme/stats_server.py  本地数据服务(端口 8642)
theme/start-theme.cmd  双击启动:起服务并打开浏览器
```

## 设计令牌

工业橙 `--accent:#ff9e1b` / 浅面板 `--panel:#eceae4` / 深面板 `--panel-dark:#22262c`
/ 底黑 `--bg-0:#0b0c0e` / 运行绿 `--ok:#43c268` / 警示黄 `--warn:#ffc53d` / 危险红 `--danger:#e5484d`
警戒模式:`body.alert-mode` 将强调色切换为 `#ff5147`。

## 迭代规则

- 修改主题只编辑 `theme/index.html`;改完把 manifest `version` 与 `marketplace.json` 条目同步 +0.0.1。
- 硬件数据卡片(GPU 温度、能源储备)读 `/api/stats`,不要写死数值;服务不可用时显示 `--`。
- 数据卡片不使用装饰性的假小字标注(历史决策:用户已要求删除)。
