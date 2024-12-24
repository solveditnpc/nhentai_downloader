import pytest
from project import extract_manga_id, safe_format_filename, download_manga

def test_extract_manga_id():
    # Test valid URLs
    assert extract_manga_id("https://nhentai.net/g/123456/") == "123456"
    assert extract_manga_id("https://nhentai.net/g/123456") == "123456"
    assert extract_manga_id("123456") == "123456"
    
    # Test invalid URLs
    with pytest.raises(ValueError):
        extract_manga_id("https://nhentai.net/invalid/url")

def test_safe_format_filename():
    # Test normal strings
    assert safe_format_filename("Test File") == "Test File"
    assert safe_format_filename("Test/File:*?") == "TestFile"
    
    # Test edge cases
    assert safe_format_filename("") == ""
    assert safe_format_filename(None) == ""
    
    # Test long filename
    long_name = "a" * 300
    assert len(safe_format_filename(long_name)) == 255

def test_download_manga():
    # Test invalid URL
    assert download_manga("https://nhentai.net/invalid/url") is None
    
    # Test non-existent manga ID
    assert download_manga("https://nhentai.net/g/999999999") is None
