# ✨ Markdown Magic Demo

Phase 8.3 - Enhanced Markdown Preview

## 🧮 LaTeX Math Support

### Inline Math

The famous equation $E = mc^2$ changed physics forever.

In calculus, we define the derivative as $f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$.

### Block Math

The Schrödinger equation:

$$i\hbar\frac{\partial}{\partial t}\Psi(\mathbf{r},t) = \hat{H}\Psi(\mathbf{r},t)$$

The quadratic formula:

$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$

Matrix multiplication:

$$\begin{pmatrix} a & b \\ c & d \end{pmatrix} \begin{pmatrix} e \\ f \end{pmatrix} = \begin{pmatrix} ae + bf \\ ce + df \end{pmatrix}$$

---

## 📊 Mermaid Diagrams

### Flowchart

```mermaid
flowchart TD
    A[Start] --> B{Is it working?}
    B -->|Yes| C[Great!]
    B -->|No| D[Debug]
    D --> B
    C --> E[Deploy]
    E --> F[🚀 Success!]
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant LSP

    User->>Frontend: Open Python file
    Frontend->>API: GET /workspace/file
    API-->>Frontend: File content
    Frontend->>LSP: Initialize server
    LSP-->>Frontend: Capabilities
    User->>Frontend: Type "import sys"
    Frontend->>LSP: Get completions
    LSP-->>Frontend: [sys, system, ...]
    Frontend->>User: Show autocomplete
```

### Class Diagram

```mermaid
classDiagram
    class LSPManager {
        +servers: Dict
        +get_server(project_id, language)
        +initialize_server()
        +shutdown_server()
    }

    class BaseLSPServer {
        +workspace_path: Path
        +initialized: bool
        +get_completions()
        +get_diagnostics()
        +get_hover()
    }

    class PythonPylspServer {
        +wrapper: PylspWrapper
        +get_completions()
        +get_diagnostics()
    }

    LSPManager --> BaseLSPServer
    BaseLSPServer <|-- PythonPylspServer
```

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Loading: Open file
    Loading --> Ready: File loaded
    Ready --> Editing: User types
    Editing --> Saving: Ctrl+S
    Saving --> Ready: Saved
    Ready --> [*]: Close file
```

### Gantt Chart

```mermaid
gantt
    title Phase 8 Implementation
    dateFormat  YYYY-MM-DD
    section LSP
    Python LSP          :done, lsp1, 2025-12-30, 1d
    Plugin discovery    :done, lsp2, after lsp1, 1d
    section Agent
    Agent Panel         :done, agent1, 2025-12-30, 1d
    Context injection   :done, agent2, after agent1, 1d
    section Editor Modes
    Markdown Enhanced   :active, md1, 2025-12-31, 1d
    Python Dev Mode     :py1, after md1, 2d
    SQL Query Mode      :sql1, after py1, 1d
```

### Pie Chart

```mermaid
pie title Phase 8 Progress
    "LSP Integration" : 100
    "AI Agent" : 100
    "Editor Modes" : 40
    "Plugin System" : 0
```

---

## 📝 Callouts

> [!NOTE]
> This is a helpful note for the reader.

> [!TIP]
> Pro tip: Use mermaid diagrams to visualize your architecture!

> [!WARNING]
> Make sure to validate user input before processing.

> [!CAUTION]
> This operation cannot be undone!

> [!IMPORTANT]
> Remember to commit your changes regularly.

---

## ✅ Task Lists

- [x] Implement LSP Integration
- [x] Add AI Agent Panel
- [x] Create Markdown Enhanced
- [ ] Add Python Dev Mode
- [ ] Add SQL Query Mode
- [ ] Implement Plugin System

---

## 📋 Tables

| Feature | Status | Priority |
|---------|--------|----------|
| Mermaid Diagrams | ✅ Done | High |
| LaTeX Math | ✅ Done | High |
| Code Highlighting | ✅ Done | Medium |
| Table of Contents | ✅ Done | Medium |
| Callouts | ✅ Done | Low |

---

## 💻 Code Blocks

```python
from gathering.lsp import LSPManager

# Initialize Python LSP
manager = LSPManager.get_server(
    project_id=1,
    language="python",
    workspace_path="/workspace/project"
)

# Get completions
completions = await manager.get_completions(
    file_path="main.py",
    line=10,
    character=5,
    content="import sys\nsys."
)

print(f"Found {len(completions)} completions!")
```

```typescript
// React component with LSP
const LSPCodeEditor: React.FC = () => {
  const [completions, setCompletions] = useState([]);

  useEffect(() => {
    lspService.getCompletions(projectId, 'python', filePath, line, char)
      .then(setCompletions);
  }, []);

  return <MonacoEditor {...props} />;
};
```

---

## 🎨 Nested Structures

### Complex Math Expression

The Fourier Transform of a function $f(t)$ is defined as:

$$\mathcal{F}\{f(t)\} = F(\omega) = \int_{-\infty}^{\infty} f(t) e^{-i\omega t} dt$$

And the inverse transform:

$$\mathcal{F}^{-1}\{F(\omega)\} = f(t) = \frac{1}{2\pi} \int_{-\infty}^{\infty} F(\omega) e^{i\omega t} d\omega$$

### Combined Diagram

```mermaid
flowchart LR
    subgraph Frontend
        A[Monaco Editor] --> B[LSP Providers]
        B --> C[lspService.ts]
    end

    subgraph Backend
        D[LSP Router] --> E[LSPManager]
        E --> F[PylspWrapper]
        F --> G[Jedi + Pyflakes]
    end

    C -->|HTTP| D
```

---

**✨ This is the magic of Phase 8.3!**
