import serial
import time
import pandas as pd
from datetime import datetime

def choisir_label():
    labels = sorted(data["label"].unique())

    print("\n1 - Créer un nouveau label")
    print("2 - Utiliser un label existant")

    choix = input("Choix : ")

    if choix == "1":
        label = input("Nom du nouveau label : ").strip()
        return label

    elif choix == "2":
        print("\nLabels existants :")
        for i, label in enumerate(labels):
            print(f"{i + 1} - {label}")

        choix_label = int(input("Choisir un label : ")) - 1

        if 0 <= choix_label < len(labels):
            return labels[choix_label]
        else:
            print("Choix invalide.")
            return None

    else:
        print("Choix invalide.")
        return None


#Fonction permettant de lire le capteur de la Seeed Xiao
def lire_fenetre_xiao(label):
    global data

    donnees = []

    print(f"\nPrépare le geste pour le label : {label}")
    input("Appuie sur Entrée pour lancer l'acquisition...")

    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    time.sleep(3)  # laisse le temps à la XIAO de redémarrer

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # Envoie la commande de départ
    ser.write(b"S")
    ser.flush()

    print("Acquisition en cours...")

    debut = time.time()

    while True:
        ligne = ser.readline().decode("utf-8", errors="ignore").strip()

        if ligne == "":
            continue

        if ligne == "FIN":
            break

        try:
            valeurs = [float(x) for x in ligne.split(",")]

            if len(valeurs) == len(colonnes_capteurs):
                donnees.append(valeurs)
            else:
                print("Ligne ignorée, mauvais nombre de valeurs :", ligne)

        except:
            print("Ligne ignorée :", ligne)

    ser.close()

    if len(donnees) == 0:
        print("Aucune donnée reçue.")
        return None

    df_new = pd.DataFrame(donnees, columns=colonnes_capteurs)

    nom_acquisition = f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    df_new["source_file"] = nom_acquisition
    df_new["label"] = label
    df_new["origine"] = "xiao"

    data = pd.concat([data, df_new], ignore_index=True)

    print(f"Acquisition ajoutée : {nom_acquisition}")
    print(f"Nombre de lignes ajoutées : {len(df_new)}")

    return df_new

#Fonction permettant d'ajouter une nouvelle acquisition
def ajouter_une_acquisition():
    label = choisir_label()

    if label is None or label == "":
        print("Label invalide.")
        return

    df_new = lire_fenetre_xiao(label)

    if df_new is not None:
        display(df_new.head())


#Fonction permettant d'enchaîner 10 acquisitions à la suite
def faire_10_acquisitions():
    label = choisir_label()

    if label is None or label == "":
        print("Label invalide.")
        return

    for i in range(10):
        print(f"\n========== Acquisition {i + 1}/10 ==========")

        for sec in range(3, 0, -1):
            print(f"Début dans {sec}...")
            time.sleep(1)

        lire_fenetre_xiao(label)

    print(f"\n10 acquisitions terminées pour le label : {label}")

#Fonction permettant d'afficher la dernière acquisition
def afficher_derniere_acquisition():
    if len(data) == 0:
        print("Dataset vide.")
        return

    dernier_source = data["source_file"].iloc[-1]
    derniere = data[data["source_file"] == dernier_source]

    print("\nDernière acquisition")
    print("Label :", derniere["label"].iloc[0])
    print("Source :", dernier_source)
    print("Nombre de lignes :", len(derniere))

    display(derniere.head())

#Fonction permettant de supprimer la dernière acquisition
def supprimer_derniere_acquisition():
    global data

    acquisitions_xiao = data[data["origine"] == "xiao"]

    if len(acquisitions_xiao) == 0:
        print("Aucune acquisition XIAO à supprimer.")
        print("Les données Edge Impulse sont protégées.")
        return

    dernier_source = acquisitions_xiao["source_file"].iloc[-1]

    data = data[data["source_file"] != dernier_source].reset_index(drop=True)

    print("Dernière acquisition XIAO supprimée :", dernier_source)

#Fonction permettant de supprimer le dernier label créé avec ses données
def supprimer_dernier_label():
    global data

    acquisitions_xiao = data[data["origine"] == "xiao"]

    if len(acquisitions_xiao) == 0:
        print("Aucun label XIAO à supprimer.")
        print("Les labels Edge Impulse sont protégés.")
        return

    dernier_label = acquisitions_xiao["label"].iloc[-1]

    # Vérifie si le label existait déjà dans Edge Impulse
    label_protege = dernier_label in data[data["origine"] == "edge_impulse"]["label"].unique()

    if label_protege:
        print(f"Impossible de supprimer le label '{dernier_label}' car il existe dans Edge Impulse.")
        print("Seules les données XIAO ajoutées à ce label peuvent être supprimées.")
        return

    data = data[data["label"] != dernier_label].reset_index(drop=True)

    print("Label XIAO supprimé avec toutes ses données :", dernier_label)

#Fonction permettant d'afficher les labels
def afficher_labels():
    print("\nLabels existants :")
    print(data["label"].value_counts())
