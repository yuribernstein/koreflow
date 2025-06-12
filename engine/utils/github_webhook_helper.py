# github_webhook_helper.py

import requests
from urllib.parse import urlparse
from commons.logs import get_logger

logger = get_logger(__name__)

def extract_repo_slug(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path.strip("/").replace(".git", "")

def install_webhook(repo_url, token, sawe_url, repo_name, workflow_name):
    slug = extract_repo_slug(repo_url)
    webhook_url = f"{sawe_url}/api/{repo_name}/{workflow_name}"
    api_url = f"https://api.github.com/repos/{slug}/hooks"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    body = {
        "name": "web",
        "active": True,
        "events": ["push"],
        "config": {
            "url": webhook_url,
            "content_type": "json",
            "insecure_ssl": "0"
        }
    }

    logger.info(f"[GITOPS] Installing webhook to {slug} → {webhook_url}")

    try:
        res = requests.post(api_url, json=body, headers=headers)
        if res.status_code in [200, 201]:
            logger.info(f"[GITOPS] Webhook created for {slug}")
            return True
        elif res.status_code == 422:
            logger.info(f"[GITOPS] Webhook already exists for {slug}")
            return True
        else:
            logger.error(f"[GITOPS] Failed to create webhook: {res.status_code} — {res.text}")
            return False
    except Exception as e:
        logger.exception(f"[GITOPS] Exception creating webhook for {slug}: {e}")
        return False
