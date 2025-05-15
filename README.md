# PDFJoker - PDF Automation Decryption Toolkit

## Features

- **Automated PDF Processing**: Fully automated workflow for handling PDF files
- **Password Recovery**: 
  - Generates PDF hashes for password recovery
  - Integrates with hashcat for efficient password cracking
- **PDF Decryption**: Automatically decrypts PDFs once password is recovered
- **Restriction Removal**:
  - Removes all PDF usage restrictions
  - Eliminates watermarks from documents
- **Dual Interface**:
  - Command Line Interface (CLI) for scriptable operations
  - Streamlit-based Web UI for interactive use
- **Real-time Monitoring**: Processing progress visible in real-time through UI
- **Download Ready**: Provides download links for processed files
- **Extensible Design**: Includes placeholder functions for future enhancements

## Usage

### CLI Mode
```bash
python app/cli_main.py input.pdf -o output.pdf
```

### Web UI Mode
```bash
streamlit run app/streamlit_main.py
```

The web interface will open in your default browser where you can:
1. Upload PDF files
2. Monitor processing in real-time
3. Download the processed files

## License
GNU Affero General Public License v3.0 (AGPL-3.0)