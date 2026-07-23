import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split


#Fonction qui réalise le split training/test

def split_dataset(data, test_size=0.2, random_state=42):
    """
    Sépare le dataset en ensembles d'entraînement et de test.

    Le découpage est effectué par acquisition (source_file) afin qu'une
    acquisition complète appartienne soit au jeu d'entraînement, soit au
    jeu de test. La proportion train/test est respectée pour chaque label.

    Paramètres
    ----------
    data : DataFrame
        Dataset complet.
    test_size : float
        Proportion des acquisitions à placer dans le jeu de test.
    random_state : int
        Graine aléatoire.

    Retour
    ------
    train_data, test_data
    """

    train_files = []
    test_files = []

    # Traitement indépendant pour chaque label
    for label in data["label"].unique():

        acquisitions = (
            data[data["label"] == label]["source_file"]
            .drop_duplicates()
            .tolist()
        )

        train, test = train_test_split(
            acquisitions,
            test_size=test_size,
            random_state=random_state,
            shuffle=True
        )

        train_files.extend(train)
        test_files.extend(test)

    # Construction des DataFrames
    train_data = data[data["source_file"].isin(train_files)].copy()
    test_data = data[data["source_file"].isin(test_files)].copy()

    train_data.reset_index(drop=True, inplace=True)
    test_data.reset_index(drop=True, inplace=True)

    print(f"Pourcentage de test demandé : {test_size*100:.0f}%")
    print(f"Nombre de lignes training : {len(train_data)}")
    print(f"Nombre de lignes testing : {len(test_data)}")
    print(f"Shape training : {train_data.shape}")
    print(f"Shape testing : {test_data.shape}")

    print("\nRépartition par label :")
    repartition = pd.DataFrame({
        "Training": train_data.groupby("label")["source_file"].nunique(),
        "Testing": test_data.groupby("label")["source_file"].nunique()
    }).fillna(0).astype(int)

    repartition["Total"] = repartition["Training"] + repartition["Testing"]
    repartition["% Test"] = (
        repartition["Testing"] / repartition["Total"] * 100
    ).round(1)

    display(repartition)

    return train_data, test_data

def plot_data_split(train_data, test_data):
    """
    Affiche la répartition (%) entre les jeux d'entraînement et de test.

    Parameters
    ----------
    train_data : DataFrame, Series, list, ndarray...
        Jeu de données d'entraînement.
    test_data : DataFrame, Series, list, ndarray...
        Jeu de données de test.
    """
    
    split_percent = pd.Series({
        "Training": len(train_data),
        "Testing": len(test_data)
    })

    # Conversion en pourcentages
    split_percent = split_percent / split_percent.sum() * 100

    ax = split_percent.plot(
        kind="bar",
        color=["steelblue", "orange"]
    )

    plt.title("Répartition des données (%)")
    plt.xlabel("Jeu de données")
    plt.ylabel("Pourcentage (%)")
    plt.ylim(0, 100)

    # Affichage des pourcentages sur les barres
    for i, v in enumerate(split_percent):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center")

    plt.show()


def plot_label_split(train_data, test_data):
    """
    Affiche la répartition (%) des acquisitions par label entre
    le jeu d'entraînement et le jeu de test.

    Parameters
    ----------
    train_data : pandas.DataFrame
        Jeu de données d'entraînement.
    test_data : pandas.DataFrame
        Jeu de données de test.
    """

    # Nombre d'acquisitions (source_file) par label
    train_counts = (
        train_data.groupby("label")["source_file"]
        .nunique()
        .rename("Training")
    )

    test_counts = (
        test_data.groupby("label")["source_file"]
        .nunique()
        .rename("Testing")
    )

    # Fusion des résultats
    label_split = pd.concat([train_counts, test_counts], axis=1).fillna(0)

    # Conversion en pourcentage
    label_split_percent = (
        label_split.div(label_split.sum(axis=1), axis=0) * 100
    )

    # Tracé du graphique
    ax = label_split_percent.plot(
        kind="bar",
        figsize=(10, 5)
    )

    plt.title("Répartition (%) des acquisitions par label")
    plt.xlabel("Label")
    plt.ylabel("Pourcentage (%)")
    plt.xticks(rotation=45)
    plt.ylim(0, 100)

    # Affichage des pourcentages sur les barres
    for container in ax.containers:
        ax.bar_label(container, fmt="%.0f%%")

    plt.legend(title="Jeu de données")
    plt.tight_layout()
    plt.show()