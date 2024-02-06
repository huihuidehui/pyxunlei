# pyxunlei
基于Docker版本的[Xunlei API Client](https://github.com/cnk3x/xunlei)
## 支持版本
仅在3.7.1版本中测试通过

## 使用方法
可以使用pip安装 `pip install pyxunlei -i https://pypi.python.org/simple`
```
from pyxunlei import XunleiClient
#  初始化时支持以下参数:
#  host (str): 域名或IP
#  port (int): 端口号
#  ssl (bool): 是否启动HTTPS
#  device_name (str): 设备名称，当同一个账号下绑定了多个远程迅雷，可指定设备名称，设备名称可在迅雷APP查看
#      例如：群晖-xunlei
#      device_name为空时使用第一个设备.
#  download_root_dir(str): 下载根目录的目录名称，可以在web页面上查看，如不填写则默认选择第一个(一般是迅雷下载)
xunlei_client = XunLeiClient(
        '192.168.2.137', 2345, device_name="群晖-xunlei")

# 获取已完成任务列表
completed_tasks = xunlei_client.completed_tasks()

# 获取未完成任务列表
uncompleted_tasks = xunlei_client.uncompleted_tasks()

# 提交磁力链接
magnetic_link = "磁力链接"
sub_dir = "子目录"  # 为空时则不创建子目录
preprocess_file = xunlei_client.filter_file_by_size  # 指定预处理文件函数，可使用内置的filter_file_by_size过滤掉小于500M以及大于40G的文件
xunlei_client.download_magnetic(magnetic_link, sub_dir, preprocess_file)

# 提交种子链接
torrent_file_path = "your.torrent"  # 种子文件路径
xunlei_client.download_torrent(torrent_file_path, sub_dir, preprocess_file)

```

