
from pyxunlei.pyxunlei import XunLeiClient


if __name__ == "__main__":
    xunlei_client = XunLeiClient(
        '192.168.2.137', 2345, device_name="群晖-xunlei")
    # print(xunlei_client._torrent2magnet(
    #     "))
    xunlei_client.download_torrent('/Users/kanhui/Downloads/ubuntu-23.04-live-server-amd64.iso.torrent')
