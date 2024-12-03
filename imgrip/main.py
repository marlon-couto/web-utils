import argparse
import mimetypes
import os
import re
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup


def is_external_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme in ("http", "https")


def extract_urls_from_style(style_content, base_url=None):
    urls = re.findall(r'url\((.*?)\)', style_content)
    urls = [url.strip('"\'') for url in urls]
    if base_url:
        urls = [urljoin(base_url, url) for url in urls]
    return urls


def download_file(url, output_folder):
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type")
        extension = mimetypes.guess_extension(content_type) if content_type else ""

        file_name = os.path.basename(url.split("?")[0])
        if not os.path.splitext(file_name)[1]:
            file_name += extension

        output_path = os.path.join(output_folder, file_name)
        if os.path.exists(output_path):
            # print(f"Skipping already downloaded file: {file_name}")
            return

        with open(output_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)

        print(f"Downloaded: {file_name}")
    except requests.RequestException as e:
        print(f"Failed to download {url}: {e}")


def parse_and_download(input_file, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as file:
        content = file.read()
        soup = BeautifulSoup(content, "html.parser")

    tags = soup.find_all(["img", "video", "source"])
    urls = []
    for tag in tags:
        if "data-srcset" in tag.attrs:
            url = tag["data-srcset"].split()[0]
        elif "data-src" in tag.attrs:
            url = tag["data-src"]
        else:
            url = tag["src"]

        if url:
            if url.startswith("//"):
                url = "https:" + url
            urls.append(url)

    style_tags = soup.find_all("style")
    for style_tag in style_tags:
        style_content = style_tag.string
        if style_content:
            urls.extend(extract_urls_from_style(style_content))

    inline_styles = soup.find_all(style=True)
    for element in inline_styles:
        style_content = element["style"]
        urls.extend(extract_urls_from_style(style_content))

    urls = list(set(urls))
    for url in urls:
        if url.startswith("//"):
            url = "https:" + url

        if is_external_url(url):
            download_file(url, output_folder)
        # else:
        #     print(f"Skipping local URL: {url}")


def main():
    parser = argparse.ArgumentParser(description="Download all images and videos from an HTML or Astro file.")
    parser.add_argument("input", help="Path to the input HTML or Astro file.")
    parser.add_argument("output", help="Path to the output directory.")
    args = parser.parse_args()
    parse_and_download(args.input, args.output)


if __name__ == "__main__":
    main()
