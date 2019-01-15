import setuptools

distname = "nb_connect_existing"

setuptools.setup(
    name=distname,
    packages=[distname],
    include_package_data=True,
    data_files=[
        ("share/jupyter/nbextensions/%s" % distname, [
            "%s/static/index.js" % distname,
        ]),
        ("etc/jupyter/nbconfig/tree.d", [
            "etc/jupyter/nbconfig/tree.d/%s.json" % distname
        ]),
        ("etc/jupyter/jupyter_notebook_config.d", [
            "etc/jupyter/jupyter_notebook_config.d/%s.json" % distname
        ])
    ],
    zip_safe=False
)
