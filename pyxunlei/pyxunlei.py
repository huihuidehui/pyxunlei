from datetime import datetime
import hashlib
from io import BufferedReader, BytesIO
import json
import sys
import time
from typing import List
from urllib.parse import quote
from loguru import logger
from pydantic import BaseModel
import requests
from torrentool.api import Torrent

logger.remove()
logger.add(sys.stderr, level="INFO")


class TaskInfo(BaseModel):
    name: str
    file_name: str
    file_size: int
    updated_time: datetime
    progress: int
    real_path: str   # 路径
    speed: int
    created_time: datetime
    origin: dict  # api原始返回内容


class TaskFile(BaseModel):
    index: int
    file_name: str
    file_size: int


class NotLoginXunLeiAccount(Exception):
    pass


class PanAuthInvalid(Exception):
    pass


class XunLeiClient():
    def __init__(self, host: str, port: int, ssl: bool = False, device_name: str = '', download_root_dir: str = ''):
        """

        Args:
            host (str): 域名或IP
            port (int): 端口号
            ssl (bool): 是否启动HTTPS
            device_name (str): 设备名称，当同一个账号下绑定了多个远程迅雷，可指定设备名称，设备名称可在迅雷APP查看
                例如：群晖-xunlei
                device_name为空时使用第一个设备.
            download_root_dir(str): 下载根目录的目录名称，可以在web页面上查看，如不填写则默认选择第一个(一般是迅雷下载)
        """
        # logger.disable("*")

        self._session = requests.Session()
        self._api = f"{'https' if ssl else 'http'}://{host}:{port}"
        # 获取device_id
        response = self._session.get(
            f"{self._api}/webman/3rdparty/pan-xunlei-com/index.cgi/drive/v1/tasks?type=user%23runner&device_space=", headers=self.headers)
        if response.status_code == 500:
            raise NotLoginXunLeiAccount(response.json().get('error'))
        if response.json().get('error_code') == 403:
            raise PanAuthInvalid('params: pan_auth gen error')
        tasks = response.json().get('tasks')

        if len(tasks) == 0:
            raise ValueError(f'No remote device is bound')

        self._device_id = ""
        if device_name:
            for task in tasks:
                if task.get('name') == device_name:
                    self._device_id = task.get('params').get('target')
                    break
            if not self._device_id:
                raise ValueError(f"device_name {device_name} not found")
        else:
            if len(tasks) > 1:
                logger.warning(
                    f'Multiple remote devices are bound, using the first one {tasks[0].get("device_name")}')
            self._device_id = tasks[0].get('params').get('target')

        logger.debug(f'success get device id {self._device_id}')

        # 获取下载根目录 parent_folder_id
        self._parent_folder_id = None
        response = self._session.get(
            f"{self._api}/webman/3rdparty/pan-xunlei-com/index.cgi/drive/v1/files?space={quote(self._device_id)}&limit=200&parent_id=&filters=%7B%22kind%22%3A%7B%22eq%22%3A%22drive%23folder%22%7D%7D&page_token=&device_space=", headers=self.headers)

        if not download_root_dir:
            self._parent_folder_id = response.json().get('files')[
                0].get('parent_id')
            self._parent_folder_name = response.json().get('files')[
                0].get('name')
        else:
            for parent in response.json().get('files'):
                if parent.get('name') == download_root_dir:
                    self._parent_folder_id = parent.get('id')
                    self._parent_folder_name = parent.get('name')
                    break
        if not self._parent_folder_id:
            raise ValueError(
                f"download root dir {download_root_dir} not found")

        logger.debug(
            f'success get parent_folder_id {self._parent_folder_id} parent folder name is {self._parent_folder_name}')

    @property
    def headers(self):
        return {
            'pan-auth': self.pan_auth,
            'DNT': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'device-space': '',
            'content-type': 'application/json',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }

    @property
    def pan_auth(self):
        e = int(time.time())
        s = f"{e}yrjmxtpovrzzdqgtbjdncmsywlpmyqcaawbnruddxucykfebpkuseypjegajzzpplmzrejnavcwtvciupgigyrtomdljhtmsljegvutunuizvatwtqdjheituaizfjyfzpbcvhhlaxzfatpgongrqadvixrnvastczwnolznfavqrvmjseiosmvrtcqiapmtzjfihdysqmhaijlpsrssovkpqnjbxuwkhjpfxpoldvqrnlhgdbcpnsilsmydxaxrxjzbdekzmshputmgkedetrcbmcdgljfkpbprvqncixfkavyxoibbuuyqzvcbzdgvipozeplohmcyfornhxzsadavvimivbzexfzhlndddnbywhsvjrotwzarbycpwydvpeqtuigfwzcvoswgpoakuvgdbykdjdcsdlnqskogpbsyceeyaigbgmrbnzixethpvqvvfvdcvjbilxikvklfbkcnfprzhijjnuoovulvigiqvbosnbixeplvnewmyipxuzpvocbvidnzgsrdfkejghvvyizkjlofndcuzvlhdhovpeolsyroljurbplpwbbihmdloahicnqehgjnbthmrljtzovltnlpeibodpjvemhhybmanskbtvdrgkrzoyhsjcexfrcpddoemazkfjwmrbrcloitmdzzkgxwlhnbfpjffrpryljdzdqsbacrjgohzwgbvzgevnqvxppsxqzczfgpuvigjbuhzweyeinukeurkogpotdegqhtsztdinmijjowivciviunhcjhtufzhjlmpqlngslimksdeezdzxihtmaywfvipjctuealhlovmzdodruperyysdhwjbtidwdzusifeepywsmkqbknlgdhextvlheufxivphskqvdtbcjfryxlolujmennakdqjdhtcxwnhknhzlaatuhyofenhdigojyxrluijjxeywnmopsuicglfcqyybbpynpcsnizupumtakwwnjlkfkuooqoqxhjnryylklokmzvmmgjsbbvgmwoucpvzedmqpkmazwhhvxqygrexopkmcdyniqocguykphlngjesqohhuvnkcliuawkzcmvevdbouwzvgmhtavwyhstvqwhcwjluzjopnhuisbsrloavcieskcyqftdhieduduhowgvrkimgdhyszsiknmuzvnrqqlbykbdlixosgxrdunymbixakkmgppteayqmqivxcwawyidpltevotwoxlkrucmluuluatgeskhfsrsebhniwhujpwrpknjxylidtjwebvwmbwayoepootybnlcaoixlgvjmpquxnyomoiopsjxtnorhwnlmonllastiezyvfbbgngjybtgbkxuaqdmkuqwupgzhffuyzgdnahdifaqtfmpysnlesvfoiofxvbtqkiqvdniejbyzugbkursumqddaslhqpkdrjnnsdqfthxtghxhaylgeqnknhqwpammlfnlkjuqevnxesyqsnpufvrbeohphxfabcduuklpkfoiifsqrrbsxkkmdrnkeboprnksfzwmjymjspzsrfjlwneuwzjjwejruubhhqaktxhygtjuhjmtvrklrmxdbbwooxsucmynwgcxhzdctgtchaevmpfiqfwydultmgqnionuendspvdrcctxldnyjlgnsqxaddadxeyvlcifdxksgdhaatsslhcofnxmilljpzdlumfjvcwvjrxegwbwuuwkguydhozqqnuselsoojnsefquuhpijdguofwrcjbuaugyzphkenbyhdstsldybdqsfxjhpgnerbdosbtyzdtrhyvwkzkurnmbgjtzlzcpfsuxussguelnjttmwejhreptwogekfvdsemlkvklcxeuzlboqwbngddexhsmyzqkztvlbgybbfmzbjroajaucykiqvhjrirlgawaessusvulngosviecmbpfgevxqptalguchfzkrrpruwxspggiqokepqpocezcewhyajsgxrqqqeuhwvc"
        # 对s进行Md5
        md5 = hashlib.md5()
        md5.update(s.encode('utf-8'))
        return f"{e}.{md5.hexdigest()}"

    def completed_tasks(self) -> List[TaskInfo]:
        """获取所有已经完成的任务

        Returns:
            List: 任务列表
        """
        url = f"{self._api}/webman/3rdparty/pan-xunlei-com/index.cgi/drive/v1/tasks?space={quote(self._device_id)}&page_token=&filters=%7B%22phase%22%3A%7B%22in%22%3A%22PHASE_TYPE_COMPLETE%22%7D%2C%22type%22%3A%7B%22in%22%3A%22user%23download-url%2Cuser%23download%22%7D%7D&limit=200&device_space="
        data = self._session.get(url, headers=self.headers).json()
        tasks = data.get('tasks')
        if not tasks:
            return []
        res = []
        for task in tasks:
            progress =  task.get('progress') if task.get('progress') else 0
            res.append(TaskInfo(
                name=task.get('name'),
                file_name=task.get('name'),
                file_size=int(task.get('file_size')),
                updated_time=task.get('updated_time'),
                progress=progress,
                real_path=task.get('params').get('real_path'),
                speed=int(task.get('params').get('speed')),
                created_time=task.get('created_time'),
                origin=task
            ))
        return res

    def uncompleted_tasks(self) -> List[TaskInfo]:
        """获取未完成的任务

        Returns:
            List[TaskInfo]: _description_
        """
        url = f"{self._api}/webman/3rdparty/pan-xunlei-com/index.cgi/drive/v1/tasks?space={quote(self._device_id)}&page_token=&filters=%7B%22phase%22%3A%7B%22in%22%3A%22PHASE_TYPE_PENDING%2CPHASE_TYPE_RUNNING%2CPHASE_TYPE_PAUSED%2CPHASE_TYPE_ERROR%22%7D%2C%22type%22%3A%7B%22in%22%3A%22user%23download-url%2Cuser%23download%22%7D%7D&limit=200&device_space="
        data = self._session.get(url, headers=self.headers).json()
        tasks = data.get('tasks')
        if not tasks:
            return []
        res = []
        for task in tasks:
            progress =  task.get('progress') if task.get('progress') else 0
            res.append(TaskInfo(
                file_name=task.get('name'),
                name=task.get('name'),
                file_size=int(task.get('file_size')),
                updated_time=task.get('updated_time'),
                progress=progress,
                real_path=task.get('params').get('real_path'),
                speed=int(task.get('params').get('speed')),
                created_time=task.get('created_time'),
                origin=task
            ))
        return res

    def download_http_task(self) -> bool:
        """下载http连接
        暂不实现
        Returns:
            bool: _description_
        """
        return False

    def download_magnetic(self, magnetic_link: str, sub_dir: str = '', preprocess_files=None) -> int:
        """下载磁力链接

        Args:
            magnetic_link (str): 磁力链接
            sub_dir (str, optional): 子目录，不为空时将新建子目录下载 Defaults to ''.
            preprocess_files (_type_, optional): 添加任务的回调函数，会传入文件列表，要求返回文件列表.可以在此函数中实现过滤下载文件的操作 Defaults to None.

        Returns:
            int: 三种情况:
                0: 失败
                1: 成功
                2: 已存在跳过
        """

        # 提取文件 list
        url = f"{self._api}/webman/3rdparty/pan-xunlei-com/index.cgi/drive/v1/resource/list?device_space="
        body = {"urls": magnetic_link}
        response = self._session.post(
            url, headers=self.headers, data=json.dumps(body), timeout=60)
        data = response.json()
        task_name = data.get('list').get('resources')[0].get('name')

        # 需要先判断一下有没有该任务
        all_task_names = set(
            [i.name for i in self.completed_tasks() + self.uncompleted_tasks()])
        if task_name in all_task_names:
            return 2

        task_file_count = data.get('list').get(
            'resources')[0].get('file_count')
        task_files = []
        self._index = 0
        # 递归处理

        def helper(resources):
            for resource in resources:
                if resource.get('is_dir'):
                    helper(resource.get('dir').get('resources'))
                else:
                    task_files.append(
                        TaskFile(
                            index=self._index,
                            file_size=resource.get('file_size'),
                            file_name=resource.get('name')
                        )
                    )
                    self._index += 1
        root_resources = data.get('list').get('resources')
        helper(root_resources)
        if callable(preprocess_files):
            task_files = preprocess_files(task_files)
        sub_file_index = [str(i.index) for i in task_files]

        target_parent_id = self._parent_folder_id
        # 创建子目录
        if sub_dir:
            if "/" in sub_dir:
                logger.error("Multilevel subdirectories are not supported")
                return False
            body = {"parent_id": self._parent_folder_id, "name": sub_dir,
                    "space": self._device_id, "kind": "drive#folder"}
            response = self._session.post(
                f"{self._api}/webman/3rdparty/pan-xunlei-com/index.cgi/drive/v1/files?device_space=", headers=self.headers, data=json.dumps(body))
            target_parent_id = response.json().get('file').get('id')

        # 提交任务
        body = {"type": "user#download-url", "name": task_name, "file_name": task_name, "file_size": str(sum([i.file_size for i in task_files])), "space": self._device_id, "params": {
            "target": self._device_id, "url": magnetic_link, "total_file_count": str(task_file_count), "parent_folder_id": target_parent_id, "sub_file_index": ",".join(sub_file_index), "file_id": ""}}
        response = self._session.post(f"{self._api}/webman/3rdparty/pan-xunlei-com/index.cgi/drive/v1/task?device_space=",
                                      headers=self.headers, data=json.dumps(body))
        if response.json().get('HttpStatus') == 0:
            return 1
        else:
            return 0

    def download_torrent(self, torrent_file_path: str,sub_dir:str='',preprocess_files=None) -> int:
        """_summary_

        Args:
            torrent_file_path (str): _description_

        Returns:
            int: _description_
        """
        magnet_link = self._torrent2magnet(torrent_file_path)
        return self.download_magnetic(magnet_link,sub_dir,preprocess_files)

    def _torrent2magnet(self, file_path: str) -> str:
        """种子转磁力

        Args:
            torrent_body (bytes): _description_

        Returns:
            str: _description_
        """
        torrent = Torrent.from_file(file_path)
        trs = torrent.announce_urls

        trs = '&'.join([quote(tr[0]) for tr in trs])
        return torrent.magnet_link + "&" + trs

    def filter_file_by_size(self, task_files: List[TaskFile], min_size: int = 500 * 1024 * 1024, max_size: int = 40 * 1024 * 1024 * 1024) -> List[TaskFile]:
        """preprocess_files参数内置函数，通过文件大小过滤文件

        Args:
            task_files (List[TaskFile]): _description_
            min_size (int, optional): _description_. Defaults to 500*1024*1024.
            max_size (int, optional): _description_. Defaults to 40*1024*1024*1024.

        Returns:
            List[TaskFile]: _description_
        """
        if not task_files:
            return []
        return [i for i in task_files if min_size <= i.file_size <= max_size]
