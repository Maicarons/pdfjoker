import os
import tempfile
import streamlit as st
from pdf2john import get_pdf_hash
from subprocess import run, Popen, PIPE
from pikepdf import Pdf
import time
import re

def parse_hashcat_progress(line):
    """解析hashcat输出的进度信息"""
    if 'Progress' in line:
        match = re.search(r'Progress\.+:\s+(\d+)%\s+\((\d+)/(\d+)\)', line)
        if match:
            return int(match.group(1))
    return None

def crack_pdf_hash(hash_str, mask="?d", min_len=4, max_len=8):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(hash_str.encode())
        tmp_path = tmp.name
    
    # 按照不同PDF版本的hash模式依次尝试
    hash_modes = [
        ('10500', 'PDF 1.7 Level 8 (Acrobat 10 - 11)'),
        ('10700', 'PDF 1.7 Level 3 (Acrobat 9)'),
        ('10600', 'PDF 1.7 Level 3 (Acrobat 8)'),
        ('10400', 'PDF 1.1 - 1.3 (Acrobat 2 - 4)')
    ]
    
    try:
        for mode, desc in hash_modes:
            st.write(f'🔍 尝试模式: {desc}')
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_area = st.empty()
            
            cmd = [
                'hashcat',
                '-m', mode,
                '-a', '3',
                '--increment',
                '--increment-min', str(min_len),
                '--increment-max', str(max_len),
                tmp_path,
                mask,
                '--potfile-disable',
                '--status',
                '--status-timer', '1'
            ]
            
            process = Popen(cmd, stdout=PIPE, stderr=PIPE, text=True, bufsize=1)
            start_time = time.time()
            
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                # 更新进度
                progress = parse_hashcat_progress(line)
                if progress is not None:
                    progress_bar.progress(progress / 100)
                    elapsed = time.time() - start_time
                    status_text.text(f'进度: {progress}% | 已用时间: {elapsed:.1f}秒')
                
                # 显示详细日志
                if 'Speed' in line:
                    speed = re.search(r'Speed\.+:\s+([\d.]+ .H/s)', line)
                    if speed:
                        log_area.text(f'当前破解速度: {speed.group(1)}')
                elif 'Recovered' in line:
                    recovered = re.search(r'Recovered\.+:\s+(\d+)/(\d+)', line)
                    if recovered and recovered.group(1) != '0':
                        st.success(f'✅ 使用模式 {desc} 破解成功！')
                        password = None
                        with open(tmp_path, 'r') as f:
                            for line in f:
                                if ':' in line:
                                    password = line.split(':')[-1].strip()
                                    break
                        return password
            
            st.warning(f'❌ 模式 {desc} 尝试失败，切换到下一个模式')
            
        st.error('❌ 所有模式都尝试失败')
        return None
    finally:
        os.unlink(tmp_path)

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
            st.warning("⚠️ 该PDF未加密或格式异常")

if __name__ == "__main__":
    main()

def decrypt_pdf(input_path, password, output_path):
    with Pdf.open(input_path, password=password) as pdf:
        pdf.save(output_path)
        pdf.remove_all_restrictions()