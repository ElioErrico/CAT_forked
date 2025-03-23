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
    user_status[user][user] = True
    # cat.send_ws_message(f"{str(user_status[user])}","chat")

    declarative_recall_config["metadata"] = user_status[user]
    # cat.send_ws_message(f"{str(user_status[user])}","chat")

    return declarative_recall_config


@hook
def before_rabbithole_stores_documents(docs, cat):
    # This hook function runs before documents are stored in the rabbithole
    # It adds user-specific metadata to each document being uploaded

    # Get the current user's ID from the cat object
    user=cat.user_id
    # Define the path to the user status JSON file
    user_status_path="cat/static/user_status.json"
    # Open the user status file for reading
    file=open(user_status_path, "r")
    # Load the JSON data from the file
    user_status=json.load(file)
    # Extract the metadata specific to the current user
    metadata_for_upload = user_status[user]
    metadata_for_upload[user] = True
    
    
    # cat.send_ws_message(f"{str(metadata_for_upload)}","chat")
    # Iterate through each document that's being uploaded
    for doc in docs:
        # Update each document's metadata with the user-specific metadata
        # This allows for filtering documents by user-specific attributes later
        doc.metadata.update(metadata_for_upload)

        # Debugging line (commented out) that would send metadata to the chat interface
        # cat.send_ws_message(f"{str(metadata_for_upload)}","chat")

    # Return the modified documents with updated metadata
    return docs