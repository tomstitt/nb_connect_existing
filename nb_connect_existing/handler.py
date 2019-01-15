import uuid
import json
import os

from tornado import gen
from ipython_genutils.py3compat import unicode_type
from jupyter_client.connect import find_connection_file
from notebook.base.handlers import IPythonHandler

from .manager import IOLoopKernelClient
from .tunnel import open_ssh_tunnel, TunnelError


class ConnectExistingHandler(IPythonHandler):
    def finish_error(self, status, msg):
        self.log.error(msg)
        self.set_status(status)
        self.set_header("Content-Type", "application/json")
        self.finish(json.dumps(dict(message=msg)))

    @gen.coroutine
    def post(self):
        model = self.get_json_body()

        if model is None: model = {}
        conn_file = model.get("conn_file", "kernel-*.json")
        server = model.get("server", "localhost")

        # not currently used
        timeout = model.get("timeout", 5)

        # validate transport protocol
        transport = model.get("transport", "ipc")
        if transport != "ipc" and transport != "tcp":
            return self.finish_error(400, "Invalid transport protocol '%s'" % transport)

        # validate port
        try:
            port = int(model.get("port", 22))
        except ValueError:
            return self.finish_error(400, "Invalid port '%s'" % model["port"])
        if port < 0 or port > 65535:
            return self.finish_error(400, "Port out of range [0, 65535]: %d" % port)

        basename = os.path.basename(conn_file)
        dirname = os.path.dirname(conn_file)

        # verify that the connection file actually exists
        try:
            conn_file = find_connection_file(basename, None if dirname == "" else dirname)
            self.log.info("Found connection file: %s" % conn_file)
        except IOError as e:
            return self.finish_error(404, str(e))

        # create kernel
        self.log.info("Connecting to existing %s" % conn_file)
        # Possible to get kernel_name from connection file: kernel_name=kernel_name
        kernel = IOLoopKernelClient(parent=self.kernel_manager, log=self.kernel_manager.log)
        kernel.load_connection_file(conn_file)
        # used when tunneling to get socket path
        kernel.connection_file = conn_file

        if server != "localhost":
            self.log.info("This kernel isn't on localhost, trying to open ssh tunnels")
            try:
                open_ssh_tunnel(self.log, kernel, server, transport=transport, ssh_port=port)
            except TunnelError as e:
                return self.finish_error(500, "Unable to create tunnel: %s" % str(e))
            # it's easier to debug without this
            #except Exception as e:
            #    return self.finish_error(500, "unknown error: %s" % str(e))

        # try to connect to kernel/get kernel info
        try:
            kernel_info = yield gen.maybe_future(kernel.get_kernel_info(timeout=timeout))
        except Exception as e:
            return self.finish_error(404, str(e))

        # create notebook file
        try:
            nb_model = self.contents_manager.new_untitled(type="notebook")
        except Exception as e:
            return self.finish_error(500, str(e))

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
            return self.finish_error(500, str(e))

        # respond with new info
        self.set_status(201)
        self.set_header('Content-Type', 'application/json')
        self.finish(json.dumps({
            "kernel": kernel_model,
            "session": session_model,
            "notebook": {"path": nb_model["path"]}}))

handlers = [("/existing", ConnectExistingHandler)]
