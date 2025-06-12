import os
import shutil
import tempfile
import hashlib
import logging
import requests
from git import Repo
from commons.get_config import get_config
from commons.logs import get_logger
logger = get_logger("poller")


try:
    config = get_config()
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

logger.debug(f"Configuration loaded: {config}")

md5_strict = config.get('md5_strict', False)

def md5_of_folder(folder_path):
    """Calculate MD5 hash of all files in a folder recursively."""
    hash_md5 = hashlib.md5()
    for root, dirs, files in os.walk(folder_path):
        for file in sorted(files):
            file_path = os.path.join(root, file)
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
    return hash_md5.hexdigest()

def poll_modules(poll_modules=True, poll_workflows=True):
    """Poll the Module Dispatcher for module updates."""
    md_url = config['module_dispatcher']['url']
    workdir = config['directories']['workdir']
    modules_dir = config['directories']['modules']
    customer_id = config['module_dispatcher']['customer_id']
    secret_key = config['module_dispatcher']['secret_key']

    if not all([md_url, customer_id, secret_key]):
        logger.error("Missing MD URL, SAWECUSTOMERID or SAWESECRETKEY.")
        raise Exception("Module Poller configuration missing.")

    headers = {
        'SAWECUSTOMERID': customer_id,
        'SAWESECRETKEY': secret_key
    }

    logger.info(f"Polling Module Dispatcher at {md_url}...")
    try:
        response = requests.get(md_url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to contact Module Dispatcher: {e}")
        raise

    data = response.json()
    repos = data.get('repos', [])
    if not repos:
        logger.warning("No repos received from Module Dispatcher.")
        return

    logger.info(f"Received {len(repos)} repos from Module Dispatcher.")
    logger.info(f"Ensuring repos directory exists at {modules_dir}...")
    os.makedirs(modules_dir, exist_ok=True)
    if poll_modules:
        cleanup('modules')    
        logger.info(f"Cloning modules to {modules_dir}...")
        for repo_info in repos:
            _url = repo_info['url']
            access_key = repo_info['access_key']
            if not access_key:
                logger.error(f"Missing access key for repo {repo_info}.")
                continue
            url = _url.replace("https://", f"https://{access_key}:x-oauth-basic@")
            branch = repo_info.get('branch')
            expected_md5 = repo_info['md5']
            module_name = repo_info['name']
            subfolder = repo_info['subfolder']

            target_path = os.path.join(modules_dir, module_name)
            if os.path.exists(target_path):
                logger.info(f"Module {module_name} already exists. Skipping clone.")
                continue

            success = False
            for attempt in range(1, 4):
                logger.info(f"Cloning attempt {attempt} for module {module_name}...")
                try:
                    try:
                        temp_dir = tempfile.mkdtemp()
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                            os.makedirs(temp_dir, exist_ok=True)
                    except Exception as e:
                        logger.error(f"Failed to create temp directory: {e}")
                        raise
                    repo = Repo.clone_from(url, temp_dir)
                    if branch:
                        repo.git.checkout(branch)

                    source_subfolder = os.path.join(temp_dir, subfolder)
                    if not os.path.exists(source_subfolder):
                        logger.error(f"Subfolder {subfolder} not found in repo {url}.")
                        raise Exception("Subfolder missing.")

                    shutil.copytree(source_subfolder, target_path)
                    actual_md5 = md5_of_folder(target_path)

                    if actual_md5 != expected_md5:
                        if md5_strict:
                            logger.error(f"MD5 mismatch for module {module_name}. Expected {expected_md5}, got {actual_md5}.")
                            shutil.rmtree(target_path, ignore_errors=True)
                            raise Exception("MD5 mismatch.")
                        else:
                            logger.warning(f"MD5 mismatch for module {module_name}. Strict mode is off, proceeding anyway.")
                    
                    logger.info(f"Module {module_name} cloned and validated successfully.")
                    success = True
                    break

                except Exception as e:
                    logger.error(f"Error cloning module {module_name}: {e}")
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)

            if not success:
                logger.error(f"Failed to clone and validate module {module_name} after 3 attempts.")

    if poll_workflows:
        cleanup('workflows')
        logger.info("Cloning workflows repo...")
        workflows_info = data.get('workflows_repo')
        if workflows_info:
            clone_workflows_repo(workflows_info, config)



def cleanup(target):
    """Cleanup old repos and workflows."""
    modules_dir = config.get('repos_base_path')
    workflows_dir = config.get('workflows_base_path')
    if target == 'modules':
        target_dir = os.path.join(modules_dir)
    elif target == 'workflows':
        target_dir = os.path.join(workflows_dir)

    logger.info(f"Cleaning up old {target_dir}...")
    if os.path.exists(target_dir):
        shutil.rmtree(workflows_dir, ignore_errors=True)


def clone_workflows_repo(workflows_info, config):
    _url = workflows_info['url']
    access_key = workflows_info['access_key']
    if not access_key:
        raise ValueError("Missing access key for workflows repo.")
    url = _url.replace("https://", f"https://{access_key}:x-oauth-basic@")
    
    branch = workflows_info.get('branch')
    expected_md5 = workflows_info['md5']
    subfolder = workflows_info['subfolder']
    workflows_dir = config.get('workflows_base_path')

    if os.path.exists(workflows_dir):
        logger.info("Workflows repo already exists. Skipping clone.")
        return

    success = False
    for attempt in range(1, 4):
        logger.info(f"Cloning attempt {attempt} for workflows repo...")
        try:
            temp_dir = tempfile.mkdtemp()
            repo = Repo.clone_from(url, temp_dir)
            if branch:
                repo.git.checkout(branch)

            source_subfolder = os.path.join(temp_dir, subfolder)
            if not os.path.exists(source_subfolder):
                logger.error(f"Subfolder {subfolder} not found in repo {url}.")
                raise Exception("Subfolder missing.")

            shutil.copytree(source_subfolder, workflows_dir)
            actual_md5 = md5_of_folder(workflows_dir)

            if actual_md5 != expected_md5:
                if md5_strict:
                    logger.error(f"MD5 mismatch for workflows repo. Expected {expected_md5}, got {actual_md5}.")
                    shutil.rmtree(workflows_dir, ignore_errors=True)
                    raise Exception("MD5 mismatch.")
                else:
                    logger.warning(f"MD5 mismatch for workflows repo. Strict mode is off, proceeding anyway.")

            logger.info("Workflows repo cloned and validated successfully.")
            success = True
            break

        except Exception as e:
            logger.error(f"Error cloning workflows repo: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    if not success:
        logger.error("Failed to clone and validate workflows repo after 3 attempts.")



if __name__ == "__main__":
    try:
        poll_modules()
    except Exception as e:
        logger.error(f"Error in module polling: {e}")