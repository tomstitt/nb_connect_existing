from __future__ import absolute_import

from traitlets import Instance

from zmq.eventloop import ioloop
from tornado.concurrent import Future
from tornado import gen
from jupyter_client.client import KernelClient
from jupyter_client.ioloop.manager import as_zmqstream


class IOLoopKernelClient(KernelClient):
    """Client for existing kernel for use with Notebooks

    Methods copied from jupyter_client.manager.KernelManager
    and jupyter_client.ioloop.manager.IOLoopKerenlManager

    TODO: restarting the kernel results in errors
    """
    loop = Instance('tornado.ioloop.IOLoop')

    _restarter = None

    def _loop_default(self):
        return ioloop.IOLoop.current()

    def start_restarter(self):
        pass

    def stop_restarter(self):
        pass

    def remove_restart_callback(self, *args, **kwargs):
        pass

    def add_restart_callback(self, *args, **kwargs):
        pass

    def request_shutdown(self, restart=False):
        pass

    def shutdown_kernel(self, now=False, restart=False):
        pass

    def finish_shutdown(self, waittime=1, pollinterval=0.1):
        pass

    def interrupt_kernel(self):
        pass

    def cleanup(self, connection_file=True):
        pass

    @gen.coroutine
    def get_kernel_info(self, timeout=10):
        future = Future()
        loop = ioloop.IOLoop.current()

        def cleanup():
            loop.remove_timeout(to)
            if not shell.closed():
                shell.close()

        def on_recv(msg):
            self.log.warning("Received kernel_info_reply from existing kernel")
            cleanup()
            if not future.done():
                future.set_result(msg)

        def on_timeout():
            self.log.warning("Timeout waiting for kernel_info_reply from existing kernel")
            cleanup()
            if not future.done():
                future.set_exception(gen.TimeoutError("Timeout trying to connect to existing kernel"))

        shell = self.connect_shell()
        self.session.send(shell, "kernel_info_request")
        shell.on_recv(on_recv)
        to = loop.add_timeout(loop.time() + timeout, on_timeout)

        res = yield future
        raise gen.Return(res)

    connect_shell = as_zmqstream(KernelClient.connect_shell)
    connect_iopub = as_zmqstream(KernelClient.connect_iopub)
    connect_stdin = as_zmqstream(KernelClient.connect_stdin)
    connect_hb = as_zmqstream(KernelClient.connect_hb)
    connect_control = as_zmqstream(KernelClient.connect_control)
