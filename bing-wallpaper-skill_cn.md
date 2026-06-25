# Bing Daily Wallpaper Gallery - Skill v5.8.6

## 概述
自动化 Bing 每日壁纸画廊生成器。从 Bing 官方 API 获取 11 个独立更新市场的壁纸数据，去重后生成自包含 HTML 文件，支持多语言描述和 Did You Know 卡片。

**v5.8.6 核心特性**：
- **语言隔离**：英文 Did You Know 只从英文市场获取，中文"你知道吗"只从 cn.bing.com 获取，严禁跨语言混入
- **分层获取**：国际版（global.bing.com）获取英文内容（主），国内版（cn.bing.com）获取中文内容（补充）
- **全市场遍历**：`fetch_all_descriptions()` 遍历所有 11 个市场的 API 获取描述和 QuickFact
- **浏览器增强**：通过浏览器自动化从 Bing 搜索卡片获取更完整的描述（~1000字符 vs API ~400字符）
- **语言标签修复**：非英文独占壁纸（德/法/意/西/葡/日）显示对应语言标签而非 "English"
- **增量缓存**：JSON 缓存保留历史数据，每次运行只获取 14 天新数据
- **补充版 HTML**：在原版 HTML 基础上生成单独的补充版，不覆盖原版

## API 端点

### 1. Bing Wallpaper Archive API（14天历史 + 市场去重）
```
https://global.bing.com/HPImageArchive.aspx?format=js&n={n}&idx={offset}&mkt={code}&pid=hp&FORM=BEHPTB&ql=6
```
- 返回：title, caption, copyright, urlbase, desc, copyrightlink
- 每个市场调用2次（idx=0 和 idx=7），共 22 次调用

### 2. Bing Model API - Global（英文 + 本地语言描述）
```
https://global.bing.com/hp/api/model?mkt={code}
```
- **关键**：`global.bing.com` 绕过 IP 地理限制，`mkt` 参数生效
- 返回：Description, Headline, Title, QuickFact.MainText, Copyright
- 覆盖：今天 + 7 个预加载项
- **注意**：global.bing.com 的 QuickFact.MainText 通常为空（服务端限制）

### 3. Bing Model API - China（中文描述和你知道吗）
```
https://cn.bing.com/hp/api/model?mkt=zh-CN
```
- 市场由 IP 决定（中国 IP 始终返回 zh-CN），`mkt` 参数被忽略
- 返回中文 Description, QuickFact, Title
- **关键**：cn.bing.com 的 QuickFact.MainText 有完整内容（与 global.bing.com 不同）

## 市场配置（11个市场）

| 市场 | 代码 | 独立更新 | 本地语言 |
|------|------|----------|----------|
| US | en-US | 是（基准） | English |
| UK | en-GB | 否 | English |
| CA | en-CA | 否 | English |
| DE | de-DE | 否 | Deutsch |
| FR | fr-FR | 是 | Français |
| IT | it-IT | 否 | Italiano |
| ES | es-ES | 否 | Español |
| BR | pt-BR | 否 | Português |
| JP | ja-JP | 是 | 日本語 |
| CN | zh-CN | 否 | 中文 |
| IN | en-IN | 否 | English |

## 语言隔离策略

### 英文壁纸（hasEnglish = true）
- **描述（desc）**：只从 ENGLISH_MARKETS（en-US/en-GB/en-CA/en-IN）获取
- **Did You Know（quickFact）**：只从 ENGLISH_MARKETS 获取
- **语言标签**：显示 "English"（蓝色）

### 非英文独占壁纸（hasEnglish = false）
- **描述（desc）**：从 LOCAL_PRIORITY 获取当地语言描述
- **语言标签**：根据 descLang 显示对应语言名（Deutsch/Français/Italiano/Español/Português/日本語）
- **descLang 字段**：记录描述的语言代码（de/fr/it/es/pt/ja）

### 中文内容（所有壁纸）
- **中文描述（descZh）**：只从 cn.bing.com API 获取
- **中文你知道吗（quickFactZh）**：只从 cn.bing.com API 获取
- **语言标签**：显示 "中文"（红色）

### 语言标签渲染逻辑（JavaScript）
```javascript
if (img.hasEnglish) {
    contentHtml += '<div class="lang-label lang-en">English</div><br>';
} else {
    var langMap = {"de":"Deutsch","fr":"Français","it":"Italiano",
                   "es":"Español","pt":"Português","ja":"日本語",
                   "zh":"中文","en":"English"};
    var langName = langMap[img.descLang] || img.descLang || "English";
    contentHtml += '<div class="lang-label lang-local">' + langName + '</div><br>';
}
```

## 浏览器增强描述

