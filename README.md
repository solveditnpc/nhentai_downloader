# NHentai Manga Downloader
#### Video Demo: https://youtu.be/JIGcwnKR7Os
#### Description:

This project is a Python-based command-line tool that allows users to download manga from NHentai. It features robust error handling, asynchronous downloads for better performance, and a clean, modular design that makes the code maintainable and testable.

## Project Structure

The project consists of several key files:

### project.py
This is the main file containing the core functionality:

- `extract_manga_id(url)`: Extracts the manga ID from various URL formats using regex pattern matching. It handles different URL patterns and provides clear error messages for invalid URLs.
- `safe_format_filename(name)`: Sanitizes filenames by removing illegal characters and enforcing length limits. This ensures downloaded files have valid names across different operating systems.
- `fetch_manga_images(manga_id)`: An asynchronous function that retrieves image URLs from multiple servers. It implements retry logic and server fallbacks for reliability.
- `download_images(manga_id, image_urls, download_folder)`: Handles the actual downloading of images with proper error handling and progress reporting.
- `download_manga(url)`: The high-level function that orchestrates the entire download process.
- `main()`: Reads URLs from a configuration file and processes them sequentially.

### test_project.py
Contains comprehensive test cases for the core functions:
- Tests for URL parsing with various formats
- Tests for filename sanitization including edge cases
- Tests for error handling in the download process

### requirements.txt
Lists all project dependencies with specific versions for reproducibility:
- run on python 3.10.0
- httpx for async HTTP requests
- nhentai for parsing
- beautifulsoup4 for HTML parsing
- Other supporting libraries

## Design Choices

1. **Asynchronous Downloads**: I chose to use async/await patterns with httpx instead of traditional synchronous downloads because:
   - It significantly improves download speeds for multiple images
   - Provides better resource utilization
   - Allows for concurrent downloads while maintaining code readability

2. **Modular Function Design**: Each function has a single responsibility, making the code:
   - Easier to test
   - More maintainable
   - Simpler to debug and modify

3. **Error Handling**: Comprehensive error handling is implemented at multiple levels:
   - URL validation
   - Network request failures
   - File system operations
   - This ensures the program fails gracefully and provides useful feedback

4. **File Management**: The project includes robust file management features:
   - Automatic creation of download directories
   - Safe filename generation
   - Proper file extension handling

## Future Improvements

Potential enhancements could include:
- Adding a graphical user interface
- Implementing download progress bars
- Adding support for batch downloads from text files
- Implementing resume functionality for interrupted downloads

## How to Use

1. Install dependencies for linux:
```bash
install python 3.10.0(use pyenv for linux) and create a virtual environment
python -m venv venv_nhentai_Py3.10.0
source venv_nhentai_Py3.10.0/bin/activate
```

```bash
pip install -r requirements.txt
```

2. Run the program:
```bash
python project.py
```

3. Add URLs to download in constants.txt, one per line.

## Testing

Run the tests using pytest:
```bash
pytest test_project.py -v
```
