import re
import os
import asyncio
import traceback
import httpx
from nhentai.parser import doujinshi_parser
from nhentai.logger import logger
from nhentai.utils import format_filename

def extract_manga_id(url):
    """
    Extract manga ID from nhentai URL
    
    :param url: Full URL of the manga on nhentai
    :return: Manga ID as a string
    """
    # Use regex to extract ID from various possible URL formats
    match = re.search(r'/g/(\d+)/?', url)
    if match:
        return match.group(1)
    
    # If no match found, try to use the last part of the URL
    parts = url.rstrip('/').split('/')
    for part in reversed(parts):
        if part.isdigit():
            return part
    
    raise ValueError(f"Could not extract manga ID from URL: {url}")

def safe_format_filename(name):
    """
    Safely format filename, handling None and empty string cases
    
    :param name: Input name to format
    :return: Formatted filename
    """
    if not name:
        return ''
    
    try:
        # Remove any characters that are not allowed in filenames
        sanitized_name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
        return sanitized_name[:255]  # Limit filename length
    except Exception:
        # Fallback to basic sanitization
        return re.sub(r'[<>:"/\\|?*]', '', name).strip()[:255]

async def fetch_manga_images(manga_id):
    """
    Fetch manga image URLs using multiple i-named servers and extensions
    
    :param manga_id: ID of the manga
    :return: List of image URLs
    """
    # Get doujinshi information to get the gallery ID and total pages
    doujinshi_info = doujinshi_parser(manga_id)
    
    # Extract gallery ID (preferring img_id, falling back to manga_id)
    gallery_id = doujinshi_info.get('img_id', manga_id)
    
    # Possible image servers and extensions
    image_servers = ['i1', 'i2', 'i3', 'i4']
    possible_extensions = ['jpg', 'webp']
    
    # Construct image URLs
    image_urls = []
    
    # Use total pages from doujinshi info or default to a safe maximum
    total_pages = doujinshi_info.get('pages', 50)  # Default to 50 if not found
    
    async with httpx.AsyncClient() as client:
        # Headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://nhentai.net/'
        }
        
        # Try to find image URLs for each page
        for page_num in range(1, total_pages + 1):
            url_found = False
            
            # Try different servers and extensions
            for server in image_servers:
                for ext in possible_extensions:
                    # Construct image URL
                    img_url = f"https://{server}.nhentai.net/galleries/{gallery_id}/{page_num}.{ext}"
                    
                    try:
                        # Verify the image URL
                        response = await client.head(img_url, headers=headers)
                        
                        if response.status_code == 200:
                            # Verify content type is an image
                            content_type = response.headers.get('content-type', '')
                            if content_type.startswith('image/'):
                                image_urls.append(img_url)
                                print(f"Verified image for page {page_num}: {img_url}")
                                url_found = True
                                break
                    
                    except Exception as e:
                        print(f"Error checking {img_url}: {e}")
                
                if url_found:
                    break
            
            # If no URL found for this page, log a warning
            if not url_found:
                print(f"Could not find image URL for page {page_num}")
        
        print(f"Found {len(image_urls)} image URLs")
        return image_urls

async def download_images(manga_id, image_urls, download_folder):
    """
    Download images for a manga
    
    :param manga_id: ID of the manga
    :param image_urls: List of image URLs
    :param download_folder: Folder to save images
    :return: List of downloaded file paths
    """
    os.makedirs(download_folder, exist_ok=True)
    
    async with httpx.AsyncClient() as client:
        downloaded_files = []
        
        for index, img_url in enumerate(image_urls, 1):
            try:
                # Extract extension from the URL
                ext = img_url.split('.')[-1]
                
                # Prepare filename
                filename = os.path.join(download_folder, f"{index:03d}.{ext}")
                
                # Download image with headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': 'https://nhentai.net/'
                }
                response = await client.get(img_url, headers=headers)
                
                if response.status_code == 200:
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded_files.append(filename)
                    print(f"Downloaded: {filename}")
                else:
                    print(f"Failed to download {img_url}. Status code: {response.status_code}")
            
            except Exception as e:
                print(f"Error downloading image {img_url}: {e}")
        
        return downloaded_files

def download_manga(url):
    """
    Download a manga from an nhentai URL
    
    :param url: Full URL of the manga on nhentai
    :return: Path to downloaded manga
    """
    try:
        # Extract manga ID from URL
        manga_id = extract_manga_id(url)
        
        # Parse the manga details
        doujinshi_info = doujinshi_parser(manga_id)
        
        # Print out the doujinshi info for debugging
        print("Doujinshi Info:", doujinshi_info)
        
        # Prepare safe name and pretty_name
        name = safe_format_filename(doujinshi_info.get('name', ''))
        pretty_name = safe_format_filename(doujinshi_info.get('pretty_name', ''))
        
        # Create a download folder
        download_folder = name or pretty_name or str(manga_id)
        download_folder = os.path.join(os.getcwd(), download_folder)
        
        # Fetch image URLs
        image_urls = asyncio.run(fetch_manga_images(manga_id))
        
        if not image_urls:
            print("No image URLs found.")
            return None
        
        # Download images
        downloaded_files = asyncio.run(download_images(manga_id, image_urls, download_folder))
        
        if downloaded_files:
            print(f"Successfully downloaded {len(downloaded_files)} files to: {download_folder}")
            return download_folder
        else:
            print("Failed to download any images.")
            return None
    
    except Exception as e:
        print(f"Error downloading manga: {e}")
        print("Detailed traceback:")
        traceback.print_exc()
        return None

def main():
    # Example usage
    manga_url = input("Enter the nhentai manga URL: ").strip()
    downloaded_path = download_manga(manga_url)
    
    if downloaded_path:
        print(f"Manga downloaded to: {downloaded_path}")
    else:
        print("Failed to download manga.")

if __name__ == '__main__':
    # Configure logger to show more information
    logger.setLevel('DEBUG')
    
    # Run the main function
    main()