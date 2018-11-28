import setuptools

setuptools.setup(
    name="NBConnectExisting",
    packages=["nb_connect_existing"],
    include_package_data=True,
    data_files=[
        # like `jupyter nbextension install --sys-prefix`
        ("share/jupyter/nbextensions/nb_connect_existing", [
            "nb_connect_existing/static/index.js",
        ]),
        # like `jupyter nbextension enable --sys-prefix`
        ("etc/jupyter/nbconfig/tree.d", [
            "etc/jupyter/nbconfig/tree.d/nb_connect_existing.json"
        ]),
        # like `jupyter serverextension enable --sys-prefix`
        ("etc/jupyter/jupyter_notebook_config.d", [
            "etc/jupyter/jupyter_notebook_config.d/nb_connect_existing.json"
        ])
    ],
    zip_safe=False
)
