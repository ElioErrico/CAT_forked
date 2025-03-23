from pydantic import BaseModel
from cat.mad_hatter.decorators import plugin
from pydantic import BaseModel, Field, field_validator
from.helper import aggiorna_users_tags, aggiorna_users_tags_solo_nuovi

class MySettings(BaseModel):
    add_new_users: bool =False

@plugin
def settings_schema():
    aggiorna_users_tags_solo_nuovi()
    return MySettings.schema()
