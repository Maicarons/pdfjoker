import argparse
from pdf2john import get_pdf_hash
from config import Config
from streamlit_main import crack_pdf_hash, decrypt_pdf

def main():
    parser = argparse.ArgumentParser(description='PDF解锁命令行工具')
    parser.add_argument('input', help='输入PDF文件路径')
    parser.add_argument('-o', '--output', required=True, help='解密后的输出路径')
    parser.add_argument('-m', '--mask', default='?a?a?a?a?a', help='密码掩码模式')
    
    args = parser.parse_args()
    
    try:
        with open(args.input, 'rb') as f:
            hash_str = get_pdf_hash(f.read())
            
        if not hash_str:
            print("错误：文件未加密或格式异常")
            return
            
        password = crack_pdf_hash(hash_str, args.mask)
        
        if password:
            decrypt_pdf(args.input, password, args.output)
            print(f"解密成功！文件保存至：{args.output}")
        else:
            print("破解失败，请尝试其他掩码组合")
    except Exception as e:
        print(f"发生错误：{str(e)}")

if __name__ == "__main__":
    main()