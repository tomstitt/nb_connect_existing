# Notebook Connect Existing

Jupyter Notebook tree (front page) extension that lets you connect to existing kernels.
An ssh tunnel can be automatically created for non-local kernels but for now the host with the kernel
must be visable from the host of the notebook and either a) accessible with passwordless ssh or b)
accessible via munge rsh to the kernel host and passwordless ssh back to the notebook host.

(out-of-date)
![demo](demo.gif)

## Install

```shell
pip install .
```

## Helpful links

[Distributing Jupyter Extensions as Python Packages - Server Extension](https://jupyter-notebook.readthedocs.io/en/stable/examples/Notebook/Distributing%20Jupyter%20Extensions%20as%20Python%20Packages.html#Example---Server-extension)

[Custom request handlers - Writing a notebook server extension](https://jupyter-notebook.readthedocs.io/en/stable/extending/handlers.html#writing-a-notebook-server-extension)