### 获取流程
1. 从 HTML 中提取每张壁纸的 `copyrightlink`（Bing 搜索 URL）
2. 通过浏览器自动化访问 `https://www.bing.com{copyrightlink}`
3. 从搜索页面快照中提取 "Featured on Bing" 或 "Today on Bing" 卡片内容
4. 卡片描述通常有 3 段完整内容（~1000字符），比 API 返回的更完整（~400字符）
5. 保存到 `browser_descriptions.json`

### 语言检测
```python
def detect_language(text):
    # 日文：平假名/片假名
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', sample): return "ja"
    # 中文
    if re.search(r'[\u4E00-\u9FFF]', sample): return "zh"
    # 意大利语/葡萄牙语/德语/法语/西班牙语 特征字符检测
    # 默认英文
    if re.match(r'^[A-Za-z]', sample): return "en"
```

### 增强应用规则
- 英文壁纸 + 英文增强描述 → 替换 `desc`（仅当更长时）
- 非英文壁纸 + 英文增强描述 → 替换 `desc`（仅当更长时）
- 非英文壁纸 + 非英文增强描述 → 放入 `localDesc`

## 数据获取流程

### 完整版生成流程（bing_gen_v5.8.6.py）
1. **加载缓存**：读取 `.bing_cache_v586.json`（0 次 API 调用）
2. **获取14天历史**：11 个市场 × 2 次调用 = 22 次 API 调用
3. **获取描述**：11 个市场 model API + 1 次 cn.bing.com = 12 次调用
4. **合并缓存**：补充缺失字段（0 次 API 调用）
5. **保存缓存**：写入更新后的缓存
6. **应用浏览器增强**：加载 `browser_descriptions.json` 替换不完整描述
7. **生成 HTML**：基于 v5.3 模板替换 ALL_IMAGES 和 ALL_MARKETS 数据
8. **总计**：~34 次 API 调用

### 补充版生成流程
1. 复制原版 HTML 作为基础
2. 从 cn.bing.com API 获取最新中文内容
3. 加载浏览器提取的描述和中文补充
4. 质量过滤：跳过百度百科等非壁纸标准描述
5. 将补充内容注入 HTML 数据中
6. 保存为单独的补充版 HTML（不覆盖原版）

## 校对验证流程

### 校对项
1. **壁纸数量**：确认 30 张壁纸全部存在
2. **描述完整性**：检查 desc 字段是否为空或被截断（<200字符视为不完整）
3. **Did You Know**：检查 quickFact 和 quickFactZh 是否存在
4. **语言标签**：确认非英文壁纸不显示 "English" 标签
5. **页面可打开**：HTML 文件大小 >50KB，无 JavaScript 语法错误

### 校对结果处理
- **无缺漏**：保留备份，次日只需生成补充版 HTML
- **有缺漏**：回到完整版 py 脚本重新生成

## 文件结构

| 文件 | 用途 |
|------|------|
| `/workspace/bing_gen_v5.8.6.py` | 主生成脚本（完整版） |
| `/workspace/bing_gallery_v5.3_backup.html` | HTML 模板（UI 基准） |
| `/workspace/bing_gallery_v5.8.6.html` | 原版输出 HTML |
| `/workspace/bing_gallery_v5.8.6_supplement.html` | 补充版输出 HTML |
| `/workspace/.bing_cache_v586.json` | 增量缓存 |
| `/workspace/browser_descriptions.json` | 浏览器提取的增强描述 |
| `/workspace/cn_supplements.json` | 中文补充数据 |
| `/workspace/backup_v5.8.6/` | 完整备份目录 |

## 已知限制

1. **global.bing.com QuickFact 为空**：服务端限制，请求头修改无法解决
2. **cn.bing.com 中文覆盖有限**：只有部分壁纸在 cn.bing.com 有对应内容（~9/30）
3. **cn.bing.com 搜索无卡片**：cn.bing.com 搜索页面不显示壁纸卡片，无法通过搜索补充中文描述
4. **非英文独占壁纸**：部分壁纸（意大利/葡萄牙/日本）可能缺少英文描述

## 版本历史

### v5.8.6: 语言标签修复 + 浏览器增强 + 补充版
- 修复非英文独占壁纸语言标签显示 "English" 的问题
- 浏览器自动化从 Bing 搜索卡片获取完整描述（~1000字符）
- 生成单独的补充版 HTML，不覆盖原版
- 语言检测确保增强描述不会错误替换

### v5.8.5: 语言隔离修复
- quickFact 只从 ENGLISH_MARKETS 获取，不混入其他语言
- desc 增加 has_english 判断，区分英文壁纸和非英文独占壁纸
- 恢复 v5.3 的全市场获取逻辑

### v5.3: 稳定基线
- 增量缓存机制
- 描述补充（短描述自动补充 Title/Headline）
- UI 模板基准
