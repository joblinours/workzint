#!/usr/bin/env python3
import json
import argparse
import re
import os
import time
import concurrent.futures

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_external_account(data):
    if "\n" in data:
        parts = data.split("\n")
        label_part = parts[0]
    else:
        label_part = data
    label = label_part.split(" (")[0].strip().lower()
    m = re.search(r"<SFURL>(.*?)</SFURL>", data)
    url = m.group(1).strip() if m else "NULL"
    return label, url


def parse_hacked_email(data):
    m = re.search(r"\[(.*?)\]", data)
    return m.group(1).strip() if m else None


def merge_data(holeheh_data, spiderfoot_data, sherlock_data):
    merged = {}

    for record in holeheh_data:
        email = record.get("email")
        if email:
            merged[email] = {
                "email": email,
                "name": None,
                "usernames": [],
                "merged_services": [],
                "hacked_services": [],
                "img": [],
            }
            for service in record.get("services", []):
                merged[email]["merged_services"].append(f"{service}->NULL")

    for sublist in spiderfoot_data:
        email = next(
            (item["data"] for item in sublist if item.get("type") == "Email Address"),
            None,
        )
        if not email:
            continue

        if email not in merged:
            merged[email] = {
                "email": email,
                "name": None,
                "usernames": [],
                "merged_services": [],
                "hacked_services": [],
                "img": [],
            }

        for item in sublist:
            t, data = item.get("type"), item.get("data")
            if not data:
                continue

            if t == "Human Name":
                merged[email]["name"] = data
            elif t == "Username" and data not in merged[email]["usernames"]:
                merged[email]["usernames"].append(data)
            elif t == "Account on External Site":
                label, url = parse_external_account(data)
                parsed = f"{label}->{url}"
                if parsed not in merged[email]["merged_services"]:
                    merged[email]["merged_services"].append(parsed)
            elif t == "Hacked Email Address":
                hacked = parse_hacked_email(data)
                if hacked and hacked not in merged[email]["hacked_services"]:
                    merged[email]["hacked_services"].append(hacked)

    for record in sherlock_data:
        username = record.get("Username")
        if not username:
            continue

        matched_email = None
        for email, data in merged.items():
            if any(username.lower() == u.lower() for u in data.get("usernames", [])):
                matched_email = email
                break
        if matched_email is None:
            merged[username] = {
                "email": username,
                "name": None,
                "usernames": [username],
                "merged_services": [],
                "hacked_services": [],
                "img": [],
            }
            matched_email = username

        for service in record.get("services", []):
            parts = service.split("->")
            if len(parts) != 2:
                continue
            label = parts[0].strip().lower()
            url = parts[1].strip()
            new_service = f"{label}->{url}"
            already_present = any(
                new_service in mdata.get("merged_services", [])
                for mdata in merged.values()
            )
            if not already_present:
                merged[matched_email]["merged_services"].append(new_service)

    return merged


def take_screenshots(merged_data):
    target_folder = "../screen/"
    os.makedirs(target_folder, exist_ok=True)

    cookie_xpaths = [
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accepter')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'autoriser')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consent')]",
    ]

    def click_cookie_button(driver):
        for xpath in cookie_xpaths:
            try:
                cookie_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                ActionChains(driver).move_to_element(cookie_button).click().perform()
                return True
            except Exception:
                pass
        return False

    def process_url(email, service_name, url):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        try:
            driver.get(url)
            time.sleep(2)
            click_cookie_button(driver)
            time.sleep(2)
            sanitized_service_name = re.sub(r"[^\w\-_\. ]", "_", service_name)
            screenshot_path = os.path.join(
                target_folder, f"{email}_{sanitized_service_name}.png"
            )
            driver.save_screenshot(screenshot_path)
            return screenshot_path
        except Exception:
            return None
        finally:
            driver.quit()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_mapping = {}
        for email, data in merged_data.items():
            services = [
                (service.split("->")[0], service.split("->")[1])
                for service in data["merged_services"]
                if service.split("->")[1] != "NULL"
            ]
            for service_name, url in services:
                future = executor.submit(process_url, email, service_name, url)
                future_mapping.setdefault(email, []).append(future)

        for email, futures in future_mapping.items():
            for future in futures:
                screenshot_path = future.result()
                if screenshot_path:
                    merged_data[email]["img"].append(screenshot_path)


def main():
    parser = argparse.ArgumentParser(
        description="Fusionne et épure trois fichiers JSON avec capture d'écran."
    )
    parser.add_argument("holeheh", help="Chemin vers holeheh_agg.json")
    parser.add_argument("spiderfoot", help="Chemin vers spiderfoot_agg.json")
    parser.add_argument("sherlock", help="Chemin vers sherlock_agg.json")
    parser.add_argument(
        "-o", "--output", help="Fichier de sortie", default="merged_result.json"
    )
    args = parser.parse_args()

    try:
        holeheh_data = load_json(args.holeheh)
        spiderfoot_data = load_json(args.spiderfoot)
        sherlock_data = load_json(args.sherlock)
    except Exception as e:
        print("Erreur lors du chargement des fichiers:", e)
        return

    merged_data = merge_data(holeheh_data, spiderfoot_data, sherlock_data)
    take_screenshots(merged_data)

    try:
        with open(args.output, "w", encoding="utf-8") as f_out:
            json.dump(list(merged_data.values()), f_out, indent=4, ensure_ascii=False)
        print(f"Fusion réussie. Résultat écrit dans {args.output}")
    except Exception as e:
        print("Erreur lors de l'écriture du fichier de sortie:", e)


if __name__ == "__main__":
    main()
