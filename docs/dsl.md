# Koreflow Workflow DSL Reference

This document defines the Koreflow YAML-based DSL for authoring declarative workflows, including schema structure, conditional logic, variable resolution, failure handling, and execution triggers.

---

## Root Structure

```yaml
workflow:
  name: <string>
  match: <match_block>               # Optional matching conditions
  payload_parser: <list of rules>   # Optional parsing rules
  context_variables: <list>         # Optional context defaults
  global_modules: <list>            # Optional preloaded module list
  steps: <list of steps>            # Required execution steps
  on_success: <list of steps>       # Optional global success handlers
  on_failure: <list of steps>       # Optional global failure handlers
  global_failure_handler: <string>  # Optional step ID to call on any failure
  trigger: <trigger_block>          # Optional trigger type
```

---

## Match Block (Optional)

```yaml
match:
  conditions:
    - path: <dot_notation_path>
      operator: <supported_operator>
      value: <any>                  # Optional depending on operator
      id: <string>
  condition_logic: <string>         # e.g., "A and (B or not C)"
```

### Supported Operators:

| Operator       | Description                          |
|----------------|--------------------------------------|
| equals         | actual == value                      |
| not_equals     | actual != value                      |
| contains       | value in actual                      |
| not_contains   | value not in actual                  |
| starts_with    | actual.startswith(value)             |
| is_in          | actual in value (value must be list) |
| not_in         | actual not in value                  |
| present        | path exists                          |
| absent         | path does not exist                  |
| length         | compares array length                |

---

## Payload Parser (Optional)

```yaml
payload_parser:
  - path: <dot_notation_path>
    var: <string>                  # Variable name in context
    absent_action: fail|ignore     # Optional (default: fail)
```

---

## Context Variables (Optional)

```yaml
context_variables:
  - name: <string>
    type: string|int|array|object   # Optional
    default: <value>                # Optional
    description: <string>          # Optional
```

**Context Resolution Notes:**
- `context.token` refers to values from `context_variables`.
- All parsed variables (`payload_parser`) and registered outputs (`register_vars`, `register_output`) are added to the dynamic execution context.
- Variables can be accessed using Jinja-style syntax (`{{ var }}`) in inputs, conditions, and outputs.

---

## Global Modules (Optional)

```yaml
global_modules:
  - name: <module_name>            # Must match directory/module name
    path: <path_to_module_dir>     # Optional override of default path
```

These are loaded and validated at engine boot time and made available globally.

---

## Steps (Required)

```yaml
steps:
  - id: <string>
    type: action
    action: <module.class.method>
    input: <dict of inputs>
    conditions: <list of conditions>          # Optional
    register_output: <string>                # Optional
    register_vars: <list of variables>       # Optional
```

### Per-Step Conditions (Optional)

```yaml
conditions:
  - name: <string>
    condition: <template string>
```

### Register Variables (Optional)

```yaml
register_vars:
  - name: <string>
    value: <template string>
    absent_action: fail|ignore   # Optional

  - name: <string>
    conditional:
      - if: <template string>
        value: <any>
      - elif: <template string>
        value: <any>
      - default: <any>           # Optional
```

---

## Global Handlers

### `on_success` and `on_failure`

Executed only after all `steps` finish, depending on global outcome.

```yaml
on_success:
  - id: log_success
    type: action
    action: logger.stdout.print
    input:
      message: "Workflow completed successfully"

on_failure:
  - id: log_failure
    type: action
    action: logger.stdout.print
    input:
      message: "Workflow failed"
```

### `global_failure_handler`

Executed as a last-resort fallback in the event of uncaught exceptions or hard failures (optional):

```yaml
global_failure_handler: log_failure
```

---

## Templating Support

All template strings use `{{ var }}` syntax and support:
- Variables from `context_variables`, `payload_parser`, `register_output`, and `register_vars`
- Jinja-like syntax with basic logic and filters

---

## Trigger Block (Optional)

```yaml
trigger:
  type: api | git | scheduled | ad-hoc | aiagent

  api:
    match: {...}                  # Same structure as root match
    parsers: <payload_parser>

  git:
    repo: <url>
    auth:
      type: token
      token: {{ context.token }}
    method: push | poll
    branch: <branch>
    files:
      - path: <string>
        on_change: trigger

  scheduled:
    cron: "0 9 * * *"              # UTC time cron

  ad-hoc: {}                       # No extra fields
```

---

## Notes

- Only one `trigger` block is allowed per workflow.
- `steps` is the only required root field; all others are optional.
- Koreflow runtime performs strict validation on workflows before execution.
- For more info about aiagents trigger type, check docs/agents.md

---

## Example Workflow

```yaml
workflow:
  name: deploy_workflow

  match:
    conditions:
      - path: payload.repo.name
        operator: equals
        value: "infra-tools"
        id: repo_check
    condition_logic: repo_check

  payload_parser:
    - path: payload.labels[*]
      var: labels
    - path: payload.author
      var: author
      absent_action: ignore

  context_variables:
    - name: token
      default: "default-token"

  global_modules:
    - name: logger

  steps:
    - id: fetch_data
      type: action
      action: gather.api.fetch
      input:
        url: "https://api.example.com"
        headers:
          Authorization: Bearer {{ context.token }}
      register_output: response
      register_vars:
        - name: status
          value: "{{ response.status }}"

    - id: notify
      type: action
      conditions:
        - name: send only on failure
          condition: "{{ status }} == 'error'"
      action: email.alert.send
      input:
        to: ["devops@acme.io"]
        subject: "API call failed"
        body: "Details: {{ response }}"

  on_failure:
    - id: log_failure
      type: action
      action: logger.stdout.print
      input:
        message: "Workflow encountered an error"

  global_failure_handler: log_failure
```

