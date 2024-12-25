import re
import os
import asyncio
import traceback
import httpx
import certifi
import urllib3
from nhentai.parser import doujinshi_parser
from nhentai.logger import logger
from nhentai.utils import format_filename
from bs4 import BeautifulSoup

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        return format_filename(name)
    except Exception:
        # If format_filename fails, do a basic sanitization
        return re.sub(r'[<>:"/\\|?*]', '', name).strip()

async def fetch_high_quality_images(manga_id):
    """
    Fetch high-quality manga image URLs directly
    
    :param manga_id: ID of the manga
    :return: List of high-quality image URLs
    """
    async with httpx.AsyncClient(verify=certifi.where()) as client:
        try:
            # Set headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://nhentai.net/'
            }
            
            # Fetch the gallery page
            url = f"https://nhentai.net/g/{manga_id}/"
            response = await client.get(url, headers=headers)
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"Failed to fetch gallery page. Status code: {response.status_code}")
                return []
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all image containers
            image_containers = soup.select('div.thumb-container')
            
            # Extract high-quality image URLs
            image_urls = []
            for container in image_containers:
                # Try to find the image link
                img_link = container.find('a', class_='gallerythumb')
                if not img_link:
                    continue
                
                # Get the page URL
                page_url = f"https://nhentai.net{img_link['href']}"
                
                # Fetch individual page
                page_response = await client.get(page_url, headers=headers)
                if page_response.status_code == 200:
                    page_soup = BeautifulSoup(page_response.text, 'html.parser')
                    
                    # Find the high-resolution image
                    img_element = page_soup.select_one('img#image')
                    if img_element:
                        img_src = img_element.get('src')
                        if img_src:
                            # Ensure full URL
                            if img_src.startswith('//'):
                                img_src = f"https:{img_src}"
                            image_urls.append(img_src)
                
                # Prevent overwhelming the server
                await asyncio.sleep(0.5)
            
            print(f"Found {len(image_urls)} image URLs")
            return image_urls
        
        except Exception as e:
            print(f"Error fetching high-quality manga images: {e}")
            traceback.print_exc()
            return []

async def download_image(client, img_url, filename, max_retries=3):
    """
    Download a single image with retry mechanism
    
    :param client: HTTP client
    :param img_url: URL of the image
    :param filename: Path to save the image
    :param max_retries: Maximum number of retry attempts
    :return: Boolean indicating success or failure
    """
    for attempt in range(max_retries):
        try:
            # Download image with headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://nhentai.net/'
            }
            response = await client.get(img_url, headers=headers)
            
            if response.status_code == 200:
                # Log image details
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)
                print(f"Downloading {filename}: {content_type}, {content_length} bytes")
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded: {filename}")
                return True
            else:
                print(f"Attempt {attempt + 1} failed to download {img_url}. Status code: {response.status_code}")
        
        except Exception as e:
            print(f"Attempt {attempt + 1} error downloading {img_url}: {e}")
        
        # Wait before retrying
        await asyncio.sleep(2 ** attempt)
    
    print(f"Failed to download {img_url} after {max_retries} attempts")
    return False

async def download_images(manga_id, image_urls, download_folder):
    """
    Download images for a manga with retry mechanism
    
    :param manga_id: ID of the manga
    :param image_urls: List of image URLs
    :param download_folder: Folder to save images
    :return: List of downloaded file paths and failed downloads
    """
    os.makedirs(download_folder, exist_ok=True)
    
    async with httpx.AsyncClient(verify=certifi.where()) as client:
        downloaded_files = []
        failed_downloads = []
        
        for index, img_url in enumerate(image_urls, 1):
            try:
                # Determine file extension
                ext = img_url.split('.')[-1]
                if ext not in ['jpg', 'png', 'webp', 'gif']:
                    ext = 'jpg'
                
                # Prepare filename
                filename = os.path.join(download_folder, f"{index:03d}.{ext}")
                
                # Download image with retry
                success = await download_image(client, img_url, filename)
                
                if success:
                    downloaded_files.append(filename)
                else:
                    failed_downloads.append((index, img_url, ext))
            
            except Exception as e:
                print(f"Unexpected error processing image {img_url}: {e}")
                failed_downloads.append((index, img_url, ext))
        
        return downloaded_files, failed_downloads

def retry_failed_downloads(download_folder, failed_downloads):
    """
    Retry downloading failed images
    
    :param download_folder: Folder to save images
    :param failed_downloads: List of failed downloads
    :return: Boolean indicating if all downloads were successful
    """
    if not failed_downloads:
        return True
    
    print(f"\nRetrying {len(failed_downloads)} failed downloads...")
    
    # Use synchronous asyncio run for retry
    async def retry_downloads():
        async with httpx.AsyncClient(verify=certifi.where()) as client:
            for index, img_url, ext in failed_downloads:
                filename = os.path.join(download_folder, f"{index:03d}.{ext}")
                success = await download_image(client, img_url, filename)
                
                if not success:
                    print(f"Permanent failure: Could not download page {index}")
                    return False
        return True
    
    return asyncio.run(retry_downloads())

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
        download_folder = re.sub(r'[<>:"/\\|?*]', '', download_folder).strip()
        
        # Fetch high-quality image URLs
        image_urls = asyncio.run(fetch_high_quality_images(manga_id))
        
        if not image_urls:
            print("No image URLs found.")
            return None
        
        # Download images
        downloaded_files, failed_downloads = asyncio.run(download_images(manga_id, image_urls, download_folder))
        
        # Retry failed downloads
        if failed_downloads:
            retry_success = retry_failed_downloads(download_folder, failed_downloads)
            
            if not retry_success:
                print("Some images could not be downloaded after retries.")
        
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