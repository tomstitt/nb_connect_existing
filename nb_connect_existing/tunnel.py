#
# tunnel.py
#
# tunnel.py helps to ssh tunnel between a client and a server on LC
# Sockets can be IP-based or IPC-based
#

from __future__ import print_function
import socket
import os
import getpass
import time
import errno
import pexpect
from subprocess import Popen, DEVNULL
from zmq.ssh.tunnel import select_random_ports
from jupyter_core.paths import jupyter_runtime_dir


localhost = socket.gethostname()
runtime_dir = jupyter_runtime_dir()
port_names = ["hb_port", "stdin_port", "shell_port", "iopub_port", "control_port"]
connection_refused = "Connection refused"
unknown_host = "Are you sure you want to continue connecting"
auth_fail = "Authentication failed."
permission_denied = "Permission Denied."
ssh_cmd = "ssh -S none -nT -{fwd_flg} {fwd_args} -p {ssh_port} {server} sleep {sleep}"
mrsh_cmd = "mrsh {server} {ssh_cmd}"


class TunnelError(RuntimeError):
    pass


def ssh_tunnel(logger, mode, ltransport, lport, rtransport, rport, server, user,
        ssh_port, sleep_duration=30, silent=True):
    """Open ssh tunnel from lport on localhost to rport on server

    ssh -{L|R} {<local port>|<local socket>}:{<host>:<remote port>|<remote socket>}

    <host> is always localhost for now.

    The local port is always local to the starting machine even though it is 
    referred to as the remote in the ssh docs in the -R case.
    """
    if rtransport == "tcp":
        forwarding_args = "%s:%s:%s" % (lport, "localhost", rport)
    else:
        forwarding_args = "%s:%s" % (lport, rport)

    # remove the local ipc socket if it exists, might be
    # better to pick a unique name
    if ltransport == "ipc" and os.path.exists(lport):
        os.remove(lport)

    if mode == "ssh":
        cmd = ssh_cmd.format(fwd_flg="L", fwd_args=forwarding_args,
                server=server, ssh_port=ssh_port, sleep=sleep_duration)
    elif mode == "mrsh":
        cmd = mrsh_cmd.format(server=server, ssh_cmd=ssh_cmd.format(
            fwd_flg="R", fwd_args=forwarding_args, server=localhost,
            ssh_port=ssh_port, sleep=sleep_duration))
    else:
        raise TunnelError("Unknown mode %s" % mode)

    if silent:
        args = dict(stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL)
    else:
        args = {}

    logger.info("starting ssh tunnel> %s" % cmd)
    # TODO: this can fail
    Popen(cmd.split(), close_fds=True, preexec_fn=os.setpgrp, **args)


def try_ssh(logger, server, port, env, timeout=2):
    cmd = "ssh -p %d %s true" % (port, server)
    logger.info("Testing ssh> %s" % cmd)
    with pexpect.spawn(cmd, env=env, timeout=timeout) as p:
        index = p.expect([pexpect.EOF, connection_refused, unknown_host, auth_fail, pexpect.TIMEOUT])
    if index == 0:
        if len(p.before) == 0:
            return True
        else:
            raise TunnelError(p.before)
    elif index == 1:
        # try mrsh
        #raise TunnelError("Connection refused")
        return False
    elif index == 2:
        raise TunnelError("Host authenticity can't be established")
    elif index == 3:
        raise TunnelError("Authenication failed")
    elif index == 4:
        raise TunnelError("Timeout trying to tunnel to host")
    return False


def try_mrsh(logger, server, port, env, timeout=2):
    cmd = "mrsh %s ssh -p %d %s true" % (server, port, localhost)
    logger.info("Testing mrsh> %s" % cmd)
    with pexpect.spawn(cmd, env=env, timeout=2) as p:
        index = p.expect([pexpect.EOF, connection_refused, permission_denied, pexpect.TIMEOUT])
    if index == 0:
        if len(p.before) == 0:
            return True
        else:
            raise TunnelError(p.before)
    elif index == 1:
        raise TunnelError("Premission Refused")
    elif index == 2:
        raise TunnelError("Unable to connect to localhost after mrsh to %s" % server)
    #elif index == 3:
    #    raise TunnelError("Authenication failed")
    elif index == 3:
        raise TunnelError("Timeout connecting back to localhost after mrsh to %s" % server)
    return False


def open_ssh_tunnel(logger, kernel, server, user=getpass.getuser(), transport=None, ssh_port=22,
        password=None, timeout=5):
    """Try to create ssh tunnels from localhost to server

    Try to create a a) passwordless ssh tunnel from localhost to server or b) munge rsh to server
    and create a passwordless reverse ssh tunnel from server to localhost.
    The transport protocol on localhost and server may differ if needed.
    """
    # server must be visable for now
    try:
        server_info = socket.gethostbyaddr(server)
    except socket.herror:
        raise TunnelError("host %s is inaccessible" % server)

    # make sure the kernel isn't on localhost
    if server_info[0] == "localhost":
        logger.info("kernel on localhost - nothing to do")
        return
    
    # no gui password prompt
    env = os.environ.copy()
    env.pop("SSH_ASKPASS", None)

    if try_ssh(logger, server, ssh_port, env):
        mode = "ssh"
    elif try_mrsh(logger, server, ssh_port, env):
        mode = "mrsh"
    else:
        raise TunnelError("Unable to connect, tried ssh and mrsh")

    # remote ports are the ports for the machine hosting the kernel
    if kernel.transport == "ipc":
        ssh_remote_ports = ["%s-%s" % (kernel.ip, getattr(kernel, name)) for name in port_names]
    elif kernel.transport == "tcp":
        ssh_remote_ports = [getattr(kernel, name) for name in port_names]
    else:
        raise TunnelError("Unsupported protocol %s on kernel-side" % kernel.transport)

    # local ports are the ports for machine hosting the notebook server
    if transport is None:
        transport = kernel.transport

    if transport == "ipc":
        ip = "%s-ipc-%s" % (os.path.splitext(kernel.connection_file)[0], localhost)
        # TODO: with ipc the sockets in ssh_local_port may already be in use
        new_kernel_ports = [getattr(kernel, name) for name in port_names]
        ssh_local_ports = ["%s-%d" % (ip, port) for port in new_kernel_ports]

    elif transport == "tcp":
        ip = "127.0.0.1"
        ssh_local_ports = select_random_ports(len(port_names))
        new_kernel_ports = ssh_local_ports
    else:
        raise TunnelError("Unsupported protocol %s on client-side" % transport)

    logger.info("attempting to create tunnels from %s@%s to %s@%s" % (transport, localhost,
        kernel.transport, server))

    for lport, rport in zip(ssh_local_ports, ssh_remote_ports):
        ssh_tunnel(logger, mode, ltransport=transport, lport=lport,
                rtransport=kernel.transport, rport=rport,
                server=server, user=user, ssh_port=ssh_port)

    # update the kernel object's transport, ip, and ports
    kernel.transport = transport
    kernel.ip = ip
    for name, port in zip(port_names, new_kernel_ports):
        setattr(kernel, name, port)
