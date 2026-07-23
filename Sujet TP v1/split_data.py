import pandas as pd
import matplotlib.pyplot as plt

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