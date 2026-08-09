# document-write — 编写结构化文档

## When to Use

编写产品/技术类文档，包括但不限于：
- 产品需求文档 (PRD) — 做什么、为什么
- 产品设计文档 — 用户看到什么、怎么交互
- 技术需求文档 (TRD) — 技术约束、架构模式
- 技术设计文档 — 代码怎么实现

## Four-Document Pattern

For feature-level work, the user prefers a **four-document split** (an evolution of the original PRD+TRD pair):

| Doc | Content | Audience |
|-----|---------|----------|
| **产品需求** (PRD) | 功能描述、用户故事、优先级、需求来源 | 产品/业务 |
| **产品设计** | 布局图（ASCII）、交互流程、视觉规范、颜色方案、组件状态 | 设计师/前端 |
| **技术需求** (TRD) | 架构模式、数据模型、状态管理、API 定义、技术约束 | 后端/架构 |
| **技术设计** | 组件结构、代码实现细节、CSS 模式、已知问题清单 | 开发实施 |

### Relationships

```
产品需求  ──说明→  产品设计
   │                    │
   解释"为什么"       解释"怎么用"
   │                    │
   ▼                    ▼
技术需求  ──约束→  技术设计
                    （具体实现）
```

### File Naming

Project-level naming convention:
```
docs/
├── product-requirements.md              ← 产品需求 (PRD)
├── sales-product-design.md              ← 产品设计
├── technical-requirements.md            ← 技术需求 (TRD)
└── sales-technical-design.md            ← 技术设计
```

For domain-specific modules, prefix with module name: `sales-*`, `product-*`, etc.

### Versioning

Each doc should have a header block:
```markdown
> **版本:** v0.1
> **状态:** 前端已实现（Mock 数据）
> **最后修改:** 2026-06-04
```

## Layout Visualization

For UI/UX documents, use ASCII-art tree diagrams to show layout structure. Use Unicode box-drawing characters for column layouts:

```
┌─────────────────────┬──────────────────────────┐
│  Left (2/3)         │  Right (1/3)             │
│                     │  ┌─ Panel A (2/3) ─────┐ │
│  Content here       │  │  ...                │ │
│                     │  └─────────────────────┘ │
│                     │  ┌─ Panel B (1/3) ─────┐ │
│                     │  │  ...                │ │
│                     │  └─────────────────────┘ │
└─────────────────────┴──────────────────────────┘
```

For tighter representations, use ASCII tree diagrams:

```
└─ order-left (flex column)
   ├─ order-top-half (flex:1)
   │  ├─ section-title
   │  ├─ search input
   │  └─ product-list (flex:1, scroll)
   └─ order-bottom-half (flex:1, border-top)
      ├─ section-title
      └─ selected-list (flex:1, scroll)
```

## Standard Tables

Use pipe tables in the following standardized formats:

### Component/Property Specs
```markdown
| 元素 | 字号 | 粗细 | 圆角 |
|------|------|------|------|
| 面板头部 | 13px | 600 | — |
| 建议标签 | 10px | 600 | 4px |
```

