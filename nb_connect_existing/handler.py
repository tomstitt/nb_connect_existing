import uuid
import json
import os

from tornado import gen
from ipython_genutils.py3compat import unicode_type
from jupyter_client.connect import find_connection_file
from notebook.base.handlers import IPythonHandler
from notebook.utils import url_path_join, url_escape

from .manager import IOLoopKernelClient
from .tunnel import open_ssh_tunnel, TunnelError


class ConnectExistingHandler(IPythonHandler):
    def finish_error(self, status, msg):
        self.log.error(msg)
        self.set_status(status)
        self.set_header("Content-Type", "application/json")
        self.finish(json.dumps(dict(message=msg)))

    @gen.coroutine
    def create_manager(self):
        conn_file = self.get_argument("conn_file", "kernel-*.json")
        server = self.get_argument("server", "localhost")
        timeout = self.get_argument("timeout", 5)
        transport = self.get_argument("transport", "ipc")
        port = self.get_argument("port", 22)

        # validate
        if transport != "ipc" and transport != "tcp":
            self.finish_error(400, "Invalid transport protocol %s" % transport)
            return
        try:
            port = int(port)
        except ValueError:
            self.finish_error(400, "Invalid port %s" % port)
            return
        if port < 0 or port > 65535:
            self.finish_error(400, "Port out of range [0, 65535]: %d" % port)
            return

        basename = os.path.basename(conn_file)
        dirname = os.path.dirname(conn_file)

        # verify that the connection file actually exists
        try:
            conn_file = find_connection_file(basename, None if dirname == "" else dirname)
            self.log.info("Found connection file: %s" % conn_file)
        except IOError as e:
            self.finish_error(404, str(e))
            return

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
                self.finish_error(500, "Unable to create tunnel: %s" % str(e))
                return
            # it's easier to debug without this
            #except Exception as e:
            #    return self.finish_error(500, "unknown error: %s" % str(e))

        # try to connect to kernel/get kernel info
        try:
            kernel_info = yield gen.maybe_future(kernel.get_kernel_info(timeout=timeout))
        except Exception as e:
            self.finish_error(404, str(e))
            return

        # create notebook file
        try:
            nb_model = self.contents_manager.new_untitled(type="notebook")
        except Exception as e:
            self.finish_error(500, str(e))
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
            self.finish_error(500, str(e))
            return

        raise gen.Return(url_path_join(self.base_url, "notebooks", url_escape(nb_model["path"])))

    @gen.coroutine
    def post(self):
        try:
            url = yield gen.maybe_future(self.create_manager())
            # respond with new info
            self.set_status(201)
            self.set_header('Content-Type', 'application/json')
            self.finish(json.dumps({"path": url}))
        except:
            pass

    @gen.coroutine
    def get(self):
        try:
            url = yield gen.maybe_future(self.create_manager())
            self.redirect(url)
        except:
            pass


handlers = [("/existing", ConnectExistingHandler)]
