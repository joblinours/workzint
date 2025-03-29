import subprocess
import json
import re
import concurrent.futures
import os

output_dir = "../result/"
os.makedirs(output_dir, exist_ok=True)

emails_file = os.path.join(output_dir, "emails.json")
with open(emails_file, "r") as f:
    emails = json.load(f)


def run_holeheh(email, container_index):
    container_name = f"holehe_{container_index}"
    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "moradconstella/holehe",
        "holehe",
        email,
        "--only-used",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.splitlines()

    parsed_email = ""
    services = []
    supp = []
    email_regex = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

    for line in output:
        line = line.strip()
        if not parsed_email:
            m = email_regex.search(line)
            if m:
                parsed_email = m.group(0)
        if "Email used" in line:
            break
        if line.startswith("[+] "):
            line_clean = line[4:]
            if " / " in line_clean:
                service_part, supp_info = line_clean.split(" / ", 1)
            else:
                service_part = line_clean
                supp_info = ""
            service = service_part.strip()
            if service.lower() == "email":
                continue
            services.append(service)
            supp_info = supp_info.strip()
            if supp_info:
                clean_supp = supp_info.replace("\u2022", "").strip()
                if clean_supp:
                    supp.append(clean_supp + "...")
    if not parsed_email:
        parsed_email = email
    return {
        "email": parsed_email,
        "services": services,
        "supp": supp,
        "container": container_name,
    }


holeheh_results = []

with concurrent.futures.ThreadPoolExecutor(max_workers=len(emails)) as executor:
    future_to_email = {
        executor.submit(run_holeheh, email, idx + 1): email
        for idx, email in enumerate(emails)
    }

    for future in concurrent.futures.as_completed(future_to_email):
        email = future_to_email[future]
        try:
            res = future.result()
            holeheh_results.append(res)
            print(f"Holeheh - Résultat obtenu pour {res['email']}")
        except Exception as e:
            print(f"Erreur pour {email} : {e}")

holeheh_file = os.path.join(output_dir, "holeheh_agg.json")
with open(holeheh_file, "w") as f:
    json.dump(holeheh_results, f, indent=4)
print(
    f"Tous les résultats Holeheh ont été sauvegardés dans le dossier result sous le nom {holeheh_file}"
)
