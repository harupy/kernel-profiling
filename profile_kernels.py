"""
A script to scrape scores (on each commit) on top 20 public kernels on a specified competition.
"""

import os
import argparse
import traceback
import re
from functools import reduce
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


driver = webdriver.Chrome('./chromedriver')
TOP_URL = 'https://www.kaggle.com'


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='kaggle profiling')
    parser.add_argument('-c', '--comp', required=True, help='competition tag (e.g. titanic)')
    return parser.parse_args()


def chromedriver_exists():
    """
    Return True if ChromeDriver exists in the current directory.
    """
    return os.path.exists('chromedriver')


def make_soup(html):
    """
    Returns a soup object from given html.
    """
    return BeautifulSoup(html, 'lxml')


def get_kernel_meta(kernel):
    """
    Parse kernel metadata from given kernel soup object.
    """
    return {
        'author_name': kernel.select('span.tooltip-container')[0].get('data-tooltip').strip(),
        'author_url': kernel.select('a.avatar')[0].get('href').strip(),
        'thumbnail_src': kernel.select('img.avatar__thumbnail')[0].get('src').strip(),
        'vote_count': kernel.select('span.vote-button__vote-count')[0].text.strip(),
        'comment_count': kernel.select('a.kernel-list-item__info-block--comment')[0].text.strip(),
        'last_updated': kernel.select('div.kernel-list-item__details > span')[0].text.strip(),
        'best_score': kernel.select('div.kernel-list-item__score')[0].text.strip(),
    }


def utc_timestamp():
    """
    Make a timestamp from the current UTC.
    """
    return datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S (UTC)")


def parse_public_score(html):
    """
    Parse a public score from given html.
    """
    m = re.search(r'"publicScore":"(.+?)"', html)
    return float(m.group(1)) if m else 0


def parse_best_public_score(html):
    """
    Parse a best public score from given html.
    """
    m = re.search(r'"bestPublicScore":([^,]+)', html)
    return float(m.group(1)) if m else 0


def make_link(text, url):
    """
    Make a markdown link from given text and url.
    """
    return f'[{text}]({url})'


def make_row(items):
    """
    Make a row of a markdown table.
    """
    row = '|'.join(map(str, items))
    return f'|{row}|'


def make_table(header, data):
    """
    Make a markdown table from given header and data.
    """
    rows = []
    rows.append(make_row(header))
    rows.append(make_row(['-' for _ in range(len(header))]))
    rows.extend([make_row(items) for items in data])
    return '\n'.join(rows)


def make_profile(kernel_link, commit_table, meta):
    """
    Make a profile from given kernel data.
    """
    thumbnail = ('<img src="{}" alt="{}" width="72" height="72">'
                 .format(meta['thumbnail_src'], meta['author_name']))
    thumbnail = '<a href="{}">{}</a>'.format(meta['author_url'], thumbnail)
    author_link = make_link(meta['author_name'], meta['author_url'])
    return f"""
<br>

# {kernel_link}

{thumbnail}

- Author: {author_link}
- Best score: {meta['best_score']}
- Vote count: {meta['vote_count']}
- Comment count: {meta['comment_count']}
- Last updated: {meta['last_updated']}

{commit_table}
""".strip()


def main():
    args = parse_args()
    comp_url = f'https://www.kaggle.com/c/{args.comp}/notebooks'

    profiles = []
    try:
        # open the notebook page.
        driver.get(comp_url)

        # click 'Sort By' select box.
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.KaggleSelect')))
        sort_by = driver.find_element_by_css_selector('div.KaggleSelect')
        sort_by.click()

        # select 'Best score'.
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.Select-menu-outer')))
        options = driver.find_elements_by_css_selector('div.Select-menu-outer div')
        best_score = [opt for opt in options if opt.text == 'Best Score'][0]
        best_score.click()

        # parse kernels.
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.block-link__anchor')))
        soup = make_soup(driver.page_source)
        kernels = soup.select('div.block-link--bordered')
        kernels = [(ker.select('div.kernel-list-item__name')[0].text,  # kernel name
                    TOP_URL + ker.select('a.block-link__anchor')[0].get('href'),  # kernel url
                    get_kernel_meta(ker))  # kernel metadata
                   for ker in kernels]
        num_kernels = len(kernels)

        for ker_idx, (ker_title, ker_url, ker_meta) in (enumerate(kernels)):
            # if ker_idx > 1: break
            print(f'Processing {ker_url} ({ker_idx + 1} / {num_kernels})')

            # open the kernel.
            driver.get(ker_url)

            # open the version table.
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.fa-history')))
            commit_link = driver.find_element_by_css_selector('span.fa-history')
            commit_link.click()

            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.vote-button__voters-modal-title')))
            soup = make_soup(driver.page_source)

            # process commit data
            pattern = r'VersionsPaneContent_IdeVersionsTable.+'
            ver_table = soup.find('table', {'class': re.compile(pattern)})
            ver_items = ver_table.select('tbody > div')

            def process_version_item(acc, item):
                ver = item.select('a:nth-of-type(2)')[0]
                committed_at = item.find('span', recursive=False).text.strip()
                href = ver.get('href')
                if href is None:
                    return acc
                return acc + [(ver.text.strip(), committed_at, TOP_URL + href)]

            ver_items = reduce(process_version_item, ver_items, [])
            ver_data = []

            for ver, committed_at, ver_url in ver_items:
                resp = requests.get(ver_url)
                score = parse_public_score(resp.text)
                ver_link = make_link('Open', ver_url)
                ver_data.append((
                    ker_title,
                    ver,
                    score if score != 0 else '-',
                    committed_at,
                    ver_link,
                ))

            # compose scraped data.
            header = ['Title', 'Version', 'Score', 'Committed at', 'Link']
            table = make_table(header, ver_data)
            kernel_link = make_link(ker_title, ker_url)
            profiles.append(make_profile(kernel_link, table, ker_meta))

        # save the result with a timestamp.
        with open('result.md', 'w') as f:
            f.write((2 * '\n').join([f'### Created at {utc_timestamp()}'] + profiles))

    except Exception:
        print(traceback.format_exc())
    finally:
        driver.quit()


if __name__ == '__main__':
    if not chromedriver_exists():
        print('ChromeDriver not found. Please download one here: '
              'https://chromedriver.chromium.org')
    main()
