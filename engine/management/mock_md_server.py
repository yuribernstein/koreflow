from flask import Flask, jsonify, request
from commons.get_config import get_config
config = get_config()

md_config = config["module_dispatcher"]
app = Flask(__name__)

@app.route("/poll", methods=["GET"])
def poll_modules():
    customer_id = request.headers.get('SAWECUSTOMERID')
    secret_key = request.headers.get('SAWESECRETKEY')

    if not customer_id or not secret_key:
        return jsonify({"error": "Missing headers"}), 400

    # Return static mock response
    return jsonify({
        "repos": [
            {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "name": "slack_module", ### equal to a relative dir under /sawe/repos
                "subfolder": "slack_module"
            },
            {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "name": "api_module",
                "subfolder": "api_module"
            },
            {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "name": "email_module",
                "subfolder": "email_module"
            },
            {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "name": "chatbot_module",
                "subfolder": "chatbot_module"
            }, 
            {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "name": "webform",
                "subfolder": "webform"
            },     
            {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "name": "git_module",
                "subfolder": "git_module"
            },
           {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "name": "delegate_remote_workflow",
                "subfolder": "delegate_remote_workflow"
            },
           {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "name": "command_module",
                "subfolder": "command_module"
            }              
        
        ],
        "workflows_repo": {
                "url": md_config['modules_repo'],
                "access_key": md_config['modules_repo_access_key'],
                "branch": "md_config['modules_branch']",
                "md5": "d41d8cd98f00b204e9800998ecf8427e",
                "subfolder": "workflows"
        }

    })

def start_server():
    app.run(host="0.0.0.0", port=md_config['port'])
