"""smtp"""

import os
import traceback

from datacontract.iscoutdataset import IscoutTask
from .zgrab2scannerbase import Zgrab2ScannerBase
from ..zgrab2parser import Zgrab2ParserSMTP
from .....clientdatafeedback.scoutdatafeedback import PortInfo


class Zgrab2ScannerSMTP(Zgrab2ScannerBase):
    """zgrab2 http scanner"""

    def __init__(self, zgrab_path: str):
        Zgrab2ScannerBase.__init__(self, "zgrab2smtp")
        self._parser: Zgrab2ParserSMTP = Zgrab2ParserSMTP()

    def get_banner_smtp(
        self,
        task: IscoutTask,
        level,
        portinfo: PortInfo,
        *args,
        zgrab2path: str = "zgrab2",
        sudo: bool = False,
        timeout: float = 600,
    ) -> iter:
        """scan smtp services and get the banner"""
        hostfi = None
        outfi = None
        try:
            port: int = portinfo._port
            if not isinstance(port, int) or port < 0 or port > 65535:
                raise Exception("Invalid port: {}".format(port))

            hosts: list = [portinfo._host]
            for h in portinfo.hostnames:
                if h not in hosts:
                    hosts.append(h)
            for d in portinfo.domains:
                if d not in hosts:
                    hosts.append(d)

            hostfi = self._write_hosts_to_file(task, hosts)
            if hostfi is None:
                return

            outfi = self._scan_smtp(
                task,
                level,
                hostfi,
                port,
                *args,
                zgrab2path=zgrab2path,
                sudo=sudo,
                timeout=timeout,
            )
            if outfi is None or not os.path.isfile(outfi):
                return

            self._parser.parse_banner(task, level, portinfo, outfi)

        except Exception:
            self._logger.error("Scan mssql error: {}".format(traceback.format_exc()))
        finally:
            if not hostfi is None and os.path.isfile(hostfi):
                os.remove(hostfi)
            if not outfi is None and os.path.isfile(outfi):
                os.remove(outfi)

    def _scan_smtp(
        self,
        task: IscoutTask,
        level,
        host_file: str,
        port: int,
        *args,
        zgrab2path: str = "zgrab2",
        sudo: bool = False,
        timeout: float = 600,
    ) -> str:
        """scan smtp
        """
        outfi: str = None
        try:
            enhanced_args = []

            # add hosts and ports to args
            enhanced_args.append("smtp")
            enhanced_args.append(f"-p {port}")
            # zgrab2 smtp --send-ehlo --ehlo-domain="mail.example.com" --starttls --keep-client-logs -f host.txt -o smtp3.json
            enhanced_args.append(f"-t {timeout}")

            if not "--send-ehlo" in args:
                enhanced_args.append("--send-ehlo")
            if not "--ehlo-domain=" in args:
                enhanced_args.append('--ehlo-domain="mail.example.com"')
            if not "--keep-client-logs" in args:
                enhanced_args.append("--keep-client-logs")

            # 这个args里面几乎没有东西，除非真的是外面有特殊说明这个才有值，所以还是先留在这里
            enhanced_args.extend(args)

            if port == 25 and not "--starttls" in enhanced_args:
                enhanced_args.append("--starttls")
                if "--smtps" in enhanced_args:
                    enhanced_args.remove("--smtps")
            elif port == 465 and not "--smtps" in enhanced_args:
                # although it have scanned tls certificate in advance,
                # here should scan it again in order to check if the
                # certificate is different from the one previously scanned.
                enhanced_args.append("--smtps")
                if "--starttls" in enhanced_args:
                    enhanced_args.remove("--starttls")

            if "--input-file=" not in args or "-f" not in args:
                enhanced_args.append(f"-f {host_file}")  # input file

            outfi = os.path.join(self._tmpdir, "{}_{}.smtp".format(task.batchid, port))
            if "--output-file=" not in args or "-o" not in args:
                # here must use -o, use '--output-file' will cause exception 'No such file or directory'
                # this may be a bug
                # 人家没说可以用--output-file
                enhanced_args.append(f"-o {outfi}")  # output file

            # 如果没有当前文件夹那么就创建当前文件夹
            outdir = os.path.dirname(outfi)
            if not os.path.exists(outdir) or not os.path.isdir(outdir):
                os.makedirs(outdir)

            curr_process = None
            try:

                curr_process = self._run_process(
                    zgrab2path, *enhanced_args, rootDir=outdir, sudo=sudo
                )
                stdout, stderr = curr_process.communicate(timeout=timeout)
                exitcode = curr_process.wait(timeout=timeout)
                if stdout is not None:
                    self._logger.trace(stdout)
                if stderr is not None:
                    self._logger.trace(stderr)
                if exitcode != 0:
                    raise Exception(f"Scan smtp error: {stdout}\n{stderr}")
                self._logger.info(
                    f"Scan smtp exitcode={str(exitcode)}\ntaskid:{task.taskid}\nbatchid:{task.batchid}\nport:{port}"
                )
            finally:
                if curr_process is not None:
                    curr_process.kill()
        except Exception:
            if outfi is not None and os.path.isfile(outfi):
                os.remove(outfi)
            outfi = None
            self._logger.info(
                f"Scan smtp exitcode={str(exitcode)}\ntaskid:{task.taskid}\nbatchid:{task.batchid}\nport:{port}"
            )

        return outfi
