from pathlib import Path
import platform
import os
from datetime import datetime

class Config:
    # 获取项目根目录
    ROOT_DIR = Path(__file__).parent.parent
    
    # 日志目录
    LOG_DIR = ROOT_DIR / 'logs'
    ERROR_LOG = LOG_DIR / 'error.log'
    
    @classmethod
    def get_pdf_log_path(cls, pdf_name):
        """获取PDF文件的日志路径"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = ''.join(c if c.isalnum() else '_' for c in pdf_name)
        return cls.LOG_DIR / f'{safe_name}_{timestamp}.log'
    
    # hashcat相关路径
    HASHCAT_DIR = ROOT_DIR / 'bin' / ('win' if platform.system() == 'Windows' else 'linux') / 'hashcat
    HASHCAT_BIN = HASHCAT_DIR / ('hashcat.exe' if platform.system() == 'Windows' else 'hashcat.bin')
    HASHCAT_KERNELS = HASHCAT_DIR / 'OpenCL'
    
    @classmethod
    def validate(cls):
        """验证配置是否正确"""
        # 创建日志目录
        cls.LOG_DIR.mkdir(exist_ok=True)
        
        # 验证hashcat是否存在
        if not cls.HASHCAT_BIN.exists():
            raise FileNotFoundError(f'hashcat可执行文件不存在：{cls.HASHCAT_BIN}')
        
        # 验证kernels目录是否存在
        if not cls.HASHCAT_KERNELS.exists():
            raise FileNotFoundError(f'hashcat kernels目录不存在：{cls.HASHCAT_KERNELS}')