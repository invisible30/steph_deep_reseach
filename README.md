# LangGraph 研究助手

基于 LangGraph 构建的智能研究助手，能够自动将复杂问题拆分为子问题，逐一分析，并生成完整的研究报告。

## 功能特性

- 🔍 **智能问题拆分**：将复杂研究问题自动拆分为 1-3 个关键子问题
- 📊 **深度分析**：对每个子问题进行深入分析，包含背景、关键因素、现状和挑战
- 📝 **报告生成**：将分析结果整合为结构化的研究报告
- 🌊 **流式输出**：支持实时流式输出，提供更好的交互体验（demo1.py）
- 🔐 **环境变量配置**：使用 `.env` 文件管理敏感配置信息

## 项目结构

```
langraph_agent/
├── demo0.py          # 基础版本（非流式输出）
├── demo1.py          # 流式输出版本（推荐）
├── requirements.txt  # 项目依赖
├── .env_example      # 环境变量模板
└── README.md         # 项目说明文档
```

## 工作流程

项目使用 LangGraph 构建了一个三阶段的研究工作流：

```
用户问题 → [plan_node] → [research_node] → [report_node] → 最终报告
```

1. **规划阶段 (plan_node)**：根据用户问题生成 1-3 个研究子问题
2. **研究阶段 (research_node)**：对每个子问题进行深入分析
3. **报告阶段 (report_node)**：整合所有分析结果，生成完整报告

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd langraph_agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板文件：

```bash
cp .env_example .env
```

编辑 `.env` 文件，填入你的 DeepSeek API 配置：

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_CHAT_MODEL=deepseek-chat
```

**注意**：你需要从 [DeepSeek](https://www.deepseek.com/) 获取 API Key。

## 使用方法

### 基础版本 (demo0.py)

使用 `invoke` 方法，一次性获取完整结果：

```bash
python demo0.py
```

### 流式输出版本 (demo1.py) - 推荐

使用 `stream` 方法，实时查看生成过程：

```bash
python demo1.py
```

流式输出版本的优势：
- ✅ 实时显示生成内容，体验更好
- ✅ 可以及时了解进度
- ✅ 所有节点（plan、research、report）都支持流式输出

## 代码示例

### 修改研究问题

在代码中修改 `user_question` 变量：

```python
user_question = "请帮我系统分析一下：未来 5 年中国大模型产业的发展机会和挑战。"
```

### 自定义工作流

你可以根据需要修改节点逻辑，例如：

- 修改 `plan_node` 中的提示词来改变问题拆分策略
- 调整 `research_node` 中的分析深度和角度
- 自定义 `report_node` 中的报告格式和结构

## 依赖说明

- `langchain`: LangChain 核心库
- `langchain-openai`: LangChain OpenAI 集成
- `langgraph`: LangGraph 工作流构建库
- `python-dotenv`: 环境变量管理
- `pydantic`: 数据验证和结构化输出

## 版本说明

- **demo0.py**: 基础版本，使用 `invoke` 方法，适合快速测试
- **demo1.py**: 流式输出版本，所有节点支持实时输出，推荐使用

## 更新日志

### v1.0.0 - 2025-11-23

首次发布：实现三阶段研究工作流（规划→研究→报告），支持流式输出和环境变量配置。

## 许可证

本项目仅供学习和研究使用。

## 贡献

欢迎提交 Issue 和 Pull Request！

