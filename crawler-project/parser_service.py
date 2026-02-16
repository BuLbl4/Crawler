import os
import requests
import time
from bs4 import BeautifulSoup
from config import OUTPUT_FOLDER, INDEX_FILE

BASE_URL = "https://www.moralstories.org/"
TOTAL_PAGES = 17

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def parse():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    created_files = 0
    visited_links = set()
    index_lines = []

    for page in range(1, TOTAL_PAGES + 1):

        if page == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}page/{page}/"

        print(f"Scanning: {url}")

        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")

        for h3 in soup.find_all("h3"):
            a_tag = h3.find("a")
            if not a_tag:
                continue

            story_url = a_tag["href"]

            if story_url in visited_links:
                continue

            visited_links.add(story_url)

            try:
                story_response = requests.get(story_url, headers=HEADERS)

                html_content = story_response.text

                filename = f"{created_files}.txt"
                filepath = os.path.join(OUTPUT_FOLDER, filename)

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)

                index_lines.append(f"{created_files} {story_url}")
                created_files += 1

                print(f"Saved {created_files}: {story_url}")

                time.sleep(0.2)

            except Exception as e:
                print("Error:", e)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        for line in index_lines:
            f.write(line + "\n")

    return created_files