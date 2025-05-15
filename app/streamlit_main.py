import os
import tempfile
import streamlit as st
from pdf2john import get_pdf_hash
from subprocess import Popen, PIPE
from pikepdf import Pdf
import time
import re
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

def parse_hashcat_progress(line):
    """解析hashcat输出的进度信息"""
    if 'Progress' in line:
        match = re.search(r'Progress\.+:\s+(\d+)%\s+\((\d+)/(\d+)\)', line)
        if match:
            return int(match.group(1))
    return None

def crack_pdf_hash(hash_str, pdf_name, mask="?d", min_len=4, max_len=8):
    logger = PdfLogger(pdf_name)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(hash_str.encode())
        tmp_path = tmp.name
        log_info(f'创建临时文件: {tmp_path}')
    
    # 按照不同PDF版本的hash模式依次尝试
    hash_modes = [
        ('10500', 'PDF 1.4 - 1.6 (Acrobat 5 - 8)'),
        ('10700', 'PDF 1.7 Level 8 (Acrobat 10 - 11)'),
        ('10600', 'PDF 1.7 Level 3 (Acrobat 9)'),
        ('10400', 'PDF 1.1 - 1.3 (Acrobat 2 - 4)')
    ]
    
    try:
        Config.validate()  # 验证hashcat是否存在
        log_info('hashcat验证通过')
        
        for mode, desc in hash_modes:
            st.write(f'🔍 尝试模式: {desc}')
            log_info(f'开始尝试模式: {desc}')
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_area = st.empty()
            error_log = st.empty()
            
            cmd = [
                str(Config.HASHCAT_BIN),
                '-d', '1',
                '-m', mode,
                '-a', '3',
                '--increment',
                '--increment-min', str(min_len),
                '--increment-max', str(max_len),
                tmp_path,
                mask,
                '--potfile-disable',
                '--status',
                '--status-timer', '1',
                '-w', '4',  # 工作负载配置文件
                '--force',  # 忽略警告
                '-O'  # 优化内核以减少内存使用
            ]
            
            # 记录开始执行的命令
            log_info(f'开始执行模式 {desc}')
            log_command(cmd, '开始执行...')
            
            process = Popen(cmd, stdout=PIPE, stderr=PIPE, text=True, bufsize=1, cwd=str(Config.HASHCAT_DIR))
            start_time = time.time()
            log_info(f'进程启动时间: {datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")}')
            
            # 收集完整的输出
            output_lines = []
            error_output = []
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                # 收集所有输出
                output_lines.append(line.strip())
                
                # 收集错误信息
                if 'ERROR' in line or 'FAILED' in line or 'WARNING' in line:
                    error_output.append(line.strip())
                    error_log.text('⚠️ ' + '\n'.join(error_output))
                    log_error(f'Mode {desc}: {line.strip()}')
                
                # 更新进度
                progress = parse_hashcat_progress(line)
                if progress is not None:
                    progress_bar.progress(progress / 100)
                    elapsed = time.time() - start_time
                    status_msg = f'进度: {progress}% | 已用时间: {elapsed:.1f}秒'
                    status_text.text(status_msg)
                    log_info(status_msg)
                
                # 显示详细日志
                if 'Speed' in line:
                    speed = re.search(r'Speed\.+:\s+([\d.]+ .H/s)', line)
                    if speed:
                        speed_msg = f'当前破解速度: {speed.group(1)}'
                        log_area.text(speed_msg)
                        log_info(speed_msg)
                elif 'Recovered' in line:
                    recovered = re.search(r'Recovered\.+:\s+(\d+)/(\d+)', line)
                    if recovered and recovered.group(1) != '0':
                        success_msg = f'✅ 使用模式 {desc} 破解成功！'
                        st.success(success_msg)
                        log_info(success_msg)
                        password = None
                        with open(tmp_path, 'r') as f:
                            for line in f:
                                if ':' in line:
                                    password = line.split(':')[-1].strip()
                                    log_info(f'找到密码: {password}')
                                    break
                        # 记录完整输出
                        log_command(cmd, '\n'.join(output_lines))
                        return password
            
            # 记录完整输出
            log_command(cmd, '\n'.join(output_lines))
            
            # 显示失败原因
            if error_output:
                error_msg = f'❌ 模式 {desc} 失败原因：\n' + '\n'.join(error_output)
                st.error(error_msg)
                log_error(error_msg)
            else:
                msg = f'❌ 模式 {desc} 尝试失败，切换到下一个模式'
                st.warning(msg)
                log_info(msg)
        
        msg = '❌ 所有模式都尝试失败'
        st.error(msg)
        log_error(msg)
        return None
    except FileNotFoundError as e:
        msg = f'❌ 错误：{str(e)}'
        st.error(msg)
        log_error(msg)
        return None
    except Exception as e:
        msg = f'❌ 未知错误：{str(e)}'
        st.error(msg)
        log_error(msg)
        return None
    finally:
        log_info(f'删除临时文件: {tmp_path}')
        os.unlink(tmp_path)

def decrypt_pdf(input_file, password, output_file):
    try:
        log_info(f'开始解密PDF文件: {input_file}')
        with Pdf.open(input_file, password=password) as pdf:
            pdf.save(output_file)
            pdf.remove_all_restrictions()
            log_info(f'PDF解密成功，已保存到: {output_file}')
    except Exception as e:
        msg = f'❌ PDF解密失败：{str(e)}'
        st.error(msg)
        log_error(msg)

def main():
    st.title("📄 PDF解锁工具")
    uploaded_file = st.file_uploader("上传PDF文件", type="pdf")
    
    if uploaded_file:
        with st.spinner('⏳ 正在生成哈希...'):
            hash_str = get_pdf_hash(uploaded_file.getvalue())
            
        if hash_str:
            st.success("✅ 哈希生成成功！")
            with st.expander("查看哈希详情"):
                st.code(hash_str)
            
            # 在破解按钮前添加新的UI组件
            mask_presets = {
                '纯数字': '?d',  # 0-9
                '小写字母': '?l',  # a-z
                '大写字母': '?u',  # A-Z
                '字母（大小写）': '?a',  # a-zA-Z
                '字母数字': '?h',  # a-zA-Z0-9
                '特殊字符': '?s',  # 特殊字符(!@#$等)
                '全部字符': '?b',  # 所有可能字符
                '自定义': ''
            }
            
            col1, col2 = st.columns(2)
            with col1:
                min_len = st.number_input('最小密码长度', 1, 48, 4)
            with col2:
                max_len = st.number_input('最大密码长度', 1, 48, 8)
            
            selected_mask = st.selectbox('预设掩码模式', options=list(mask_presets.keys()))
            custom_mask = st.text_input('自定义掩码模式', disabled=(selected_mask != '自定义'))
            pr
            if st.button("🚀 开始破解"):
                final_mask = custom_mask if selected_mask == '自定义' else mask_presets[selected_mask]
                with st.spinner('⚡ 正在破解中...'):
                    password = crack_pdf_hash(hash_str, final_mask, min_len, max_len)
                    
                if password:
                    st.balloons()
                    st.success(f"🎉 破解成功！密码是: {password}")
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                        decrypt_pdf(uploaded_file, password, tmp.name)
                        with open(tmp.name, 'rb') as f:
                            st.download_button(
                                "📥 下载解密后的PDF",
                                f.read(),
                                file_name="decrypted.pdf",
                                mime="application/pdf"
                            )
        else:
            msg = "⚠️ 该PDF未加密或格式异常"
            st.warning(msg)
            log_error(msg)

if __name__ == "__main__":
    main()