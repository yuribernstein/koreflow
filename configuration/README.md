# Koreflow Configuration Reference

This document explains the structure and purpose of each section in the Koreflow configuration file. It is designed to help you customize and manage the Koreflow execution environment effectively.

---

## Logging

```yaml
logging:
  level: DEBUG
  format: "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
```

- **level**: Controls the log verbosity. Common options: DEBUG, INFO, WARNING, ERROR.
- **format**: Python-style log formatter string.

---

## Directories

```yaml
directories:
  workdir: ...
  modules: ...
  workflows: ...
  lifetimes: ...
  logs: ...
```

- **workdir**: Root working directory of Koreflow.
- **modules**: Path where modules (with `module.yaml`) are discovered and loaded.
- **workflows**: Directory for stored workflows.
- **lifetimes**: Internal use (for long-lived stateful modules).
- **logs**: Path to store execution and system logs.

---

## Application Settings

```yaml
app:
  port: 8080
  poll_for_modules_on_startup: false
  ignored_workflow_dirs:
    - "samples"
    - "deprecated"
  base_url: http://localhost:8080
```

- **port**: Main HTTP server port.
- **poll_for_modules_on_startup**: If true, refreshes module list from dispatcher repo on each boot.
- **ignored_workflow_dirs**: List of folders under `workflows/` to skip loading.
- **base_url**: Used for internal links (e.g., webforms or approval URLs).

---

## Module Dispatcher

```yaml
module_dispatcher:
  port: 8081
  url: http://localhost:8081/poll
  md5_strict: false
  customer_id: community
  secret_key: community
  modules_repo: https://github.com/...
  modules_repo_access_key: "..."
  modules_branch: lifetime
```

- Dispatcher helps synchronize available modules from a Git repo.
- **md5_strict**: If true, enforces content hash matching.
- **modules_repo**: Git URL where modules live.
- **modules_branch**: Branch to pull updated modules from.
- **access_key**: Access token for private repos.

---

## Module Defaults

These allow you to pre-configure module-specific settings and API clients globally.

### Chatbot

```yaml
chatbot:
  provider: openai
  model: gpt-4
  temperature: 0.7
  api_key: ...
```

### API Requests

```yaml
api:
  timeout: 15
  headers:
    Content-Type: "application/json"
    Authorization: "Bearer {{ context.default_api_token }}"
  blocking_defaults:
    poll_interval_seconds: 5
    timeout_minutes: 3
```

### Email

```yaml
email_module:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  smtp_user: ...
  smtp_pass: ...
  from_addr: ...
```

### Slack

```yaml
slack_module:
  webhook_url: ...
```

### GitHub

```yaml
git_module:
  github_token: ...
```

### Jira

```yaml
jira_module:
  jira_base_url: ...
  username: ...
  api_token: ...
```

> **Note:** You can override these defaults inside individual steps by specifying `input` directly.

---

## Security Note

Avoid hardcoding sensitive secrets in configuration files in production environments. Consider:
- Environment variables
- Encrypted secret stores (e.g., HashiCorp Vault)
- External secret injection via CI/CD pipelines

---

