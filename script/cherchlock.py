#!/usr/bin/env python3
import json
import subprocess
import concurrent.futures
import sys
import re
import os

EXCLUDE_SERVICES = [
    "yandexmusic",
    "nationstates",
    "eyeem",
    "cults3d",
    "freelance.habr",
    "torrentgalaxy",
    "mydramalist",
    "GNOME VCS",
    "HackerNews",
    "LibraryThing",
    "librarything",
    "gnome vcs",
    "memrise",
    "giphy",
    "omg.lol",
    "tumblr",
]


def parse_output(output):
    services = []
    regex = re.compile(r"^\[\+\]\s*(.+?):\s*(https?://\S+)", re.IGNORECASE)
    for line in output.splitlines():
        line = line.strip()
        match = regex.match(line)
        if match:
            service_name = match.group(1).strip()
            url = match.group(2).strip()
            if any(exclude in service_name.lower() for exclude in EXCLUDE_SERVICES):
                continue
            services.append(f"{service_name} -> {url}")
    return services


def run_scan(username, scan_number):
    container_name = f"sherlock_{scan_number}"
    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "sherlock/sherlock",
        username,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        services = parse_output(result.stdout)
        return username, services
    except subprocess.CalledProcessError as e:
        return username, [f"Erreur lors du scan: {e.stderr.strip()}"]


def main():
    if len(sys.argv) != 2:
        print("Usage: {} <fichier_input.json>".format(sys.argv[0]))
        sys.exit(1)

    input_file = sys.argv[1]

    with open(input_file, "r") as f:
        data = json.load(f)

    usernames = []
    for entry_group in data:
        for entry in entry_group:
            if entry.get("type") == "Username":
                usernames.append(entry.get("data"))

    aggregated_results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for idx, username in enumerate(usernames, start=1):
            futures.append(executor.submit(run_scan, username, idx))
        for future in concurrent.futures.as_completed(futures):
            username, services = future.result()
            aggregated_results.append({"Username": username, "services": services})

    output_directory = "../result/"
    os.makedirs(output_directory, exist_ok=True)
    output_file = os.path.join(output_directory, "sherlock_agg.json")

    with open(output_file, "w") as f:
        json.dump(aggregated_results, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
