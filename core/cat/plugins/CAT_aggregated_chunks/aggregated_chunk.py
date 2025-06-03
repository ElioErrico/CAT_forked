from cat.mad_hatter.decorators import hook,plugin
from langchain.docstore.document import Document

from cat.log import log


@hook
def after_rabbithole_splitted_text(chunks, cat):
    settings = cat.mad_hatter.get_plugin().load_settings()
    
    if settings.get("enable_classification", True):  # Default to True if not set
        # Define classification labels
        classification_labels = {
            "useful": ["relevant", "important", "useful", "meaningful"],
            "no sense": ["nonsense", "gibberish", "random", "unclear"],
            "header or footer": ["copyright", "footer", "header", "page number", "confidential"]
        }
        filtered_chunks = []
        for chunk in chunks:
            classification = cat.classify(chunk.page_content, labels=classification_labels)
            cat.send_ws_message(classification)
            if classification in ["useful"]:
                filtered_chunks.append(chunk)
    else:
        filtered_chunks = chunks  # Skip classification if disabled

    # Original aggregation logic on filtered chunks
    concatenated_chunks_list = []
    settings = cat.mad_hatter.get_plugin().load_settings()
    n_of_chunks = settings["n_of_chunks"]

    for i in range(0, len(filtered_chunks), n_of_chunks):
        chunk_group = filtered_chunks[i:i + n_of_chunks]
        concatenated_content = ''.join(chunk.page_content for chunk in chunk_group)
        concatenated_chunks_list.append(concatenated_content)        
        concatenated_new_document = Document(page_content=concatenated_content)
        filtered_chunks.append(concatenated_new_document)
    
    return filtered_chunks
