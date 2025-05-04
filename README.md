# AI Tutorial Generator

**Automatically generate a step-by-step Markdown tutorial from any PDF or web page.**  
Powered by a modular “Agent” architecture (beeai-framework + Docling + Ollama/Granite models).


## Introduction

The **AI Tutorial Generator** transforms any source document—be it a PDF report, academic paper, or web page—into a polished, step-by-step tutorial in Markdown format. Under the hood, it uses a **multi-agent system** built on the [beeai-framework], a lightweight Python library for defining “Agents” plus [Docling] for robust document parsing, and Granite models (via Ollama or Replicate).

### What is the beeai-framework?

[`beeai-framework`] is a Python toolkit designed to simplify agentic architectures:

- **Agent**: A class with a single `run()` method that takes inputs and returns standardized `Document` objects.
- **Document**: A container for `page_content` + `metadata`, passed between agents.
- **Workflow**: Orchestrates a sequence of agents, handling errors and data flow.
- **ChatModel**: Integrates large language model calls (Ollama, Watsonx.ai) with prompt templates.

This pattern keeps logic modular, testable, and extensible.



## Architecture & Flow

Below is a high-level Mermaid diagram of the six-step workflow:

```mermaid
flowchart TD
    A["Start: Source URI"] --> B[SourceRetrieverAgent]
    B --> C[DocumentParserAgent]
    C --> D[ContentAnalyzerAgent]
    D --> E[TutorialStructureAgent]
    E --> F[MarkdownGenerationAgent]
    F --> G[ReviewerRefinerAgent]
    G --> H[Final Markdown Tutorial]

    subgraph RetrievalParsing["Retrieval & Parsing"]
        B
        C
    end

    subgraph AnalysisStructuring["Analysis & Structuring"]
        D
        E
    end

    subgraph GenerationRefinement["Generation & Refinement"]
        F
        G
    end

    style RetrievalParsing fill:#eef,stroke:#aac,stroke-width:1px
    style AnalysisStructuring fill:#efe,stroke:#aca,stroke-width:1px
    style GenerationRefinement fill:#fee,stroke:#caa,stroke-width:1px

````



## ✨ Features

* **SourceRetrieverAgent**
  Fetches raw PDF bytes or HTML text from a URL or local file.

* **DocumentParserAgent**
  Leverages **Docling** to extract text blocks, images, tables, and code snippets.

* **ContentAnalyzerAgent**
  Classifies each block’s role (introduction, step, concept, etc.) using Granite via Ollama or Replicate, and generates image captions.

* **TutorialStructureAgent**
  Crafts a clean Markdown outline (Introduction, Prerequisites, Steps, Examples, Conclusion).

* **MarkdownGenerationAgent**
  Fills the outline with text, code fences, and image descriptions to produce a complete tutorial.

* **ReviewerRefinerAgent** (optional)
  Performs a final pass to polish language, fix formatting, and ensure clarity.

* **CLI & Web UI**

  * **CLI**: Generate tutorials in your terminal (`python src/main.py …`).
  * **Web UI**: A 4-step Flask wizard (`python app.py`).



## ⚙️ Prerequisites

* **Python 3.12+**
* **beeai-framework**
* **Docling**
* **Ollama** (or **Replicate API token** for live Granite models)
* **Flask**

Set environment variables:

```bash
export USE_MOCKS=false                    # true to force mock mode
export DOCLING_OUTPUT_DIR=./docling_output
export MODEL_NAME=ollama:granite3.1-dense:8b
```

For Ollama local inference:

```bash
brew install ollama
ollama pull granite3.1-dense:8b
ollama pull granite-vision-3.2-2b
```


## 📥 Installation

1. **Clone**

   ```bash
   git clone https://github.com/your-org/ai-tutorial-generator.git
   cd ai-tutorial-generator
   ```

2. **Virtualenv**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Start Ollama**

   ```bash
   ollama serve &
   ```


## 🎯 Usage

### CLI Mode

```bash
python src/main.py https://example.com/guide.pdf > tutorial.md
```

### Web UI Mode

```bash
python app.py
# → Open http://0.0.0.0:8080 in your browser
```

Follow the 4-step wizard to input source, preview outline, review draft, and download final Markdown.

---

## 📝 Example

**CLI**

```bash
python src/main.py intro-to-ml.pdf > ml-tutorial.md
```

**Web**

```bash
python app.py
# visit http://localhost:8080
```



## 📂 Project Tree

```
ai-tutorial-generator/
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
├── app.py
├── templates/
│   └── wizard.html
├── static/
│   ├── app.js
│   └── style.css
├── src/
│   ├── __main__.py
│   ├── main.py
│   ├── workflows.py
│   └── agents/
│       ├── source_retriever_agent.py
│       ├── document_parser_agent.py
│       ├── content_analyzer_agent.py
│       ├── tutorial_structure_agent.py
│       ├── markdown_generation_agent.py
│       └── reviewer_refiner_agent.py
└── docling_output/
```



## 🛠 Troubleshooting & Tips

* **Mock Mode**: Agents auto‐fall back to mocks if no `REPLICATE_API_TOKEN`.
* **Docling**: Ensure `docling_output` is writable.
* **Ollama**: Increase context size with `--num_ctx` for large docs.
* **Performance**: Large PDFs/images will take longer—consider splitting.


## 🤝 Contributing

Contributions welcome! Fork, branch, PR, and open issues for bugs or features.



Thank you for using **AI Tutorial Generator**!
We hope this multi-agent approach streamlines your tutorial creation.

[beeai-framework]: https://github.com/beeai/beeai-framework
[Docling]: https://github.com/docling/docling