### Color/Variable Specs
```markdown
| 用途 | CSS 变量 / 值 | 说明 |
|------|--------------|------|
| 背景（画布） | `var(--chakra-colors-bg-canvas, #fff)` | 纯白底 |
| 文字（默认） | `var(--chakra-colors-fg-default, #1a202c)` | 正文 |
```

### API Endpoints
```markdown
| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/sales/leads` | 潜客列表 |
```

### Data Models
```markdown
| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键 |
```

## Integration with software-dev Composite

The `document-write` operation appears in the `software-dev` composite pattern at step 2:

```
0. [git] Pre-Change Sync
1. info-search    → 调研现有方案
2. document-write → 写 PRD/TRD + 产品设计/技术设计
3. code-write     → 实现（TDD）
4. code-review    → 审查
5. [git] Post-Change Workflow
```

For feature work that's already implemented (docs-as-built, not docs-as-spec), write all four docs together to capture the complete design intent for future maintenance.

## Functional Semantics Requirement

**Every element described in a document must include its functional semantics** — the purpose, intent, and behavior, not just a label or position. This ensures the doc is usable for future reference and verification, not just a build checklist.

### What to include per element type

| Element type | Must include | Good example | Poor example |
|-------------|-------------|-------------|-------------|
| **Button** | What happens on click, what triggers it, what outcome for user | "🔍预览 — 根据当前已选产品动态生成订单详情+收款码组合图片并在浮层展示。用于让销售在发送前确认内容排版和金额正确。" | "预览按钮，弹出浮层" |
| **Tab / Sub-tab** | What content, when visible, what user goal | "AI对话 — 三栏布局：左侧聊天界面（销售↔AI交流），右侧历史记录（按渠道分组）+ AI分析建议。用于快速记录客户跟进、查看历史对话。" | "AI对话 tab" |
| **Display area / panel** | What data, what user can do, why it exists | "收款码下方独立操作卡片：包含4个操作按钮，用于对已生成的订单图片进行预览确认、发送给客户、复制到剪贴板或下载保存。" | "收款码下方有操作按钮" |
| **Interaction** | Full cause-effect chain: user action → system action → user sees | "点击待办事项 → 系统通过openLead将该潜客加入已打开列表，setActiveView切换到潜客管理或客户管理，右侧详情面板同步打开。" | "点击待办跳转到详情" |
| **Permission / visibility rule** | Who can see it, when it appears, when hidden | "数据显示子tab — 仅role===admin的销售员可见。非管理员看不到该tab按钮，也不影响其他视图。" | "管理员可见" |

### Why it matters
1. **Future verification**: A new developer (or the same agent in a future session) should understand what a feature is supposed to DO, not just where it RENDERS.
2. **Cross-reference with implementation**: Detailed semantics make it possible to detect drift between spec and code. "预览弹出浮层" vs "预览动态生成图片并弹窗展示" — the latter is testable, the former is vague.
3. **Design iteration**: When the user says "the meaning of this button should be clearer", the doc should already contain the semantic description so the conversation starts from a shared understanding.

### Integration into the workflow

When writing or updating any of the four docs:
1. For every new button, tab, panel, or interaction being described, write its functional semantics in the same pass
2. When reading an existing doc, note where semantic descriptions are missing — these become qualified items for the "待完善事项" table
3. Do NOT defer semantics to a later cleanup step — the doc is not complete until every user-facing element has a "why" or "what happens" description

## Cross-Referencing with Session History

When writing "as-built" docs for work already implemented, use the `conversation-message-list` skill (if available) to review the actual conversation and extract the precise set of changes:

```bash
# Get the session ID for the relevant conversation
hermes sessions list

# Show compact Q&A history (no tool calls)
python3 scripts/list-messages.py <session_id>
```

This gives a tool-call-free list of every user question and final answer, which maps directly to feature requirements and design decisions.

## Pitfalls

| Pitfall | Correction |
|---------|------------|
| Writing only PRD without design/tech docs | Split into all four to cover product + implementation perspectives |
| ASCII diagrams with ambiguous proportion | Mark flex ratios explicitly (`flex: 2` / `flex: 1`) in the diagram caption |
| Ignoring user feedback-coupling | Use feedback-station skill (if available) to cross-reference doc sections with user feedback IDs |
| Doc status unchanged after implementation | Update status from "需求讨论中" to actual development phase |
| No known-issues section in tech design | Always include a backlog/Known Issues table to track gaps |
| Overwriting existing PRD structure | Read existing doc first, then append/update sections — don't rewrite from scratch |
| Writing docs from memory instead of session replay | Use `conversation-message-list` skill (if available) to re-read the actual conversation for accurate change scope |
| Forgetting to update sibling docs | When any one doc changes, check and update all four — they form a coherent set |
