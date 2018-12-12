from notebook.utils import url_path_join

from .handler import handlers


def _jupyter_server_extension_paths():
    return [{
        "module": "nb_connect_existing"
    }]


def _jupyter_nbextension_paths():
    return [{
        "section": "tree",
        "src": "static",
        "dest": "nb_connect_existing",
        "require": "nb_connect_existing/index"
    }]


def load_jupyter_server_extension(nbapp):
    host_pattern = '.*$'
    base_url = nbapp.web_app.settings["base_url"]

    # add in the base url
    updated_handlers = []
    for handler in handlers:
        pattern = url_path_join(base_url, handler[0])
        updated_handlers.append(tuple([pattern] + list(handler[1:])))
    nbapp.web_app.add_handlers(host_pattern, updated_handlers)
