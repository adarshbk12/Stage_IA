from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
from scipy.stats import skew, kurtosis
from sklearn.preprocessing import StandardScaler, LabelEncoder

# Axes du capteur
axes = ["AxX", "AxY", "AxZ", "GxX", "GxY", "GxZ"]

def split_train_validation(train_data, validation_size=0.2, random_state=42):
    """
    Sépare le jeu d'entraînement en un jeu d'entraînement et un jeu de validation.

    Le découpage est effectué par acquisition (source_file) afin qu'une
    acquisition complète appartienne soit au jeu d'entraînement, soit au
    jeu de validation. La proportion est respectée pour chaque label.

    Paramètres
    ----------
    train_data : DataFrame
        Jeu d'entraînement.
    validation_size : float
        Proportion des acquisitions à placer dans le jeu de validation.
    random_state : int
        Graine aléatoire.

    Retour
    ------
    train_final, validation_data
    """

    train_files = []
    validation_files = []

    # Découpage indépendant pour chaque label
    for label in train_data["label"].unique():

        acquisitions = (
            train_data[train_data["label"] == label]["source_file"]
            .drop_duplicates()
            .tolist()
        )

        train, validation = train_test_split(
            acquisitions,
            test_size=validation_size,
            random_state=random_state,
            shuffle=True
        )

        train_files.extend(train)
        validation_files.extend(validation)

    train_final = train_data[
        train_data["source_file"].isin(train_files)
    ].reset_index(drop=True)

    validation_data = train_data[
        train_data["source_file"].isin(validation_files)
    ].reset_index(drop=True)

    print(f"Pourcentage de validation demandé : {validation_size*100:.0f}%")
    print(f"Nombre de lignes entraînement : {len(train_final)}")
    print(f"Nombre de lignes validation : {len(validation_data)}")

    print("\nRépartition par label :")
    repartition = pd.DataFrame({
        "Training": train_final.groupby("label")["source_file"].nunique(),
        "Validation": validation_data.groupby("label")["source_file"].nunique()
    }).fillna(0).astype(int)

    repartition["Total"] = (
        repartition["Training"] + repartition["Validation"]
    )

    repartition["% Validation"] = (
        repartition["Validation"] / repartition["Total"] * 100
    ).round(1)

    display(repartition)

    return train_final, validation_data

#Fonction qui génère les caractéristiques d'une donnée par analyse spectrale

def generate_spectral_features(sample, axes=axes, n_fft=20):
    """
    Génère les caractéristiques statistiques et fréquentielles
    d'une acquisition.

    Paramètres
    ----------
    sample : DataFrame
        Acquisition à analyser.
    axes : list
        Liste des axes IMU.
    n_fft : int
        Nombre de coefficients FFT conservés.

    Retour
    ------
    dict
        Dictionnaire contenant les caractéristiques.
    """

    features = {}

    for axis in axes:

        signal = sample[axis].to_numpy(dtype=float)

        # Suppression de la composante continue
        signal = signal - np.mean(signal)

        # Caractéristiques statistiques
        features[f"{axis}_rms"] = np.sqrt(np.mean(signal**2))
        features[f"{axis}_skewness"] = skew(signal)
        features[f"{axis}_kurtosis"] = kurtosis(signal)

        # FFT
        fft_values = np.fft.rfft(signal)
        power = np.abs(fft_values) ** 2

        # On ignore fft_0 : la composante continue a déjà été retirée.
        # On conserve les coefficients 1 à 20.
        power = power[1:n_fft + 1]

        for i, value in enumerate(power):
            features[f"{axis}_fft_{i}"] = value

    return features

# 2. Fonction de génération des features pour toutes les données

def construire_features(dataset):
    feature_rows = []

    for source_file, sample in dataset.groupby("source_file"):
        features = generate_spectral_features(sample, axes, n_fft=20)

        features["source_file"] = source_file
        features["label"] = sample["label"].iloc[0]

        feature_rows.append(features)

    return pd.DataFrame(feature_rows)


