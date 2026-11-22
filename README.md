# ZCode 终末地工业主题 (Endfield Industrial Theme)

参考《明日方舟:终末地》视觉语言制作的 ZCode 主题:琥珀橙 × 浅色切角面板 × 警示斜纹 × 双语标注。

包含三层能力(可独立使用):

1. **主题插件**(`endfield-theme/`)——主题页:六阶段交互开机序列 → 主操作台,概览页实时 GPU 温度/电量
2. **客户端皮肤补丁**(`client-patch/`)——把 ZCode 桌面客户端本体换装:启动动画、对话页面配色、十字准星、右下角硬件 HUD
3. **本地数据服务**——为 HUD/主题页提供 GPU 温度(nvidia-smi)与电池电量(WMI),含 CORS,支持开机自启

## 安装

### A. 主题插件

1. 克隆本仓库(或下载 ZIP 解压)
2. ZCode → 插件市场 → 添加 → 添加插件市场 → 粘贴**本仓库根目录**(含 marketplace.json)
3. 个人 → Endfield Market → 终末地工业主题 → 安装
4. 新任务发送 `/endfield-theme` 即可启动主题页

### B. 客户端皮肤补丁(改 app.asar,风险自负)

> 原理:外科手术式替换 `resources/app.asar` 中 `out/renderer/index.html` 与主样式表,
> 原版清单字节不动;修改前自动备份,失败自动回滚。**应用更新会覆盖补丁,重跑即可。**

1. 关闭 `python -I asar_patch.py "D:\zcode\resources"` 之外的一切(见下),完整退出 ZCode(含托盘)
2. 双击 `client-patch/endfield-apply.cmd` → 自动换包并重启 ZCode
3. 恢复原版:`client-patch/endfield-restore.cmd`

重新打补丁(应用更新后):

```cmd
python -I client-patch/asar_patch.py "D:\zcode\resources"
```

4. 数据服务:`theme/stats_server.py`(仅监听 127.0.0.1:8642),可用
   `theme/start-theme.cmd` 启动;开机自启:在启动文件夹放一个指向
   `pythonw.exe stats_server.py` 的快捷方式(无窗口)

## 交互启动序列

自检 BOOT(2.4s) → 需要访问许可(**GRANT ACCESS**,点击或 Enter/Space) → 身份资料确认 →
读取权限(HEX 数据流) → 圆环核验 → WELCOME → 主界面。
右上 SKIP / Esc 随时跳过;交互阶段 15s 无操作自动跳过。

## 快捷键

| 快捷键 | 功能 |
|---|---|
| Enter / Space | 启动序列:推进当前阶段 |
| Esc | 启动序列:直接进入应用 |
| Ctrl+Alt+X | 显隐对话页 HUD(十字准星 + 硬件状态) |

## 文件结构

```text
marketplace.json              本地/GitHub 市场清单
endfield-theme/               插件源(skills + commands + theme)
client-patch/
  asar_patch.py               app.asar 外科手术补丁器(stdlib 实现,含完整性校验)
  endfield_client_skin/       皮肤源(boot_style.css / boot_loading.html / override.css / hud_block.html)
  endfield-apply.cmd          应用皮肤(等待退出→备份→换包→失败自动回滚)
  endfield-restore.cmd        恢复原版
```

## 兼容性

- 基于 ZCode Desktop 3.18.x / 3.19.x(Electron,app.asar 无 fuse)验证
- 应用大版本更新后内部结构可能变化,asar_patch.py 的断言会拦截并提示
- 仅用于个人美化,题材致敬《明日方舟:终末地》,Fan Work
