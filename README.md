# WQ 文件 · 简体中文版（WQFiles zh-Hans）

[WQFiles](https://github.com/kolbicz/WQFiles) 的简体中文构建，基于官方 **v0.7**。
只改界面文案，不动任何功能逻辑。

> **下载 IPA**：进 [Actions](../../actions/workflows/build-zh-hans.yml) → 选最新一次成功的运行
> → 页面底部 **Artifacts** → `WQFiles-zh-Hans-IPA`。artifacts 保留 90 天。

最新构建（#5，commit `eeed650`）：

| 项 | 值 |
|---|---|
| 文件 | `WQFiles-zh-Hans.ipa` |
| 大小 | 297,760 字节 |
| SHA-256 | `d44ca5754802392615b775e2332f4f827a9d7a97ed8b4baec028f957cbd3d7cf` |
| 版本 | 0.7 (build 26) |
| 最低系统 | iOS 26.0 |
| 编译环境 | macOS 26 runner · Xcode 26.6 · iOS 26 SDK |

## 这是什么

WQ 文件是一个免越狱的 iOS 文件管理器：靠 worse_query 沙盒技术访问其他 App 的数据容器，
可以浏览 App 数据目录、备份/恢复 App 数据、清缓存、编辑 plist、改文件字节。

本仓库只做汉化，功能与官方 v0.7 完全一致。

## 自己构建

仓库已配置 GitHub Actions，**push 到 main 会自动构建**，也可以手动触发：

Actions → Build WQFiles zh-Hans IPA → Run workflow（可指定上游 ref）

工作流做的事：

1. 拉取 `kolbicz/WQFiles` 指定 ref 的源码
2. 跑 `localize.py` 套用 628 条译文
3. 跑 `postlocalize.py` 处理「同一串在标题处译、比较处不译」
4. 跑 `check_zh.py` 闸门（误伤逻辑串 / 语法破损 / 清单键丢失 → 直接失败）
5. `build.sh` 用 Xcode 的 iPhoneOS SDK 编译 + ad-hoc 签名
6. 校验签名与 App Group，算 SHA-256，上传 artifact

## 本地构建（macOS）

```bash
xcode-select --install
git clone https://github.com/kolbicz/WQFiles.git source
cp -r src/* source/
cd source && chmod +x build.sh && ./build.sh
```

## 从官方源码自己汉化

```bash
git clone https://github.com/kolbicz/WQFiles.git source
python3 localize.py --src source --catalog zh-Hans.json --write
python3 postlocalize.py --src source
python3 check_zh.py --src source
cd source && ./build.sh
```

## 安装

产出是 **ad-hoc 签名**，必须重新签名才能装，且签名工具必须保留 App Group：

- **AltStore / SideStore**：会自动创建 App Group，最省事
- **Feather / ESign + p12**：描述文件必须显式包含 App Group。
  通配符描述文件给不了，会报 entitlement 错误，或装上后 Log 首行显示「无应用组」，功能全废

首次启动看 **工具 → 日志**，第一行会写实际拿到的应用组。

## 系统要求

- iOS **26.0 – 26.7.2** 或 **iOS 27**
- 必须重新签名并保留 App Group
- iOS 26 上「系统数据」「系统共享组」不可达，「系统后台服务」首次扫描可能耗时近一小时（官方行为）

## 翻译边界

**翻译**：所有用户可见文案——标题、按钮、提示框、错误信息、进度文字、空状态。

**刻意不译**（译了功能会坏）：

| 类别 | 例子 | 原因 |
|---|---|---|
| 参与比较的字符串 | `Backups`、`AppBackups`、`Application`、`Active`、`Committed` | 是逻辑分支判据 |
| 备份清单键 | `Complete`、`Parts`、`PartHashes`、`Sequence` | 写进磁盘 plist，译了旧备份读不出来 |
| 路径片段 | `/private/var/mobile/...`、`.app` | 系统路径 |
| Bundle ID / 图标名 | `com.apple.*`、`CFBundleIcons` | 系统标识符 |
| 日志前缀 | `scan:`、`names:`、`grant:` | 上游排查靠 grep 这些 |
| 格式模板 | `yyyy-MM-dd HH.mm.ss`、`en_US_POSIX` | 格式化参数 |
| Apple 官方名称 | App Store、Apple Pay、iPhone 17 Pro | 专有名词 |

规则写在 `localize.py` 的 `LOGIC_LITERALS` / `MANIFEST_KEYS` / `KEEP` 里。

## 文件说明

| 文件 | 用途 |
|---|---|
| `src/` | 已汉化的完整源码树，可直接编译 |
| `zh-Hans.json` | 译文表，628 条 |
| `localize.py` | 汉化工具（词法扫描 / 替换 / 格式符校验 / 复数处理） |
| `postlocalize.py` | 上下文精修（同一串在标题处译、比较处不译） |
| `check_zh.py` | 自检闸门，CI 与本地都能跑 |
| `make_review.py` | 生成译文审校表 |
| `译文审校表.md` | 785 条译文按 9 个界面模块分组，带源码行号 |
| `术语对照表.md` | 21 组术语的统一用词 |
| `.github/workflows/build-zh-hans.yml` | CI 构建流水线 |

## 改译文

编辑 `zh-Hans.json`，然后重建源码树：

```bash
python3 localize.py --src src --catalog zh-Hans.json --write
python3 postlocalize.py --src src
python3 check_zh.py --src src     # 不通过就别提交
```

**不要只改 JSON 不重建 `src/`**，否则两边脱节，打出来的包还是旧译文。

## 许可

上游 GPL-3.0-or-later，本汉化同样遵循 GPL-3.0-or-later。
原项目版权归 Christoph Kolbicz；沙盒技术 worse_query 由 Taj C（@forcequitOS）研究；
容器枚举参考 murk-sus 的 KAMUI。
