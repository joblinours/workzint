#!/usr/bin/env python3
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor
import sys
import json
import os
import pymysql
import requests


def run_script(script_name, args=None):
    cmd = ["python3", script_name]
    if args:
        cmd.extend(args)

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        print(f"Erreur lors de l'exécution de {script_name}:")
        print(result.stderr.decode())
        return False

    print(f"{script_name} exécuté avec succès")
    return True


def load_db_credentials(env_file):
    creds = {}
    with open(env_file, "r") as f:
        for line in f:
            key, value = line.strip().split("=", 1)
            creds[key.strip()] = value.strip().strip('"').strip("'")
    return creds


def load_web_credentials(env_file):
    creds = {}
    with open(env_file, "r") as f:
        for line in f:
            key, value = line.strip().split("=", 1)
            creds[key.strip()] = value.strip().strip('"').strip("'")
    return creds


def fetch_emails_from_web(env_file, mode):
    creds = load_web_credentials(env_file)
    url = "https://osint.joblin.be/paliatif.php"
    data = {"username": creds["username"], "password": creds["password"], "mode": mode}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        emails = response.text.strip().split("\n")
        return emails
    except Exception as e:
        print("Erreur lors de la récupération des emails :", e)
        sys.exit(1)


def fetch_emails_from_db(env_file):
    creds = load_db_credentials(env_file)
    connection = pymysql.connect(
        host=creds["servername"],
        user=creds["username"],
        password=creds["password"],
        database=creds["dbname"],
        connect_timeout=10,
    )
    emails = []
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT email FROM {creds['tablename']}")
            emails = [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()
    return emails


def main():
    parser = argparse.ArgumentParser(description="Orchestrateur OSINT")
    parser.add_argument(
        "--conf",
        action="store_true",
        help="Utiliser la base de données de configuration",
    )
    parser.add_argument(
        "--osint", action="store_true", help="Utiliser la base de données OSINT"
    )
    parser.add_argument(
        "-s", action="store_true", help="Exécute l'envoi des rapports par email"
    )
    args = parser.parse_args()

    if args.conf:
        mode = "conf"
    elif args.osint:
        mode = "osint"
    else:
        print("Veuillez spécifier --conf ou --osint pour sélectionner le mode.")
        sys.exit(1)

    web_env_file = "../.env/.web_creds.conf"

    emails = fetch_emails_from_web(web_env_file, mode)
    emails_file = "../result/emails.json"
    with open(emails_file, "w") as f:
        json.dump(emails, f, indent=4)
    print(f"Emails récupérés et sauvegardés dans {emails_file}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_script, "holeheson.py"): "holeheson.py",
            executor.submit(run_script, "spiderfood.py"): "spiderfood.py",
        }

        for future in futures:
            if not future.result():
                print("Arrêt prématuré suite à une erreur")
                sys.exit(1)

    if not run_script("cherchlock.py", ["../result/spiderfoot_agg.json"]):
        sys.exit(1)

    merge_args = [
        "../result/holeheh_agg.json",
        "../result/spiderfoot_agg.json",
        "../result/sherlock_agg.json",
        "-o",
        "merged_result.json",
    ]
    if not run_script("merge.py", merge_args):
        sys.exit(1)

    if not run_script("rapport.py", ["merged_result.json"]):
        sys.exit(1)

    if args.s:
        if not run_script("sender.py"):
            sys.exit(1)

    print("\nTous les traitements sont terminés avec succès!")


if __name__ == "__main__":
    main()
