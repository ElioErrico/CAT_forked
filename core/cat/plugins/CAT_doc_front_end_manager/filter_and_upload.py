from cat.mad_hatter.decorators import hook
import json

@hook  # default priority = 1
def before_cat_recalls_declarative_memories(declarative_recall_config, cat):
    # filter memories using custom metadata. 
    # N.B. you must add the metadata when uploading the document! 

    user=cat.user_id
    user_status_path="cat/static/user_status.json"
    file=open(user_status_path, "r")
    user_status=json.load(file)

    declarative_recall_config["metadata"] = user_status[user]
    # cat.send_ws_message(f"{str(user_status[user])}","chat")

    return declarative_recall_config


@hook
def before_rabbithole_stores_documents(docs, cat):

    user=cat.user_id
    user_status_path="cat/static/user_status.json"
    file=open(user_status_path, "r")
    user_status=json.load(file)
    metadata_for_upload = user_status[user]

    for doc in docs:
        doc.metadata.update(metadata_for_upload)

        # cat.send_ws_message(f"{str(metadata_for_upload)}","chat")

    return docs