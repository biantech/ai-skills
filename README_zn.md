# ai-skills

可重複使用的 AI 程式代理技能集合。每個技能位於獨立目錄，並以 `SKILL.md` 說明觸發條件、工作流程與安全邊界。

## 技能總覽

### 程式碼品質

| 技能 | 簡要說明 |
| --- | --- |
| [karpathy-guidelines](andrej-karpathy-skills/karpathy-guidelines/) | 以簡潔、精準修改和明確假設降低 LLM 程式碼錯誤。 |
| [karpathy-skills-plus](karpathy-skills-plus/) | 以 Karpathy 原則提升程式碼的清晰度與目標導向。 |
| [code-simplifier](code-simplifier/) | 在不改變行為的前提下簡化近期修改的後端程式碼。 |
| [ponytail](ponytail/) | 優先採用能運作的最小方案，避免多餘抽象與依賴。 |

### 除錯、維運與資料

| 技能 | 簡要說明 |
| --- | --- |
| [fact-first-diagnose](fact-first-diagnose/) | 區分程式碼可證明的結論與依賴執行環境的假設。 |
| [minimal-query-planner](minimal-query-planner/) | 規劃具選擇性、有界且唯讀的查詢，控制成本與資料暴露。 |
| [data-knowledge-capture](data-knowledge-capture/) | 保存經過清理、可重用的資料流程、結構、規則與驗證知識。 |
| [db-tools](db-tools/) | Yuanchuan 各服務查詢真實資料時的指定輔助工具。 |
| [azure-appinsights-query](azure-appinsights-query/) | 對指定的 UAT、RC 或 Prod Application Insights 執行有界唯讀 KQL 查詢。 |
| [kuboard-log](kuboard-log/) | 透過 Kuboard 檢視 Kubernetes 工作負載與受限容器日誌。 |
| [gateway-api-debug](gateway-api-debug/) | 驗證閘道路由，並在核准環境執行受限的端到端 API 呼叫。 |
| [jenkins-api-build](jenkins-api-build/) | 檢視、觸發及追蹤設定好的 Jenkins Dev、UAT 與 RC 工作。 |

### 工作流程與開發工具

| 技能 | 簡要說明 |
| --- | --- |
| [riper](riper/) | 供複雜工程任務使用的五階段 RIPER 流程，需明確觸發。 |
| [riper-workflow](riper-workflow/) | 以 Research、Innovate、Plan、Execute、Review 管理複雜工作。 |
| [planning-with-files](planning-with-files/) | 以持久 Markdown 檔案保存多步驟工作的計畫與進度。 |
| [find-skills](find-skills/) | 協助依需求尋找並安裝合適的技能。 |
| [graphify](graphify/) | 從原始碼、文件等建立、查詢、檢視及匯出的本機知識圖譜。 |
| [playwright](playwright/) | 透過 `playwright-cli` 從終端機自動化真實瀏覽器。 |

### 內容與視覺產出

| 技能 | 簡要說明 |
| --- | --- |
| [gaokao-essay-coach](gaokao-essay-coach/) | 以審題、寫作、修改及評分流程輔導高考作文。 |
| [pdf](pdf/) | 讀取、建立及審閱 PDF，並驗證文字與實際版面。 |
| [professional-svg-diagram](professional-svg-diagram/) | 建立適合架構、路線圖及管理報告的可編輯 SVG 圖表。 |
| [hatch-pet](hatch-pet/) | 建立、修復、驗證並封裝 Codex 相容的動畫寵物與精靈圖。 |
| [caveman](caveman/) | 切換為可調整強度的極簡、精煉溝通風格。 |

## 使用方式

將技能目錄安裝或複製到代理的 skills 目錄，再依其 `SKILL.md` 使用。部分技能會在符合條件時自動啟用，部分則需明確提出例如 `$riper` 或 `caveman mode`。使用前請先閱讀技能說明，尤其是涉及即時系統或外部服務的技能。

## 目錄結構

- `SKILL.md`：主要指示與觸發條件。
- `SKILL_zh.md` 或 `skill-zh.md`：可用時提供的中文說明。
- `agents/`、`scripts/`、`references/`、`assets/`、`tests/`：可選的支援資源。

## 授權

請參閱本儲存庫及各技能目錄中的授權檔案。
