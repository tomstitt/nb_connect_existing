import uuid
import json
import os

from tornado import gen
from ipython_genutils.py3compat import unicode_type
from jupyter_client.connect import find_connection_file
from notebook.base.handlers import IPythonHandler

from .manager import IOLoopKernelClient


class ConnectExistingHandler(IPythonHandler):
    @gen.coroutine
    def post(self, path):
        basename = os.path.basename(path)
        dirname = os.path.dirname(path)

        # verify that the connection file actually exists
        try:
            conn_file = find_connection_file(basename, None if dirname == "" else dirname)
            self.log.info("Found connection file: %s" % conn_file)
        except IOError as e:
            msg = str(e)
            self.log.error(msg)
            self.set_status(404)
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps(dict(message=msg)))
            return

        # create kernel
        self.log.info("Connecting to existing %s" % conn_file)
        # Possible to get kernel_name from connection file: kernel_name=kernel_name
        kernel = IOLoopKernelClient(parent=self.kernel_manager, log=self.kernel_manager.log)
        kernel.load_connection_file(conn_file)

        # try to connect to kernel/get kernel info
        try:
            kernel_info = yield gen.maybe_future(kernel.get_kernel_info(timeout=5))
        except Exception as e:
            msg = str(e)
            self.log.error(msg)
            self.set_status(404)
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps(dict(message=msg)))
            return

        # create notebook file
        try:
            nb_model = self.contents_manager.new_untitled(type="notebook")
        except Exception as e:
            msg = str(e)
            self.log.error(msg)
            self.set_status(500)
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps(dict(message=msg)))
            return

        # TODO: handle kernel name
        # kernel_name is not known by the existing kernel (maybe in the conn file)
        # so we need a way to look it up, otherwise the user is asked to pick a kernel
        # OR the .ipynb doesn't have the correct metadata.kernelspec info
        # could use default kernel:
        #  from jupyter_client.kernelspec import NATIVE_KERNEL_NAME
        #  kernel_name = NATIVE_KERNEL_NAME
        self.log.debug(kernel_info)
        kernel_name = ""
        kernel.kernel_name = kernel_name

        # add to kernel manager
        kernel_id = unicode_type(uuid.uuid4())
        self.log.info("Adding existing kernel with id %s" % kernel_id)
        self.kernel_manager._kernels[kernel_id] = kernel
        self.kernel_manager._kernel_connections[kernel_id] = 0
        self.kernel_manager.start_watching_activity(kernel_id)
        kernel_model = self.kernel_manager.kernel_model(kernel_id)

        # create session
        try:
            session_model = yield gen.maybe_future(self.session_manager.create_session(path=nb_model["path"],
            name=kernel_name, kernel_id=kernel_id, type="notebook"))
        except Exception as e:
            self.kernel_manager.shutdown_kernel(kernel_id, now=True)
            msg = str(e)
            self.log.error(msg)
            self.set_status(500)
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps(dict(message=msg)))
            return

        # respond with new info
        self.set_status(201)
        self.set_header('Content-Type', 'application/json')
        self.finish(json.dumps({
            "kernel": kernel_model,
            "session": session_model,
            "notebook": {"path": nb_model["path"]}}))

handlers = [("/existing/%s" % r"(.+)", ConnectExistingHandler)]
