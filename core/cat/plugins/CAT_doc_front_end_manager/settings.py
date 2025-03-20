import json
import os
from pydantic import BaseModel, Field
from typing import List
from cat.mad_hatter.decorators import plugin
from .helper import aggiorna_users_tags

def get_default_tags():
    # Percorso del file tags.json del CAT
    root_dir = os.environ.get("CCAT_ROOT", os.getcwd())
    tags_path = os.path.join(root_dir, "cat/static/tags.json")
    
    try:
        with open(tags_path, "r") as f:
            tags_data = json.load(f)
            return tags_data.get("tags", ["tag_1", "tag_2", "tag_3"])  # Fallback to default if not found
    except (FileNotFoundError, json.JSONDecodeError):
        return ["tag_1", "tag_2", "tag_3"]  # Default if file doesn't exist or is invalid

class TagSettings(BaseModel):
    tag_list: List[str] = Field(
        default_factory=get_default_tags,
        description="Lista di tag. Modifica e salva per sovrascrivere cat/static/tags.json",
        json_schema_extra={
            "ui": {
                "input_type": "tag_input",  # Changed from textarea to tag_input
                "help": "Inserisci i tag uno per uno e premi Enter dopo ogni tag"
            }
        }
    )

@plugin
def settings_schema():
    return TagSettings.schema()

@plugin
def save_settings(settings: dict):
    # Percorso del file tags.json del CAT
    root_dir = os.environ.get("CCAT_ROOT", os.getcwd())
    tags_path = os.path.join(root_dir, "cat/static/tags.json")
    
    try:
        # Get the tag list from settings
        tag_list = settings.get("tag_list", [])
        
        # Ensure tag_list is a list
        if not isinstance(tag_list, list):
            if isinstance(tag_list, str):
                # Try to parse as JSON if it's a string
                try:
                    tag_list = json.loads(tag_list)
                except json.JSONDecodeError:
                    # If not valid JSON, split by comma and strip whitespace
                    tag_list = [tag.strip() for tag in tag_list.split(",") if tag.strip()]
            else:
                raise ValueError("tag_list must be a list or a string")
        
        # Remove any empty tags
        tag_list = [tag for tag in tag_list if tag]
        
        # Create the object with the "tags" property containing the list
        tags_object = {"tags": tag_list}
        
        # Write the object to the file
        with open(tags_path, "w") as f:
            json.dump(tags_object, f, indent=4)
        
        aggiorna_users_tags()
        return {"success": True, "message": "Tags updated successfully"}
            
    except Exception as e:
        error_msg = f"Error updating {tags_path}: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg}