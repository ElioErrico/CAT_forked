from cat.mad_hatter.decorators import hook,tool
from .helper import aggiorna_users_tags

@hook  # default priority = 1
def after_cat_bootstrap(cat):

    aggiorna_users_tags()

