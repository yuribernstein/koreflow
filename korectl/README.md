Certainly. Here's the cleaned-up `README.md` in a simple, professional Markdown format without emojis or decorative icons:

```markdown
# korectl — Koreflow CLI Tool

`korectl` is the official command-line utility for working with Koreflow automation workflows and modules.

It supports module scaffolding, workflow generation, deep schema validation, and ad-hoc workflow execution against a Koreflow engine.

---

## Features

- Module scaffolding: Create new module directories with Python stubs and manifests.
- Workflow validation: Validate workflow YAMLs against the schema and module signatures.
- Module manifest validation: Ensure module metadata conforms to the schema.
- Full workflow generation: Auto-generate realistic workflows using available modules.
- Context module resolution: Supports context-aware step referencing and validation.
- Ad-hoc execution: Run a workflow against a remote or local Koreflow server.

---

## Installation

To run locally:

```bash
python korectl.py --help
```

Or install as an editable package:

```bash
pip install -e .
```

---

## Usage

### Initialize a Module

```bash
korectl init module logger
```

Creates a module scaffold in `modules/logger/` with:

- `logger.py`
- `module.yaml`
- `usage_reference.yaml`

---

### Generate a Workflow

#### Minimal version

```bash
korectl init workflow hello_world
```

#### Full version with module usage

```bash
korectl init workflow alert_flow --full --modules logger,email --trigger api
```

**Options:**

| Option              | Description                                     |
|---------------------|-------------------------------------------------|
| `--full`            | Include example steps from module usage         |
| `--modules`         | Comma-separated list of modules to include      |
| `--modules-path`    | Path to the modules directory (default: `./modules`) |
| `--workflows-path`  | Path for saving the workflow (default: `./workflows`) |
| `--trigger`         | Trigger type: `api`, `git`, `scheduled`, `ad-hoc` |

---

### Validate a Workflow File

```bash
korectl validate-workflow --workflow workflows/demo.yaml --verbose
```

Performs:

- Schema compliance check
- Step method validation
- Argument presence check
- Duplicate step detection
- Context module validation
- Validation of `on_success`, `on_failure`, and `global_failure_handler` blocks

---

### Validate Module Manifests

```bash
korectl validate-modules
```

Validates all `module.yaml` files in the specified modules directory against the JSON schema.

---

### Run a Workflow via API

```bash
korectl run --workflow workflows/demo.yaml --server localhost:8080
```

Triggers the specified workflow on the Koreflow server instance.


---

## Author

Yuri Bernstein  
Creator of Koreflow  
Email: yuri.bernstein@gmail.com

---

## License

Koreflow is licensed under the GNU Affero General Public License v3.0 (AGPLv3).

If you use Koreflow or its derivatives in a commercial product or service (including SaaS), a revenue-sharing agreement applies. You must either:

- Open source your derived work under AGPLv3, or
- Contact the author to arrange a 1.5% gross revenue share license.

See `LICENSE` and `EULA.md` for details.
```