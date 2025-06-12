# Koreflow Module Developer Guide

## 1. Introduction

Welcome to the **Koreflow** automation framework!  
Modules are the atomic units of functionality in Koreflow workflows. They encapsulate actions and integrations that can be reused across workflows.

This guide walks you through building a module that conforms to the Koreflow engine.

---

## 2. How the Engine Works (High-Level)

- Workflows are written in YAML using the Koreflow DSL.
- The engine parses and executes each step in order.
- Each step calls a module's method using workflow input data.
- Context variables persist and evolve through the workflow lifecycle.
- Workflow failure handling is supported via conditional logic and `on_failure` / `global_failure_handler` blocks.

---

## 3. What a Module Is

A module in Koreflow is:

- A Python class
- Packaged inside a named directory under `modules/`
- Described by a `module.yaml` manifest file
- Must include a `usage_reference.yaml` file

It must define:
- A class with callable methods
- A `module.yaml` that describes its methods and argument schemas
- A `usage_reference.yaml` containing reusable step examples (used by `korectl` and `koreagent` to scaffold workflows)

---

## 4. Required Structure of a Module

### Folder Layout

```
modules/example_module/
├── module.yaml
├── usage_reference.yaml
├── example.py
├── templates/ (optional)
│    └── sample_template.j2
```

### module.yaml Example

```yaml
name: example_module
class: Example
version: 1.0
author: Your Name

methods:
  - name: echo
    description: "Echo back input values"
    arguments:
      - name: message
        type: string
        required: true
```

- `name`, `class`, `version`, and `methods` are required.
- Each method must define `arguments`, each with a `name` and `type`.

---

### usage_reference.yaml

This file provides canonical examples for how each method is invoked within a workflow. 
Used by:
- `korectl init workflow` (autogenerates workflows)
- `koreagent` (AI-assisted workflow suggestions)

Basic format:

```yaml
steps:
  - id: echo_hello
    type: action
    action: example_module.Example.echo
    input:
      message: "Hello from template!"
```

---

### Python Class Example

```python
from commons.logs import get_logger
logger = get_logger("example_module")

class Example:
    def __init__(self, context, **module_config):
        self.context = context

    def echo(self, message):
        logger.info(f"Echoing: {message}")

        return {
            "status": "ok",
            "message": "Echo complete",
            "data": {
                "echo": message
            }
        }
```

---

## 5. Method Return Convention

Every method must return a dictionary with this structure:

```python
{
  "status": "ok" | "fail" | "warn",
  "message": "Short message",
  "data": { ... }  # optional
}
```

- `status: fail` will halt the workflow unless handled
- `warn` allows workflow to continue

---

## 6. Context Access

Modules can read and write shared workflow context:

```python
self.context.get("key")
self.context.set("key", value)
```

The context is automatically populated by:
- `payload_parser`
- `context_variables`
- Previous step outputs (`register_output`)
- Dynamic variables (`register_vars`)

---

## 7. Template Rendering (Optional)

If your module uses Jinja2 templates:

- Store them under `templates/`
- Access using the preconfigured environment:

```python
template = self.env.get_template("sample_template.j2")
rendered = template.render(context=self.context.get_all())
```

---

## 8. Error Handling

- Return `{status: fail}` to mark a step as failed
- Avoid raw exceptions unless unrecoverable
- Use logging for debug and error tracing

---

## 9. Best Practices

- Log using the built-in logger
- Keep method logic small and testable
- Validate input before processing
- Fail gracefully using structured responses
- Use `context.set` to share computed values

---

## ✅ Quick Summary

| Topic         | Rule/Structure                           |
|---------------|-------------------------------------------|
| Folder        | One subfolder per module under `modules/` |
| Manifest      | Required `module.yaml` file               |
| Reference     | Required `usage_reference.yaml` file      |
| Class         | Python class matching manifest name       |
| Method Return | `status`, `message`, optional `data`      |
| Context       | `context.get`, `context.set` available     |
| Templates     | Jinja2 templates under `templates/`       |

---

## Coming Soon

- CLI validator: `korectl validate-modules`
- Auto-generated module docs from YAML
- Examples gallery

---

## Questions?
Email: yuri.bernstein@gmail.com

Happy building!
