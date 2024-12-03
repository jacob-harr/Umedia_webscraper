###################################
# Course: GEOG 5900 - Fall 2024
# Project: 3D Modeling of West Bank
# Author: Jacob Harris
# Date: 2024/12/03
####################################

import os
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

# set dirs
print('CURRENT WORKING DIR =', os.getcwd())
data_dir = '../data'
save_dir = os.path.join(data_dir, 'images')

# Function to generate a unique file name by appending a counter if necessary
def generate_unique_filename(file_path):
    base, extension = os.path.splitext(file_path)
    counter = 1
    while os.path.exists(file_path):
        file_path = f"{base}_{counter}{extension}"
        counter += 1
    return file_path

# Function to download and save the image in the specified directory
def download_image(image_url, image_title, directory):
    try:
        # Ensure the directory exists
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Construct the full file path
        image_path = os.path.join(directory, f"{image_title}.png")
        
        # Ensure the file name is unique by adding a counter if needed
        unique_image_path = generate_unique_filename(image_path)
        
        # Download the image
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(unique_image_path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Image saved as {unique_image_path}")
            return unique_image_path
        else:
            print(f"Failed to download image: {image_url}")
    except Exception as e:
        print(f"Error downloading image: {e}")
    return None

# Function to extract metadata from a page
def extract_metadata(page_soup):
    metadata = []

    # Find all <h3> tags (which represent the categories)
    for h3 in page_soup.find_all('h3'):
        category = h3.get_text(strip=True)
        
        # Find the next <dl> sibling after <h3>
        dl = h3.find_next_sibling('dl')
        if dl:
            # Collect all <dt> and <dd> pairs as "dt_text = dd_text"
            details_list = []
            for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
                dt_text = dt.get_text(strip=True)
                dd_text = dd.get_text(strip=True)
                details_list.append(f"{dt_text} = {dd_text}")
            
            # Combine all details for the "details" column
            details = ' '.join(details_list)
            metadata.append({"category": category, "details": details})
    return metadata

# Combined function to scrape images and metadata
def scrape_images_and_metadata(prompt, chrome_driver_path):
    print('-----------------------------------\n* GEOG 5900 - FALL 2024\n* Author: JACOB HARRIS\n* Project: 3D Modeling of West Bank\n-----------------------------------')
    # Set up the Chrome driver using the specified driver path
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service)
    
    # set dir and url
    
    # Base url for Umedia
    base_url = 'https://umedia.lib.umn.edu/search?facets%5Bcollection_name_s%5D%5B%5D=University+of+Minnesota+Archives+Photograph+Collection&q='
    # Change underscores (or spaces) in prompt to "+" since that is what the req format for the url
    prompt_formatted = prompt.replace('_', '+') 
    # Append prompt that is formatted for URL to the Umedia base url
    main_url = base_url + prompt_formatted # This is the final url to scrape from

    directory = os.path.join(save_dir, prompt) # The directory where images will be saved

    data = []
    image_counter = 0  # Counter to track the number of images downloaded
    download_lim = 5 # Limit to the number of images that will download per prompt

    try:
        # Load the main page
        print(f"Loading main page: {main_url}")
        driver.get(main_url)
        time.sleep(2)  # Allow time for the page to load

        # Parse the HTML content of the main page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all <a> tags with class "search-result-item-title"
        result_links = soup.find_all('a', class_='search-result-item-title')
        
        for result in result_links:
            if image_counter >= download_lim:
                print(f"Reached the limit of {download_lim} images... terminating function.")
                break

            title = result.text.strip()  # Use the text as the title
            page_url = urljoin(main_url, result['href'])  # Construct full URL
            
            # Visit each link
            print(f"Navigating to: {page_url}")
            driver.get(page_url)
            time.sleep(2)  # Wait for the page to fully load
            
            # Parse the new page content
            page_soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Extract metadata from the page
            metadata = extract_metadata(page_soup)
            for entry in metadata:
                entry["title"] = title  # Add the title to each metadata entry
                data.append(entry)
            
            # Find the <a> tag for the "Full-size image" download
            download_link = page_soup.find('a', class_='large-download', string="Full-size image")
            if download_link and 'href' in download_link.attrs:
                image_url = urljoin(page_url, download_link['href'])  # Handle relative URLs with urljoin
                print(f"Found image URL: {image_url}")
                
                # Download the image and save it in the specified directory
                download_image(image_url, title, directory)
                image_counter += 1  # Increment the counter
                print(f"\nProgress: Downloaded {image_counter}/{download_lim} images.\n")
            else:
                print(f"No 'Full-size image' link found on page: {page_url}")
    finally:
        driver.quit()  # Ensure the browser closes after execution
    
    # Convert the collected metadata into a Pandas DataFrame
    df = pd.DataFrame(data)
    return df

# Function to accept a csv file of prompts
def scrape_from_df(csv_file):

    # Path to chrom driver (CHANGE TO YOUR OWN PATH)
    chrome_driver_path = '/Users/jakeharris/Dev_tools/chromedriver-mac-arm64/chromedriver'
    # Dict to save dfs
    meta_dict = {}

    # Load csv file (stored in the data directory)
    prompts_file = os.path.join(data_dir, csv_file) 
    # Read in prompts csv as a pandas df 
    prompts_df = pd.read_csv(prompts_file)

    # Iterate through each row of the df 'Prompt' column
    for index, prompt in prompts_df['Prompt'].items():
        # Call the function with each row in the 'Prompts' column
        metadata_df = scrape_images_and_metadata(prompt, chrome_driver_path)
        # Save metadata to dict
        meta_dict[prompt] = metadata_df

    # Save metadata locally 

    meta_dir = os.path.join(data_dir, 'metadata')
    # Ensure the directory exists
    if not os.path.exists(meta_dir):
        os.makedirs(meta_dir)
    
    for name, df in meta_dict.items():
        meta_filename = f'{name}.csv'
        save_path = os.path.join(meta_dir, meta_filename)
        df.to_csv(save_path, index=False)  # Save each df as a CSV


# Call scrape from df function 
test_file_name = 'prompts_test.csv'
data_dict = scrape_from_df(test_file_name)