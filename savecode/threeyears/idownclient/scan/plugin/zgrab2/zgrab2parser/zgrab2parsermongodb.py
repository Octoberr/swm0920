"""
parser mongodb
create by judy 2019/11/19
"""

import json
import os
import traceback

from commonbaby.mslog import MsLogger, MsLogManager

from datacontract.iscandataset.iscantask import IscanTask
from idownclient.clientdatafeedback.scoutdatafeedback.portinfo import (MongoDB,
                                                                       PortInfo
                                                                       )

from .zgrab2parserbase import Zgrab2ParserBase


class Zgrab2ParserMongodb(Zgrab2ParserBase):
    """zgrab2 parser"""

    # _logger: MsLogger = MsLogManager.get_logger("Zgrab2Parsermongodb")

    def __init__(self):
        # self._name = type(self).__name__
        Zgrab2ParserBase.__init__(self)

    def parse_banner_mongodb(self, task: IscanTask, level: int, pinfo_dict, resultfi: str):
        """
        Parse mongodb banner information
        """
        try:
            if not os.path.isfile(resultfi):
                self._logger.error(
                    f"Resultfi not exists:\ntaskid:{task.taskid}\nresultfi:{resultfi}"
                )
                return

            # its' one json object per line

            linenum = 1
            with open(resultfi, mode='r') as fs:
                while True:
                    try:
                        line = fs.readline()
                        if line is None or line == '':
                            break

                        sj = json.loads(line)
                        if sj is None:
                            continue
                        ip = sj.get('ip')
                        if ip is None or pinfo_dict.get(ip) is None:
                            self._logger.error("Unexpect error, cant get ip info from zgrab2 result")
                            continue
                        portinfo = pinfo_dict.get(ip)

                        res = self._parse_mongodb(sj, task, level, portinfo)
                        # 如果成功了则证明已经将mongodb的信息解析出来了就不用再继续解析了
                        if res:
                            break
                    except Exception:
                        self._logger.error(
                            "Parse one mongodb banner json line error:\ntaskid:{}\nresultfi:{}\nlinenum:{}"
                            .format(task.taskid, resultfi, linenum))
                    finally:
                        linenum += 1

        except Exception:
            self._logger.error(
                "Parse mongodb banner error:\ntaskid:{}\nresultfi:{}"
                .format(task.taskid, resultfi))

    def _parse_mongodb(self, sj: dict, task: IscanTask, level: int, portinfo: PortInfo):
        """
        解析mongodb的banner和一些其他的信息
        总之就是port里的信息
        :param sj:
        :param task:
        :param level:
        :param portinfo:
        :return:
        """
        res = False
        if not sj.__contains__("data") or not sj["data"].__contains__(
                "mongodb"):
            return
        try:
            sjmongodb = sj['data']['mongodb']
            succ = sjmongodb["status"]
            if succ != "success":
                return

            protocol = sjmongodb["protocol"]
            if protocol != "mongodb":
                return

            if portinfo.service != protocol:
                portinfo.service = protocol

            self._get_port_timestamp(sjmongodb, portinfo)

            # 开始构建mongodb的banner

            mres = sjmongodb.get('result')
            if mres is None:
                return
            mdata = MongoDB()
            ismaster = mres.get('is_master')
            mdata.is_master = ismaster
            buildinfo = mres.get('build_info')
            mdata.build_info = buildinfo
            # 因为port里面有version，所以对version赋值
            version = buildinfo.get('version')
            portinfo.version = version

            portinfo.banner = mdata.build_banner()
            # mongodb的banner
            mdata.banner = portinfo.banner
            res = True
            portinfo.set_mongodb(mdata)

        except:
            self._logger.error(
                f"Parse mongodb protocal error, err:{traceback.format_exc()}")
        return res
