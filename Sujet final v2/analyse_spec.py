import numpy as np
import matplotlib.pyplot as plt

def choisir_acquisition(dataset, label, numero):
    """
    Sélectionne une acquisition d'un label.

    Paramètres
    ----------
    dataset : train_data ou test_data
    label : nom du label
    numero : indice de l'acquisition (0 = première, 1 = deuxième, ...)
    """

    acquisitions = (
        dataset[dataset["label"] == label]["source_file"]
        .drop_duplicates()
        .tolist()
    )

    sample_file = acquisitions[numero]
    sample = dataset[dataset["source_file"] == sample_file]

    return sample


def afficher_signaux_temporels(sample):
    """
    Affiche les signaux temporels de l'accéléromètre et du gyroscope.

    Paramètres
    ----------
    sample : pandas.DataFrame
        Acquisition contenant les colonnes :
        AxX, AxY, AxZ, GxX, GxY et GxZ.
    """

    colonnes_attendues = [
        "AxX", "AxY", "AxZ",
        "GxX", "GxY", "GxZ",
    ]

    colonnes_manquantes = [
        colonne
        for colonne in colonnes_attendues
        if colonne not in sample.columns
    ]

    if colonnes_manquantes:
        raise ValueError(
            "Colonnes manquantes dans l'acquisition : "
            + ", ".join(colonnes_manquantes)
        )

    # Accéléromètre
    plt.figure(figsize=(12, 5))

    for axe in ["AxX", "AxY", "AxZ"]:
        plt.plot(sample[axe].to_numpy(), label=axe)

    plt.title("Signal brut de l'accéléromètre")
    plt.xlabel("Échantillons")
    plt.ylabel("Accélération")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # Gyroscope
    plt.figure(figsize=(12, 5))

    for axe in ["GxX", "GxY", "GxZ"]:
        plt.plot(sample[axe].to_numpy(), label=axe)

    plt.title("Signal brut du gyroscope")
    plt.xlabel("Échantillons")
    plt.ylabel("Vitesse angulaire")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def afficher_analyse_spectrale(
    sample,
    interval_ms=20,
    axes=None,
):
    """
    Affiche le spectre de puissance des six axes de l'IMU.

    Paramètres
    ----------
    sample : pandas.DataFrame
        Acquisition contenant les colonnes AxX, AxY, AxZ,
        GxX, GxY et GxZ.

    interval_ms : float
        Intervalle entre deux mesures, en millisecondes.
        Par défaut : 20 ms, soit une fréquence de 50 Hz.

    axes : list, optionnel
        Liste des axes à afficher.

    Retour
    ------
    dict
        Fréquences et puissances calculées pour chaque axe.
    """

    if axes is None:
        axes = [
            "AxX", "AxY", "AxZ",
            "GxX", "GxY", "GxZ",
        ]

    if interval_ms <= 0:
        raise ValueError(
            "L'intervalle d'échantillonnage doit être positif."
        )

    if len(sample) < 2:
        raise ValueError(
            "L'acquisition doit contenir au moins deux mesures."
        )

    axes_manquants = [
        axe
        for axe in axes
        if axe not in sample.columns
    ]

    if axes_manquants:
        raise ValueError(
            "Colonnes manquantes dans l'acquisition : "
            + ", ".join(axes_manquants)
        )

    # Conversion des millisecondes en secondes :
    # fs = 1 / (interval_ms / 1000).
    frequence_echantillonnage = 1000.0 / interval_ms

    resultats_fft = {}

    plt.figure(figsize=(12, 6))

    for axe in axes:
        signal = sample[axe].to_numpy(dtype=float)

        if not np.all(np.isfinite(signal)):
            raise ValueError(
                f"L'axe {axe} contient des valeurs invalides."
            )

        # Suppression de la composante continue.
        signal_centre = signal - np.mean(signal)

        fft_values = np.fft.rfft(signal_centre)
        puissance = np.abs(fft_values) ** 2

        frequences = np.fft.rfftfreq(
            len(signal_centre),
            d=1.0 / frequence_echantillonnage,
        )

        resultats_fft[axe] = {
            "frequences": frequences,
            "puissance": puissance,
        }

        plt.plot(
            frequences,
            puissance,
            label=axe,
        )

    plt.title(
        "Analyse spectrale des signaux IMU "
        f"— {frequence_echantillonnage:.1f} Hz"
    )
    plt.xlabel("Fréquence (Hz)")
    plt.ylabel("Puissance")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    return resultats_fft