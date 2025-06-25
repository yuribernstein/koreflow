import requests
from commons.logs import get_logger

logger = get_logger("jira_module")


class Jira:
    def __init__(self, context, **module_config):
        self.context = context
        self.config = module_config
        self.base_url = self.config["jira_base_url"].rstrip("/")
        self.auth = (self.config["username"], self.config["api_token"])
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        logger.debug(f"[INIT] Jira module initialized with base_url: {self.base_url}")

    def _parse_response(self, resp, success_msg="", fail_msg=""):
        try:
            data = resp.json()
        except Exception as e:
            data = {"error": resp.text}
            logger.warning(f"[JIRA] Failed to parse response JSON: {e}")
        if resp.ok:
            return {"status": "ok", "message": success_msg, "data": data}
        else:
            logger.warning(f"[HTTP] {resp.request.method} {resp.url} - {resp.status_code}")
            return {"status": "fail", "message": fail_msg or str(data), "data": data}

    def create_ticket(self, project_key, summary, issue_type, description=None, custom_fields=None,
                      assignee=None, watchers=None, labels=None, components=None):
        url = f"{self.base_url}/rest/api/2/issue"
        logger.info(f"[JIRA] Creating ticket in project: {project_key} with summary: {summary}")

        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        if description:
            fields["description"] = description
        if assignee:
            fields["assignee"] = {"name": assignee}
        if custom_fields:
            fields.update(custom_fields)
        if labels:
            fields["labels"] = labels
        if components:
            fields["components"] = [{"name": c} for c in components]

        logger.debug(f"[JIRA] Final payload: {fields}")
        resp = requests.post(url, json={"fields": fields}, auth=self.auth, headers=self.headers)
        parsed = self._parse_response(resp, "Ticket created", "Failed to create ticket")

        if parsed["status"] == "ok":
            key = parsed["data"].get("key")
            parsed["data"] = key
            if watchers:
                for watcher in watchers:
                    self.add_watcher(key, watcher)
        else:
            logger.error(f"[JIRA] Ticket creation failed: {parsed['data']}")

        return parsed

    def update_ticket(self, issue_key, fields):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        logger.info(f"[JIRA] Updating ticket {issue_key} with fields {fields}")
        resp = requests.put(url, json={"fields": fields}, auth=self.auth, headers=self.headers)
        return self._parse_response(resp, f"Updated ticket {issue_key}", f"Failed to update {issue_key}")

    def add_comment(self, issue_key, comment):
        if not issue_key:
            return {"status": "fail", "message": "Empty issue key", "data": None}
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment"
        logger.info(f"[JIRA] Adding comment to {issue_key}")
        resp = requests.post(url, json={"body": comment}, auth=self.auth, headers=self.headers)
        return self._parse_response(resp, f"Comment added to {issue_key}", f"Failed to comment on {issue_key}")

    def get_ticket(self, issue_key):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        logger.debug(f"[JIRA] Fetching ticket: {issue_key}")
        resp = requests.get(url, auth=self.auth, headers=self.headers)
        return self._parse_response(resp, f"Ticket {issue_key} fetched", f"Failed to fetch {issue_key}")

    def search_tickets(self, jql):
        url = f"{self.base_url}/rest/api/2/search"
        logger.info(f"[JIRA] Searching tickets with JQL: {jql}")
        resp = requests.get(url, params={"jql": jql}, auth=self.auth, headers=self.headers)
        return self._parse_response(resp, "Search successful", "Search failed")

    def get_status(self, issue_key):
        result = self.get_ticket(issue_key)
        if result["status"] != "ok":
            return result
        try:
            status_name = result["data"]["fields"]["status"]["name"]
            return {"status": "ok", "message": f"Status of {issue_key}: {status_name}", "data": status_name}
        except Exception as e:
            return {"status": "fail", "message": f"Could not extract status: {e}", "data": None}

    def attach_file(self, issue_key, file_path):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/attachments"
        logger.info(f"[JIRA] Attaching file {file_path} to {issue_key}")
        headers = self.headers.copy()
        headers["X-Atlassian-Token"] = "no-check"

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path, f, "application/octet-stream")}
                resp = requests.post(url, headers=headers, files=files, auth=self.auth)
        except Exception as e:
            return {"status": "fail", "message": f"Failed to open file: {e}", "data": None}

        return self._parse_response(resp, f"File attached to {issue_key}", f"Failed to attach file to {issue_key}")

    def transition_ticket(self, issue_key, transition_id):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/transitions"
        logger.info(f"[JIRA] Transitioning {issue_key} with transition ID {transition_id}")
        payload = {
            "transition": {"id": str(transition_id)}
        }
        resp = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
        return self._parse_response(resp, f"Transitioned {issue_key}", f"Failed to transition {issue_key}")

    def add_watcher(self, issue_key, username):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/watchers"
        logger.info(f"[JIRA] Adding watcher {username} to {issue_key}")
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        resp = requests.post(url, data=f'"{username}"', auth=self.auth, headers=headers)
        return self._parse_response(resp, f"Watcher {username} added", f"Failed to add watcher {username}")
