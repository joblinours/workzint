import subprocess
import json
import concurrent.futures
import os

output_dir = "../result/"
os.makedirs(output_dir, exist_ok=True)

emails_file = os.path.join(output_dir, "emails.json")
with open(emails_file, "r") as f:
    emails = json.load(f)


def run_spiderfoot(email, container_index):
    container_name = f"spiderfoot_{container_index}"
    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "joblinours/spiderfood",
        email,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    raw_output = "".join(result.stdout.splitlines())
    try:
        parsed_output = json.loads(raw_output)
    except Exception as e:
        print(f"Erreur lors du parsing JSON pour {email}: {e}")
        parsed_output = []
    return parsed_output


spiderfoot_results = []

with concurrent.futures.ThreadPoolExecutor(max_workers=len(emails)) as executor:
    future_to_email = {
        executor.submit(run_spiderfoot, email, idx + 1): email
        for idx, email in enumerate(emails)
    }

    for future in concurrent.futures.as_completed(future_to_email):
        email = future_to_email[future]
        try:
            res = future.result()
            spiderfoot_results.append(res)
            print(f"Spiderfoot - Résultat obtenu pour {email}")
        except Exception as e:
            print(f"Erreur pour {email} : {e}")

spiderfoot_file = os.path.join(output_dir, "spiderfoot_agg.json")
with open(spiderfoot_file, "w") as f:
    json.dump(spiderfoot_results, f, indent=4)
print(
    f"Tous les résultats Spiderfoot ont été sauvegardés dans dans le dossier result sous le nom {spiderfoot_file}"
)
