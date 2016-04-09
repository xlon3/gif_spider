# -*- coding:utf-8 -*-

import re
import os
from bs4 import BeautifulSoup
import requests
from multiprocessing import Process, Queue, Pool, Manager
from collections import namedtuple

Gif = namedtuple('Gif', ['path', 'url'])

BaseUrl = 'http://www.ali213.net/news/bxgif/'
BasePath = 'e:/bxgif/'


class GetGifUrl:
    def __init__(self, base_url, base_path, page_cnt):
        self.base_url = base_url
        self.base_path = base_path
        self.page_cnt = page_cnt

    def mkdir(self, path):
        path = path.strip()
        if not os.path.exists(path):
            os.makedirs(path)

    def get_gif_url(self, url_q, gif_q):
        while True:
            url = ''
            try:
                url = url_q.get(block=True, timeout=10)
            except:
                print('no more urls')
                return

            page = requests.get(url).content
            soup = BeautifulSoup(page, "html.parser", from_encoding='utf-8')

            # 先获取下一页入url队列
            next_node = soup.find('a', id='after_this_page', text='下一页')
            if next_node is not None:
                url_prefix = url[:url.rfind('/')+1]
                next_url = url_prefix + next_node['href']
                url_q.put(next_url)

            # 将当前页gif存入gif队列
            dir_name = url.split('/')[-2]
            path = self.base_path + dir_name + '/'
            self.mkdir(path)
            for gif in soup.find_all('img', src=re.compile('http.*sina.*\.gif')):
                queue_item = Gif(path, gif['src'])
                gif_q.put(queue_item)

    def get_first_url(self, url_q):
        for cnt in range(self.page_cnt):
            real_url = ''
            if cnt == 0:
                real_url = self.base_url
            else:
                real_url = self.base_url + str(cnt+1) + '.html'
            page = requests.get(real_url).content
            soup = BeautifulSoup(page, "html.parser", from_encoding='utf-8')
            for url_node in soup.find_all('a', href=re.compile('http.*\.html'), text='阅读全文'):
                url_q.put(url_node['href'])


header = {
    'Host': 'ww1.sinaimg.cn',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.110 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en-US,en;q=0.8,fr;q=0.6,zh-CN;q=0.4',
    'Referer': 'http://www.ali213.net/news/bxgif/'
}


def get_url_proc(url_q, gif_q, page_cnt=10):
    print('begin get gif url')
    process = GetGifUrl(BaseUrl, BasePath, page_cnt)
    process.get_first_url(url_q)
    process.get_gif_url(url_q, gif_q)


def download_gif(gif_q):
    print('download_gif start')
    while True:
        item = None
        try:
            item = gif_q.get(timeout=10)
        except:
            print('no more gifs')
            return
        file_name = item.path + item.url.split('/')[-1]
        if os.path.exists(file_name):
            continue
        print('save %s as %s' % (item.url, file_name))
        r = requests.get(item.url, headers=header)
        data = r.content
        with open(file_name, 'wb') as f:
            f.write(data)


if __name__ == "__main__":
    url_queue = Queue()
    manage = Manager()
    gif_queue = manage.Queue()
    # Pool
    p_get_url = Process(name='get_url_process', target=get_url_proc, args=(url_queue, gif_queue, 20))
    p_get_url.start()

    p = Pool(4)
    for i in range(4):
        p.apply_async(download_gif, args=(gif_queue,))

    p.close()
    p.join()
    p_get_url.join()

