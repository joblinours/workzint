import os
import sys
import json
import subprocess


def sanitize_folder_name(name: str) -> str:
    keepchars = ("-", "_", ".")
    return "".join(c if c.isalnum() or c in keepchars else "_" for c in name)


def compare_text(value: int, average: float) -> str:
    if value > average:
        return "au-dessus de la moyenne"
    elif value < average:
        return "en dessous de la moyenne"
    else:
        return "la moyenne"


def load_template(template_path: str) -> str:
    try:
        with open(template_path, "r", encoding="utf-8") as template_file:
            return template_file.read()
    except Exception as e:
        print(f"Erreur lors du chargement du fichier template : {e}")
        sys.exit(1)


def generate_report(
    entry: dict, global_stats: dict, template: str, annex_content: str
) -> str:
    total_entries = global_stats["total_entries"]
    current_merged = len(entry.get("merged_services", []))
    current_hacked = len(entry.get("hacked_services", []))

    if total_entries > 1:
        avg_merged = (global_stats["total_merged_services"] - current_merged) / (
            total_entries - 1
        )
        avg_hacked = (global_stats["total_hacked_services"] - current_hacked) / (
            total_entries - 1
        )
    else:
        avg_merged = current_merged
        avg_hacked = current_hacked

    merged_comparison = compare_text(current_merged, avg_merged)
    hacked_comparison = compare_text(current_hacked, avg_hacked)

    identifier = entry.get("name") if entry.get("name") else entry["email"]

    merged_services = entry.get("merged_services", [])
    formatted_merged_services = (
        "\n".join(f"  - {service}" for service in merged_services)
        if merged_services
        else "Aucun"
    )

    md_content = template.format(
        identifier=identifier,
        email=entry["email"],
        name=entry.get("name", "Non renseigné"),
        usernames=(
            ", ".join(entry.get("usernames", [])) if entry.get("usernames") else "Aucun"
        ),
        merged_services=formatted_merged_services,
        hacked_services=(
            ", ".join(entry.get("hacked_services", []))
            if entry.get("hacked_services")
            else "Aucun"
        ),
        current_merged=current_merged,
        avg_merged=avg_merged,
        merged_comparison=merged_comparison,
        current_hacked=current_hacked,
        avg_hacked=avg_hacked,
        hacked_comparison=hacked_comparison,
        annex_content=annex_content,
    )
    return md_content


def generate_annex(entry: dict) -> str:
    annex_content = "## Services détectés avec captures d'écran\n\n"
    annex_content += "| Service | Capture d'écran |\n"
    annex_content += "|---------|------------------|\n"

    services = entry.get("merged_services", [])
    screenshots = entry.get("img", [])

    screenshot_map = {}
    for screenshot in screenshots:
        service_name = screenshot.split("/")[-1].split("_")[1].split(".")[0]
        screenshot_map[service_name.lower()] = screenshot

    for service in services:
        service_name = service.split("->")[0].strip().lower()
        screenshot_path = screenshot_map.get(service_name, "N/A")
        if screenshot_path != "N/A":
            annex_content += f"| {service_name} | ![Capture]({screenshot_path}) |\n"
        else:
            annex_content += f"| {service_name} | Aucun screenshot disponible |\n"

    if not services:
        annex_content += "| Aucun service détecté | N/A |\n"

    return annex_content


def is_pandoc_available() -> bool:
    try:
        subprocess.run(
            ["pandoc", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage : python rapport.py <fichier_donnees.json>")
        sys.exit(1)

    json_file = sys.argv[1]
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier JSON : {e}")
        sys.exit(1)

    template_path = os.path.join(os.path.dirname(__file__), "template.md")
    template = load_template(template_path)

    total_entries = len(data)
    total_merged_services = sum(len(entry.get("merged_services", [])) for entry in data)
    total_hacked_services = sum(len(entry.get("hacked_services", [])) for entry in data)

    global_stats = {
        "total_entries": total_entries,
        "total_merged_services": total_merged_services,
        "total_hacked_services": total_hacked_services,
    }

    pandoc_installed = is_pandoc_available()
    if not pandoc_installed:
        print(
            "Pandoc n'est pas installé. Les fichiers Markdown seront générés, mais la conversion en PDF sera ignorée."
        )

    base_dir = "../rapport/"
    os.makedirs(base_dir, exist_ok=True)

    for entry in data:
        if entry.get("usernames"):
            folder_name = sanitize_folder_name(entry["usernames"][0])
        else:
            folder_name = sanitize_folder_name(entry["email"].split("@")[0])

        user_folder = os.path.join(base_dir, folder_name)
        os.makedirs(user_folder, exist_ok=True)

        annex_content = generate_annex(entry)

        md_content = generate_report(entry, global_stats, template, annex_content)

        md_file_path = os.path.join(user_folder, "rapport.md")
        with open(md_file_path, "w", encoding="utf-8") as md_file:
            md_file.write(md_content)

        if pandoc_installed:
            pdf_file_path = os.path.join(user_folder, "rapport.pdf")
            try:
                subprocess.run(
                    ["pandoc", md_file_path, "-o", pdf_file_path], check=True
                )
                print(f"Rapport généré pour {entry['email']} dans le dossier rapport")
            except Exception as e:
                print(f"Erreur lors de la conversion de {md_file_path} en PDF : {e}")
        else:
            print(f"Fichier Markdown généré pour {entry['email']} dans {user_folder}")


if __name__ == "__main__":
    main()
