import time
import serial
import pandas as pd
from datetime import datetime
from IPython.display import display
from serial.tools import list_ports

BAUDRATE = 115200
N_SAMPLES_ATTENDUS = 250
COLONNES_CAPTEURS = ["AxX", "AxY", "AxZ", "GxX", "GxY", "GxZ"]

def choisir_label():
    labels = sorted(data["label"].astype(str).unique())
    print("\n1 - Créer un nouveau label")
    print("2 - Ajouter des acquisitions à un label existant")
    choix = input("Choix : ").strip()

    if choix == "1":
        label = input("Nom du nouveau geste : ").strip()
        if not label:
            raise ValueError("Le label ne peut pas être vide.")
        if label in labels:
            raise ValueError("Ce label existe déjà : utilisez le choix 2.")
        return label

    if choix == "2":
        for i, label in enumerate(labels, start=1):
            print(f"{i} - {label}")
        index = int(input("Numéro du label : ")) - 1
        if not 0 <= index < len(labels):
            raise ValueError("Choix de label invalide.")
        return labels[index]

    raise ValueError("Choix invalide.")

def lire_fenetre_xiao(label):
    """
    Réalise une acquisition, mais ne l'ajoute pas encore au dataset.
    """

    port = trouver_port_xiao()
    donnees = []

    input(f"Préparez « {label} », puis appuyez sur Entrée...")

    with serial.Serial(port, BAUDRATE, timeout=1) as ser:
        time.sleep(2)

        ser.reset_input_buffer()
        ser.write(b"S")
        ser.flush()

        print("Acquisition en cours pendant 5 secondes...")

        limite = time.time() + 12
        fin_recue = False

        while time.time() < limite:
            ligne = (
                ser.readline()
                .decode("utf-8", errors="ignore")
                .strip()
            )

            if not ligne:
                continue

            if ligne == "FIN":
                fin_recue = True
                break

            if ligne == "ERREUR_IMU":
                raise RuntimeError(
                    "L'IMU n'a pas été détectée par la carte."
                )

            if ligne == "PRET":
                continue

            try:
                valeurs = [
                    float(x)
                    for x in ligne.split(",")
                ]

                if len(valeurs) == len(COLONNES_CAPTEURS):
                    donnees.append(valeurs)

            except ValueError:
                pass

        if not fin_recue:
            raise TimeoutError(
                "La carte n'a pas envoyé le message FIN."
            )

    if len(donnees) != N_SAMPLES_ATTENDUS:
        raise RuntimeError(
            "Acquisition incomplète : "
            f"{len(donnees)}/{N_SAMPLES_ATTENDUS} mesures reçues."
        )

    acquisition = pd.DataFrame(
        donnees,
        columns=COLONNES_CAPTEURS,
    )

    print("Acquisition terminée.")
    print(f"Nombre de mesures reçues : {len(acquisition)}")

    return acquisition

