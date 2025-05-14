from cat.mad_hatter.decorators import hook
import json
from cat.log import log


@hook
def agent_prompt_prefix(prefix, cat):
    user = cat.user_id
    user_status_path = "cat/static/user_status.json"
    with open(user_status_path, "r") as file:
        user_status = json.load(file)
    # Get selected_prompts for tags with status True
    prompts = [
        v["selected_prompt"]
        for k, v in user_status.get(user, {}).items()
        if v.get("status", False) and "selected_prompt" in v
    ]
    # Use the first prompt if available, otherwise keep the original prefix
    if prompts:
        prefix = prompts[0]
    return prefix

@hook  # default priority = 1
def before_cat_recalls_declarative_memories(declarative_recall_config, cat):
    user = cat.user_id
    user_status_path = "cat/static/user_status.json"
    with open(user_status_path, "r") as file:
        user_status = json.load(file)
    # Only include tags with status True, and only the 'status' field
    declarative_recall_config["metadata"] = {
        k: True
        for k, v in user_status[user].items()
        if v.get("status", False)
    }
    # Add user:true metadata
    declarative_recall_config["metadata"][user] = True
    log.critical(f'metadata: {str(declarative_recall_config["metadata"])}')
    return declarative_recall_config


@hook
def before_rabbithole_stores_documents(docs, cat):

    user = cat.user_id
    user_status_path = "cat/static/user_status.json"
    with open(user_status_path, "r") as file:
        user_status = json.load(file)
    # Only include tags with status True, and only the 'status' field
    metadata_for_upload = {
        k: True
        for k, v in user_status[user].items()
        if v.get("status", False)
    }
    # Add user:true metadata
    metadata_for_upload[user] = True

    for doc in docs:
        doc.metadata.update(metadata_for_upload)
        cat.send_ws_message(f"{str(metadata_for_upload)}", "chat")

    return docs
