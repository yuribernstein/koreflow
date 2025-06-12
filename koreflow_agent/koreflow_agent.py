import os
import yaml
import re
from pathlib import Path
from openai import OpenAI

# === CONFIG ===
OPENAI_MODEL = "gpt-4"
WORKFLOW_DIR = Path("../workflows/generated")
SYSTEM_PROMPT_PATH = Path("./system_prompt.txt")
MODULES_DIR = Path("../modules")
# make sure to provide OpenAI API key in the environment variable OPENAI_API_KEY, 
# eg: export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


# === INIT ===
WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)

# === Load and extend system prompt ===
def load_module_summaries(modules_dir=MODULES_DIR):
    summaries = []
    for mod_path in modules_dir.iterdir():
        if not mod_path.is_dir():
            continue
        module_yaml = mod_path / "module.yaml"
        usage_yaml = mod_path / "usage_reference.yaml"

        if not module_yaml.exists():
            continue

        with open(module_yaml) as f:
            module_data = yaml.safe_load(f)

        methods = module_data.get("methods", [])
        usage = None
        if usage_yaml.exists():
            with open(usage_yaml) as f:
                usage = list(yaml.safe_load_all(f))


        summaries.append({
            "name": module_data.get("name", mod_path.name),
            "class": module_data.get("class", ""),
            "methods": methods,
            "usage_reference": usage
        })

    return summaries

def format_module_summary(summaries):
    formatted = ["\nHere are the currently available modules:"]
    for m in summaries:
        formatted.append(f"- **{m['name']}** ({m['class']})")
        for method in m["methods"]:
            args = ", ".join(a["name"] for a in method.get("arguments", []))
            formatted.append(f"    • `{method['name']}({args})`: {method.get('description', '')}")
    return "\n".join(formatted)

with open(SYSTEM_PROMPT_PATH, "r") as f:
    base_prompt = f.read()

modules = load_module_summaries()
module_description = format_module_summary(modules)
full_system_prompt = base_prompt + "\n\n" + module_description

# === Start chat ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
conversation = [{"role": "system", "content": full_system_prompt}]
workflow_complete = False
user_message = input("🧠 You: ")

def extract_yaml_from_reply(reply_text):
    blocks = re.findall(r"```(?:yaml)?\s*(.*?)\s*```", reply_text, re.DOTALL)
    for block in blocks:
        try:
            parsed = yaml.safe_load(block)
            if "workflow" in parsed:
                return parsed, block.strip()
        except Exception:
            continue
    return None, None


while not workflow_complete:
    conversation.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=conversation,
        temperature=0.3
    )

    reply = response.choices[0].message.content
    conversation.append({"role": "assistant", "content": reply})

    parsed, raw_yaml = extract_yaml_from_reply(reply)
    if parsed:
        wf_name = parsed["workflow"].get("name", "unnamed_workflow")
        filename = wf_name.lower().replace(" ", "_") + ".yaml"
        path = WORKFLOW_DIR / filename

        with open(path, "w") as f:
            f.write(raw_yaml)

        print(f"\n✅ Workflow saved to: {path}\n")
        workflow_complete = True
    else:
        print(f"\n🤖 Koreflow Agent: {reply}\n")
        user_message = input("🧠 You: ")


