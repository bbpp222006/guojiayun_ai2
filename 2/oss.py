import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider

from itertools import islice
import os
import logging
import time
import random
from config import *
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')




class OSSClient:
    def __init__(self):
        # 设置环境变量
        os.environ['OSS_ACCESS_KEY_ID'] = OSS_ACCESS_KEY_ID
        os.environ['OSS_ACCESS_KEY_SECRET'] = OSS_ACCESS_KEY_SECRET

        # 从环境变量中获取访问凭证
        auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())

        # 设置Endpoint和Region
        self.endpoint = "oss-cn-wuhan-lr.aliyuncs.com"
        self.region = "cn-wuhan-lr"

        self.bucket_name = "test-11451"
        self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name, region=self.region)


    # 上传本地文件到 OSS，并返回对应的 URL
    def upload_local_file_to_oss(self,local_file_path):
        try:
            # 获取文件名
            file_name = os.path.basename(local_file_path)
            # 读取文件数据
            with open(local_file_path, 'rb') as file_data:
                # 上传文件
                result = self.bucket.put_object(file_name, file_data)
                logging.info(f"File uploaded successfully, status code: {result.status}")
                # 返回文件的 URL
                file_url = f"https://{self.bucket_name}.{self.endpoint}/{file_name}"
                return file_url
        except Exception as e:
            logging.error(f"Failed to upload file {local_file_path}: {e}")
            return None

    # 删除所有云端资源（删除所有对象和 Bucket）
    def delete_all_resources(self):
        try:
            # 列出所有对象并删除
            objects = list(oss2.ObjectIterator(self.bucket))
            for obj in objects:
                self.bucket.delete_object(obj.key)
                logging.info(f"Deleted object: {obj.key}")
            
            # 删除 Bucket
            # bucket.delete_bucket()
            # logging.info(f"Bucket {bucket_name} deleted successfully")
        except oss2.exceptions.OssError as e:
            logging.error(f"Failed to delete resources: {e}")

# 主流程
if __name__ == '__main__':
    oss_client = OSSClient()
    # url = oss_client.upload_local_file_to_oss( r"test.txt")
    # print(url)
    oss_client.delete_all_resources()
