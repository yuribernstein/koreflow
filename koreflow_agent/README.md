# Koreflow Workflow Generator

This tool is an interactive CLI assistant that helps generate valid Koreflow workflows using the Koreflow DSL and OpenAI's GPT-4 API.

---

## Overview

Koreflow workflows are YAML-based automations triggered by external events. This tool guides the user through a step-by-step conversation to define those workflows, using only valid, module-supported methods defined in the Koreflow environment.

The assistant reads module definitions, appends them to a structured system prompt, and interacts with the user to produce a fully-formed `workflow:` block. Once complete, the YAML is parsed, validated, and saved to disk.

---

## Features

- **Conversational Workflow Design**  
  Interactive session powered by GPT-4 that guides users toward a valid Koreflow automation.

- **Dynamic Module Discovery**  
  Scans the `./modules` directory for `module.yaml` and `usage_reference.yaml` files and extracts method definitions automatically.

- **Strict DSL Compliance**  
  Ensures workflows follow the Koreflow schema, safely referencing only declared variables and supported actions.

- **YAML Output & Validation**  
  Extracts the `workflow:` block from assistant replies, validates it, and saves it to `./workflows/generated`.

---

## How It Works

1. **System Prompt Loading**  
   Reads `system_prompt.txt` and augments it with all available module methods for context.

2. **Module Summary Construction**  
   Extracts names, classes, methods, and arguments from each module definition.

3. **Interactive Chat Loop**  
   Begins a conversation where the user describes an automation goal. The assistant asks exactly one question at a time and assembles the workflow incrementally.

4. **YAML Parsing**  
   Replies are scanned for YAML blocks containing a `workflow:` key. If found, the workflow is validated and saved using the `name` field.

---

## File Structure

```text
.
├── workflows/
│   └── generated/            # Auto-saved workflow YAMLs
├── modules/
│   ├── my_module/
│   │   ├── module.yaml
│   │   └── usage_reference.yaml
├── system_prompt.txt         # Core DSL assistant instructions
└── generate_workflow.py      # Main entry script
````

---

## Requirements

* Python 3.8+
* OpenAI Python SDK
* PyYAML

Install dependencies:

```bash
pip install -r requirements.txt
```

Export your API key:

```bash
export OPENAI_API_KEY=your-openai-key
```

---

## Usage

Run the assistant:

```bash
python generate_workflow.py
```

The assistant will begin asking questions in the terminal. After enough information is gathered, a YAML file will be saved to:

```text
./workflows/generated/<workflow_name>.yaml
```

---

## License

This project is licensed under the AGPLv3. For alternative commercial or OEM licensing, please contact yuri.bernstein@gmail.com