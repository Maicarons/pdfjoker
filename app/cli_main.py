import argparse
import os
from pathlib import Path
from pdf2john import get_pdf_hash
from subprocess import run
from pikepdf import Pdf
from config import Config
from datetime import datetime

class PdfLogger:
    def __init__(self, pdf_name):
        self.log_file = Config.get_pdf_log_path(pdf_name)
        # 确保日志目录存在
        self.log_file.parent.mkdir(exist_ok=True)
        # 创建日志文件并写入开始信息
        with open(self.log_file, 'w', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f'[{timestamp}] 开始处理PDF文件: {pdf_name}\n')
    
    def info(self, msg):
        """记录普通日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f'[{timestamp}] {msg}\n')
    
    def error(self, error_msg):
        """记录错误日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f'[{timestamp}] ERROR: {error_msg}\n')
    
    def command(self, cmd, output):
        """记录命令和输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f'\n[{timestamp}] 执行命令: {" ".join(cmd)}\n')
            f.write(f'[{timestamp}] 命令输出:\n{output}\n')

def crack_pdf_hash(hash_str, pdf_name, mask="?d"):
    logger = PdfLogger(pdf_name)
    try:
        Config.validate()  # 验证hashcat是否存在
        logger.info('hashcat验证通过')
        
        # 按照不同PDF版本的hash模式依次尝试
        hash_modes = [
            ('10500', 'PDF 1.7 Level 8 (Acrobat 10 - 11)'),
            ('10700', 'PDF 1.7 Level 3 (Acrobat 9)'),
            ('10600', 'PDF 1.7 Level 3 (Acrobat 8)'),
            ('10400', 'PDF 1.1 - 1.3 (Acrobat 2 - 4)')
        ]
        
        logger.info('创建临时哈希文件')
        with open('temp_hash.txt', 'w') as f:
            f.write(hash_str)
        
        for mode, desc in hash_modes:
            print(f'🔍 尝试模式: {desc}')
            logger.info(f'开始尝试模式: {desc}')
            
            cmd = [
                str(Config.HASHCAT_BIN),
                '-m', mode,
                '-a', '3',
                '--increment',
                '--increment-min', '4',
                '--increment-max', '8',
                'temp_hash.txt',
                mask,
                '--potfile-disable',
                '-w', '4',  # 工作负载配置文件
                '--force',  # 忽略警告
                '-O'  # 优化内核以减少内存使用
            ]
            
            # 记录开始执行的命令
            logger.info(f'开始执行模式 {desc}')
            logger.command(cmd, '开始执行...')
            
            start_time = time.time()
            logger.info(f'进程启动时间: {datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")}')
            
            result = run(cmd, capture_output=True, text=True, cwd=str(Config.HASHCAT_DIR))
            
            # 记录完整输出
            logger.command(cmd, result.stderr + '\n' + result.stdout)
            
            # 检查错误输出
            error_lines = [line for line in result.stderr.split('\n') 
                          if 'ERROR' in line or 'FAILED' in line or 'WARNING' in line]
            
            if 'Status...........: Cracked' in result.stderr:
                msg = f'✅ 使用模式 {desc} 破解成功！'
                print(msg)
                logger.info(msg)
                with open('temp_hash.txt', 'r') as f:
                    for line in f:
                        if ':' in line:
                            password = line.split(':')[-1].strip()
                            logger.info(f'找到密码: {password}')
                            return password
            
            # 显示失败原因
            if error_lines:
                print(f'❌ 模式 {desc} 失败原因：')
                for error in error_lines:
                    error_msg = f'  ⚠️ {error.strip()}'
                    print(error_msg)
                    logger.error(f'Mode {desc}: {error.strip()}')
            else:
                msg = f'❌ 模式 {desc} 尝试失败，切换到下一个模式'
                print(msg)
                logger.info(msg)
            
            # 显示性能信息
            for line in result.stderr.split('\n'):
                if 'Speed' in line:
                    speed_msg = f'📊 {line.strip()}'
                    print(speed_msg)
                    logger.info(f'性能信息: {line.strip()}')
        
        msg = '❌ 所有模式都尝试失败'
        print(msg)
        logger.error(msg)
        return None
    except FileNotFoundError as e:
        msg = f'❌ 错误：{str(e)}'
        print(msg)
        logger.error(msg)
        return None
    except Exception as e:
        msg = f'❌ 未知错误：{str(e)}'
        print(msg)
        logger.error(msg)
        return None
    finally:
        if os.path.exists('temp_hash.txt'):
            logger.info('删除临时哈希文件')
            os.remove('temp_hash.txt')

def decrypt_pdf(input_file, password, output_file):
    try:
        log_info(f'开始解密PDF文件: {input_file}')
        with Pdf.open(input_file, password=password) as pdf:
            pdf.save(output_file)
            pdf.remove_all_restrictions()
            log_info(f'PDF解密成功，已保存到: {output_file}')
    except Exception as e:
        msg = f'❌ PDF解密失败：{str(e)}'
        print(msg)
        log_error(msg)

def main():
    parser = argparse.ArgumentParser(description='PDF解密工具')
    parser.add_argument('input', help='输入PDF文件路径')
    parser.add_argument('-o', '--output', help='输出PDF文件路径')
    parser.add_argument('-m', '--mask', default='?d', help='密码掩码模式')
    args = parser.parse_args()
    
    # 记录启动参数
    log_info('程序启动')
    log_info(f'启动参数: input={args.input}, output={args.output}, mask={args.mask}')
    
    input_path = Path(args.input)
    if not input_path.exists():
        msg = f'❌ 错误：输入文件 {input_path} 不存在'
        print(msg)
        log_error(msg)
        return
    
    output_path = Path(args.output) if args.output else input_path.with_name(f'{input_path.stem}_decrypted{input_path.suffix}')
    
    print('正在生成哈希...')
    log_info('开始生成PDF哈希')
    with open(input_path, 'rb') as f:
        hash_str = get_pdf_hash(f.read())
    
    if not hash_str:
        msg = '⚠️ 该PDF未加密或格式异常'
        print(msg)
        log_info(msg)
        return
    
    # 记录生成的哈希
    log_info(f'生成的PDF哈希:\n{hash_str}')
    
    print('开始破解...')
    log_info('开始破解PDF密码')
    password = crack_pdf_hash(hash_str, args.mask)
    
    if password:
        msg = f'🎉 破解成功！密码是: {password}'
        print(msg)
        log_info(msg)
        print('正在解密PDF...')
        decrypt_pdf(input_path, password, output_path)
        msg = f'✅ 解密完成！文件已保存到: {output_path}'
        print(msg)
        log_info(msg)
    else:
        msg = '❌ 破解失败'
        print(msg)
        log_error(msg)
    
    log_info('程序结束')

if __name__ == '__main__':
    main()