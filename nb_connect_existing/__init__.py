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
    nbapp.web_app.add_handlers(host_pattern, handlers)
