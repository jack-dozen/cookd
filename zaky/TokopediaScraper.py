# BASE: https://github.com/crypter70/Tokopedia-Scraper/blob/main/scraper.py
# MODIFIED WITH CLAUDE

from selenium.webdriver.common.by import By
from selenium import webdriver as wb
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
import pandas as pd
from selenium.webdriver.common.keys import Keys
import datetime
import time
import re
from urllib.parse import urlparse
from tinydb import TinyDB

driver = wb.Chrome()
driver.get('https://www.tokopedia.com/')
driver.implicitly_wait(5)

keywords = input("Keywords: ")

search = driver.find_element(By.XPATH, '//*[@id="header-main-wrapper"]/div[2]/div[2]/div/div/div/div/input')
search.send_keys(keywords)
search.send_keys(Keys.ENTER)
driver.implicitly_wait(5)

MAX_ITEMS = 5

def scrolling():
    scheight = .1
    while scheight < 9.9:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/%s);" % scheight)
        scheight += .01

def extract_name_from_url(url):
    path = urlparse(url).path
    slug = path.split('/')[-1]
    slug = re.sub(r'-\d{15,}-\d{15,}$', '', slug)
    slug = re.sub(r'-\d{15,}$', '', slug)
    name = slug.replace('-', ' ').title()
    return name

def get_price_from_detail(url):
    driver.get(url)
    time.sleep(3)
    try:
        price_text = wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="lblPDPDetailProductPrice"]'))
        ).text
        price_clean = re.sub(r'[^\d]', '', price_text)
        return int(price_clean)
    except:
        return None

# ── Step 1: Ambil 5 link dari halaman search ──
driver.implicitly_wait(20)
driver.refresh()
scrolling()

wait(driver, 30).until(
    EC.presence_of_element_located((By.XPATH, '//div[@data-testid="divSRPContentProducts"]'))
)
time.sleep(3)

container = driver.find_element(By.XPATH, '//div[@data-testid="divSRPContentProducts"]')
data_item = container.find_elements(By.XPATH, './div')[:MAX_ITEMS]

links = []
for item in data_item:
    try:
        href = item.find_element(By.XPATH, './/a').get_attribute('href')
        if href:
            links.append(href)
    except:
        continue

print(f"Berhasil ambil {len(links)} link")

# ── Step 2: Buka tiap link, ambil harga ──
product_data = []
for i, url in enumerate(links):
    print(f"Scraping produk {i+1}/{len(links)}...")
    name = extract_name_from_url(url)
    price = get_price_from_detail(url)
    product_data.append({
        'name': name,
        'price': price,
        'url': url
    })
    print(f"  {name} -> Rp {price:,}" if price else f"  {name} -> harga tidak ditemukan")

# ── Step 3: Hitung median & filter ──
df = pd.DataFrame(product_data)
print("\nData sebelum filter:")
print(df[['name', 'price']])

prices = df['price'].dropna().tolist()
prices_sorted = sorted(prices)
median = prices_sorted[len(prices_sorted) // 2]
print(f"\nMedian harga: Rp {median:,}")

df['selisih'] = (df['price'] - median).abs()
hasil = df.loc[df['selisih'].idxmin()]
print(f"\nProduk terpilih:")
print(f"  Nama  : {hasil['name']}")
print(f"  Harga : Rp {hasil['price']:,}")
print(f"  URL   : {hasil['url']}")

# ── Step 4: Simpan ke CSV ──
# Sementara, nantinya tidak akan di save ke CSV
now = datetime.datetime.today().strftime('%d-%m-%Y')
df.drop(columns=['selisih']).to_csv(f'sample_data_{now}.csv', index=False)

# ── Step 5: Simpan ke TinyDB ──
db = TinyDB('PLACEHOLDER.json') # Ganti jadi nama .json nantinya
tokped_ingredients = db.table('tokped_ingredients')

tokped_ingredients.insert({
    'name': hasil['name'],
    'price': int(hasil['price']),
    'url': hasil['url'],
    'timestamp': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S') # Sementara
})

print(f"\nDone! Data tersimpan ke:")
print(f"  - sample_data_{now}.csv")
print(f"  - scraping_data.json (tabel tokped_ingredients)")

driver.quit()
