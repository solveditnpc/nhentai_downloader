import re
import os
import asyncio
import traceback
import httpx
from nhentai.parser import doujinshi_parser
from nhentai.logger import logger
from nhentai.utils import format_filename
from bs4 import BeautifulSoup

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

async def fetch_manga_images(manga_id):
    """
    Fetch manga image URLs by scraping the gallery page
    
    :param manga_id: ID of the manga
    :return: List of image URLs
    """
    async with httpx.AsyncClient() as client:
        # Fetch the gallery page
        url = f"https://nhentai.net/g/{manga_id}/"
        try:
            response = await client.get(url)
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"Failed to fetch gallery page. Status code: {response.status_code}")
                return []
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find image elements
            image_elements = soup.select('div.thumb-container img')
            
            # Extract image URLs
            image_urls = []
            for img in image_elements:
                # Try to get the full image URL
                img_src = img.get('data-src') or img.get('src')
                if img_src:
                    # Convert to full image URL if needed
                    if img_src.startswith('//'):
                        img_src = f"https:{img_src}"
                    image_urls.append(img_src)
            
            return image_urls
        
        except Exception as e:
            print(f"Error fetching manga images: {e}")
            return []

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
                # Determine file extension
                ext = img_url.split('.')[-1]
                if ext not in ['jpg', 'png', 'webp', 'gif']:
                    ext = 'jpg'
                
                # Prepare filename
                filename = os.path.join(download_folder, f"{index:03d}.{ext}")
                
                # Download image
                response = await client.get(img_url)
                
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
        download_folder = re.sub(r'[<>:"/\\|?*]', '', download_folder).strip()
        
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