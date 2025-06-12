import requests
from commons.logs import get_logger

logger = get_logger("jira_module")

class JiraModule:
    def __init__(self, context, **module_config):
        self.context = context
        self.config = module_config
        self.base_url = self.config["jira_base_url"].rstrip("/")
        self.auth = (self.config["username"], self.config["api_token"])
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def _parse_response(self, resp):
        try:
            data = resp.json()
        except Exception:
            data = {"error": resp.text}
        return {"status": "ok" if resp.ok else "fail", "response": data}

    def create_ticket(self, project_key, summary, issue_type, description=None, custom_fields=None, assignee=None, watchers=None, labels=None, components=None):
        url = f"{self.base_url}/rest/api/2/issue"
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

        data = {"fields": fields}
        resp = requests.post(url, json=data, auth=self.auth, headers=self.headers)
        parsed = self._parse_response(resp)

        # Add watchers if ticket creation succeeded
        if parsed["status"] == "ok" and watchers:
            key = parsed["response"].get("key")
            for watcher in watchers:
                self.add_watcher(key, watcher)

        return parsed

    def update_ticket(self, issue_key, fields):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        resp = requests.put(url, json={"fields": fields}, auth=self.auth, headers=self.headers)
        return self._parse_response(resp)

    def add_comment(self, issue_key, comment):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/comment"
        resp = requests.post(url, json={"body": comment}, auth=self.auth, headers=self.headers)
        return self._parse_response(resp)

    def get_ticket(self, issue_key):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}"
        resp = requests.get(url, auth=self.auth, headers=self.headers)
        return self._parse_response(resp)

    def search_tickets(self, jql):
        url = f"{self.base_url}/rest/api/2/search"
        resp = requests.get(url, params={"jql": jql}, auth=self.auth, headers=self.headers)
        return self._parse_response(resp)

    def get_status(self, issue_key):
        result = self.get_ticket(issue_key)
        if result["status"] != "ok":
            return result
        status = result["response"]["fields"]["status"]["name"]
        return {"status": "ok", "issue_status": status}

    def attach_file(self, issue_key, file_path):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/attachments"
        headers = {
            "X-Atlassian-Token": "no-check"
        }
        with open(file_path, "rb") as f:
            files = {"file": (file_path, f, "application/octet-stream")}
            resp = requests.post(url, headers=headers, files=files, auth=self.auth)
        return self._parse_response(resp)

    def transition_ticket(self, issue_key, transition_id):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/transitions"
        payload = {
            "transition": {"id": str(transition_id)}
        }
        resp = requests.post(url, json=payload, auth=self.auth, headers=self.headers)
        return self._parse_response(resp)

    def add_watcher(self, issue_key, username):
        url = f"{self.base_url}/rest/api/2/issue/{issue_key}/watchers"
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        resp = requests.post(url, data=f'"{username}"', auth=self.auth, headers=headers)
        return self._parse_response(resp)