def preparer_donnees_modele(
    features_train,
    features_validation,
    features_test,
):
    """
    Sépare les features et les labels, encode les labels et
    normalise les données.

    Le LabelEncoder et le StandardScaler sont ajustés uniquement
    sur les données d'entraînement.

    Paramètres
    ----------
    features_train : pandas.DataFrame
        Features du jeu d'entraînement.

    features_validation : pandas.DataFrame
        Features du jeu de validation.

    features_test : pandas.DataFrame
        Features du jeu de test.

    Retour
    ------
    dict
        Données préparées, scaler et encodeur de labels.
    """

    colonnes_obligatoires = {
        "source_file",
        "label",
    }

    datasets = {
        "entraînement": features_train,
        "validation": features_validation,
        "test": features_test,
    }

    # Vérification des colonnes obligatoires
    for nom, dataset in datasets.items():
        colonnes_manquantes = (
            colonnes_obligatoires
            - set(dataset.columns)
        )

        if colonnes_manquantes:
            raise ValueError(
                f"Colonnes manquantes dans le jeu {nom} : "
                + ", ".join(sorted(colonnes_manquantes))
            )

    # --------------------------------------------------------
    # 1. Séparation des features et des labels
    # --------------------------------------------------------

    X_train = features_train.drop(
        columns=["source_file", "label"]
    )

    y_train = features_train["label"]

    X_validation = features_validation.drop(
        columns=["source_file", "label"]
    )

    y_validation = features_validation["label"]

    X_test = features_test.drop(
        columns=["source_file", "label"]
    )

    y_test = features_test["label"]

    # Vérification de l'ordre des features
    if list(X_validation.columns) != list(X_train.columns):
        raise ValueError(
            "Les features de validation ne correspondent pas "
            "aux features d'entraînement."
        )

    if list(X_test.columns) != list(X_train.columns):
        raise ValueError(
            "Les features de test ne correspondent pas "
            "aux features d'entraînement."
        )

    # --------------------------------------------------------
    # 2. Encodage des labels
    # --------------------------------------------------------

    label_encoder = LabelEncoder()

    y_train_encoded = label_encoder.fit_transform(
        y_train
    )

    labels_inconnus_validation = (
        set(y_validation)
        - set(label_encoder.classes_)
    )

    labels_inconnus_test = (
        set(y_test)
        - set(label_encoder.classes_)
    )

    if labels_inconnus_validation:
        raise ValueError(
            "Labels inconnus dans le jeu de validation : "
            + ", ".join(
                map(str, labels_inconnus_validation)
            )
        )

    if labels_inconnus_test:
        raise ValueError(
            "Labels inconnus dans le jeu de test : "
            + ", ".join(
                map(str, labels_inconnus_test)
            )
        )

    y_validation_encoded = label_encoder.transform(
        y_validation
    )

    y_test_encoded = label_encoder.transform(
        y_test
    )

    # --------------------------------------------------------
    # 3. Normalisation des features
    # --------------------------------------------------------

    scaler = StandardScaler()

    # Le scaler est entraîné uniquement sur le jeu d'entraînement.
    X_train_scaled = scaler.fit_transform(
        X_train
    )

    X_validation_scaled = scaler.transform(
        X_validation
    )

    X_test_scaled = scaler.transform(
        X_test
    )

    # --------------------------------------------------------
    # 4. Résumé
    # --------------------------------------------------------

    print(
        "Classes :",
        list(label_encoder.classes_),
    )

    print(
        "Nombre de features :",
        X_train.shape[1],
    )

    print(
        "Dimensions entraînement :",
        X_train_scaled.shape,
    )

    print(
        "Dimensions validation :",
        X_validation_scaled.shape,
    )

    print(
        "Dimensions test :",
        X_test_scaled.shape,
    )

    return {
        "X_train": X_train,
        "X_validation": X_validation,
        "X_test": X_test,

        "y_train": y_train,
        "y_validation": y_validation,
        "y_test": y_test,

        "X_train_scaled": X_train_scaled,
        "X_validation_scaled": X_validation_scaled,
        "X_test_scaled": X_test_scaled,

        "y_train_encoded": y_train_encoded,
        "y_validation_encoded": y_validation_encoded,
        "y_test_encoded": y_test_encoded,

        "label_encoder": label_encoder,
        "scaler": scaler,
    }