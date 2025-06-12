# Koreflow: Agent-Driven Workflow Execution Guide

Koreflow supports interactive workflows that are externally guided by agents (human or system actors). This is achieved using the `aiagent` trigger type, enabling fine-grained control and runtime data submission via HTTP APIs.

---

## 1. Overview: What Are Agents in Koreflow?

Agents are external entities that can:

- Start workflows with runtime control privileges
- Pause, resume, skip, or jump between steps
- Submit structured input mid-execution
- Query status and context of the running workflow

This model is ideal for human-in-the-loop automations, AI-assisted decision chains, or orchestrations that require external commands.

---

## 2. Declaring an AI Agent Workflow

To build an agent-aware workflow, set the `trigger.type` to `aiagent`.

### Minimal DSL Example

```yaml
workflow:
  name: agent_driven_demo
  trigger:
    type: aiagent

  context_variables:
    - name: next_command
      type: string
      description: "Command to be executed, provided by agent"

  steps:
    - id: wait_for_command
      type: action
      action: aiagent_input.wait_for_input
      input:
        expected_keys: ["next_command"]
        timeout_seconds: 600
      register_output: agent_response
      register_vars:
        - name: next_command
          value: "{{ context.step_results.agent_response.data.next_command }}"

    - id: log_decision
      type: action
      action: logger.run
      input:
        message: "Agent selected: {{ context.next_command }}"
```

---

## 3. Runtime Behavior

### Triggering the Workflow

Send a `POST` request to:

```
POST /api/<repo>/<workflow_name>
Content-Type: application/json
```

**Response:**
```json
{
  "status": "accepted",
  "workflow_uid": "abc123",
  "access_key": "agent-9e1f42b3"
}
```

Use `workflow_uid` and `access_key` in all further interactions.

---

## 4. Providing Input from Agent

### Endpoint

```
POST /api/agent/<uid>/<step_id>/input
Headers:
  Content-Type: application/json
  X-Access-Key: <access_key>
```

**Payload Example:**

```json
{
  "next_command": "restart_service"
}
```

This will unblock the `wait_for_input` step and inject values into the context, making them usable in downstream steps as `{{ context.next_command }}`.

---

## 5. Workflow Control API (Pause, Resume, Skip)

Koreflow provides an agent control API for managing workflow execution:

| Action     | Endpoint                                         |
|------------|--------------------------------------------------|
| Pause      | `POST /api/agent/<uid>/pause`                   |
| Resume     | `POST /api/agent/<uid>/resume`                  |
| Cancel     | `POST /api/agent/<uid>/cancel`                  |
| Skip Step  | `POST /api/agent/<uid>/skip/<step_id>`         |
| Jump To    | `POST /api/agent/<uid>/jump/<step_id>`         |

All requests must include the `X-Access-Key` header.

---

## 6. Checking Workflow Status

Use this endpoint to get runtime information:

```
GET /api/agent/<uid>/status
Headers:
  X-Access-Key: <access_key>
```

**Returns:**

```json
{
  "uid": "abc123",
  "current_step": "wait_for_command",
  "current_step_type": "action",
  "context": { ... },
  "step_results": { ... },
  "status": "in_progress"
}
```

---

## 7. Example Agent Flow (Full)

```yaml
workflow:
  name: example_agent_guided
  trigger:
    type: aiagent

  context_variables:
    - name: command
      type: string
    - name: action_id
      type: string

  steps:
    - id: wait_input
      type: action
      action: aiagent_input.wait_for_input
      input:
        expected_keys: ["command", "action_id"]
        timeout_seconds: 300
      register_output: input_result
      register_vars:
        - name: command
          value: "{{ context.step_results.input_result.data.command }}"
        - name: action_id
          value: "{{ context.step_results.input_result.data.action_id }}"

    - id: log_command
      type: action
      action: logger.run
      input:
        message: "Received: {{ context.command }} on {{ context.action_id }}"
```

---

## 8. Submitting Workflows On-the-Fly via API

Koreflow supports dynamic submission and validation of workflow YAML files using a `PUT` API endpoint.

### Endpoint

```
PUT /api/<repo>/<workflow_name>
Content-Type: text/plain or application/x-yaml
```

If `<workflow_name>` does not end in `.yaml`, it is automatically appended.

### Example `curl` Upload

```bash
curl -X PUT http://localhost:8080/api/default/my_workflow      -H "Content-Type: text/plain"      --data-binary @my_workflow.yaml
```

### Behavior

- The uploaded workflow is saved under `./workflows/<repo>/<workflow_name>.yaml`
- Path traversal is blocked (`..` not allowed)
- Workflow is immediately validated against the current module set

### Response on Success

```json
{
  "status": "ok",
  "message": "Workflow 'my_workflow.yaml' uploaded and validated under repo 'default'"
}
```

### Response on Failure

```json
{
  "status": "error",
  "message": "Missing required input(s) {'env'} in step 'deploy_step'"
}
```

---

## 9. Summary

Agent workflows in Koreflow allow external systems or humans to:

- Inject decisions or data mid-execution
- Control flow state with pause/resume/skip
- Upload new workflows dynamically via API
- Build collaborative or AI-assisted workflows with full traceability

This design is ideal for systems that combine automation with dynamic or unpredictable runtime input.