def ajouter_acquisition_au_dataset(acquisition, label):
    """
    Ajoute au dataset une acquisition validée par l'utilisateur.
    """

    global data

    identifiant = (
        f"{label}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    )

    acquisition = acquisition.copy()

    acquisition["source_file"] = identifiant
    acquisition["label"] = label
    acquisition["origine"] = "xiao"

    data = pd.concat(
        [data, acquisition],
        ignore_index=True,
    )

    print(f"Acquisition conservée : {identifiant}")

    return acquisition

def acquerir_et_valider(label):
    """
    Réalise une acquisition et demande si elle doit être
    refaite, conservée ou abandonnée.

    Retour
    ------
    "gardee" ou "quitter"
    """

    while True:
        acquisition = lire_fenetre_xiao(label)

        print("\n===== VALIDATION DE L'ACQUISITION =====")
        print("1 - Refaire le geste")
        print("2 - Garder l'acquisition")
        print("3 - Quitter sans garder cette acquisition")

        choix = input("Choix : ").strip()

        if choix == "1":
            print(
                "L'acquisition actuelle est supprimée. "
                "Préparez-vous à refaire le geste."
            )
            continue

        if choix == "2":
            ajouter_acquisition_au_dataset(
                acquisition,
                label,
            )

            return "gardee"

        if choix == "3":
            print(
                "L'acquisition actuelle n'a pas été conservée."
            )

            return "quitter"

        print(
            "Choix invalide. Saisissez 1, 2 ou 3."
        )

def ajouter_une_acquisition():
    label = choisir_label()
    return acquerir_et_valider(label)

def faire_plusieurs_acquisitions():
    label = choisir_label()

    nombre = int(
        input("Nombre d'acquisitions à conserver : ")
    )

    if nombre < 1:
        raise ValueError(
            "Le nombre doit être strictement positif."
        )

    nombre_conserve = 0

    while nombre_conserve < nombre:
        print(
            f"\n===== Acquisition "
            f"{nombre_conserve + 1}/{nombre} ====="
        )

        resultat = acquerir_et_valider(label)

        if resultat == "quitter":
            print(
                "Arrêt de la série d'acquisitions."
            )
            return "quitter"

        nombre_conserve += 1

        print(
            f"Progression : {nombre_conserve}/{nombre} "
            "acquisitions conservées."
        )

    print(
        f"\nLes {nombre} acquisitions du label "
        f"« {label} » ont été conservées."
    )

    return "termine"

def afficher_derniere_acquisition():
    source = data["source_file"].iloc[-1]
    acquisition = data[data["source_file"] == source]
    print("Label :", acquisition["label"].iloc[0])
    print("Source :", source)
    print("Mesures :", len(acquisition))
    display(acquisition.head())

def supprimer_derniere_acquisition_xiao():
    global data
    xiao = data[data["origine"] == "xiao"]
    if xiao.empty:
        print("Aucune acquisition ajoutée pendant cette partie.")
        return
    source = xiao["source_file"].iloc[-1]
    data = data[data["source_file"] != source].reset_index(drop=True)
    print("Acquisition supprimée :", source)

def afficher_labels():
    display(
        data.groupby("label")["source_file"]
        .nunique()
        .rename("nombre_acquisitions")
        .to_frame()
    )

def menu_acquisition(
    dataset,
    fonction_trouver_port,
):
    """
    Lance le menu d'acquisition.

    Paramètres
    ----------
    dataset : pandas.DataFrame
        Dataset provenant du notebook.

    fonction_trouver_port : callable
        Fonction permettant de détecter le port de la XIAO.

    Retour
    ------
    pandas.DataFrame
        Dataset contenant les acquisitions ajoutées.
    """

    global data
    global trouver_port_xiao

    # Les autres fonctions du module utilisent ces deux variables.
    data = dataset
    trouver_port_xiao = fonction_trouver_port

    while True:
        print("\n===== MENU ACQUISITION =====")
        print("1 - Ajouter une acquisition")
        print("2 - Enregistrer plusieurs acquisitions")
        print("3 - Afficher la dernière acquisition")
        print("4 - Supprimer la dernière acquisition XIAO")
        print("5 - Afficher les labels")
        print("6 - Terminer")

        choix = input("Choix : ").strip()

        if choix == "1":
            resultat = ajouter_une_acquisition()

            if resultat == "quitter":
                print("Fin du menu d'acquisition.")
                break

        elif choix == "2":
            resultat = faire_plusieurs_acquisitions()

            if resultat == "quitter":
                print("Fin du menu d'acquisition.")
                break

        elif choix == "3":
            afficher_derniere_acquisition()

        elif choix == "4":
            supprimer_derniere_acquisition_xiao()

        elif choix == "5":
            afficher_labels()

        elif choix == "6":
            print("Acquisition terminée.")
            break

        else:
            print(
                "Choix invalide. "
                "Saisissez un nombre entre 1 et 6."
            )
        return data


def trouver_port_xiao(afficher=True):
        ports_detectes = list(
            list_ports.comports()
        )

        candidats = []

        for port in ports_detectes:
            description = (
                f"{port.description or ''} "
                f"{port.manufacturer or ''} "
                f"{port.product or ''}"
            ).lower()

            est_seeed = port.vid == 0x2886

            est_xiao = any(
                mot in description
                for mot in [
                    "xiao",
                    "nrf52840",
                    "seeed",
                ]
            )

            if est_seeed or est_xiao:
                candidats.append(port)

        if len(candidats) == 1:
            port = candidats[0]

            if afficher:
                print(
                    "Carte détectée :",
                    port.device,
                    "-",
                    port.description,
                )

            return port.device

        if len(candidats) > 1:
            liste = "\n".join(
                f"  - {port.device} : {port.description}"
                for port in candidats
            )

            raise RuntimeError(
                "Plusieurs cartes XIAO ont été détectées :\n"
                f"{liste}\n"
                "Débranchez les cartes non utilisées."
            )

        ports_disponibles = "\n".join(
            f"  - {port.device} : {port.description}"
            for port in ports_detectes
        )

        if not ports_disponibles:
            ports_disponibles = (
                "  Aucun port série détecté."
            )

        raise RuntimeError(
            "Aucune Seeed XIAO nRF52840 détectée.\n\n"
            "Ports disponibles :\n"
            f"{ports_disponibles}"
        )