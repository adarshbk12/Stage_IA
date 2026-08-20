import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

import matplotlib.pyplot as plt

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)
import pandas as pd
import numpy as np
import seaborn as sns


def afficher_metriques_classification(
    y_true,
    y_pred,
    y_proba,
    titre="Métriques de classification",
):
    """
    Calcule et affiche les métriques d'un modèle de classification.

    Paramètres
    ----------
    y_true : array-like
        Labels réels encodés.

    y_pred : array-like
        Labels prédits.

    y_proba : array-like
        Probabilités prédites pour chaque classe.

    titre : str
        Titre affiché au-dessus du tableau.

    Retour
    ------
    pandas.DataFrame
        Tableau contenant les valeurs numériques des métriques.
    """

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    y_proba = np.asarray(y_proba)

    if len(y_true) != len(y_pred):
        raise ValueError(
            "y_true et y_pred n'ont pas la même longueur."
        )

    if y_proba.shape[0] != len(y_true):
        raise ValueError(
            "y_proba ne contient pas le bon nombre de prédictions."
        )

    # Calcul des valeurs numériques
    auc = roc_auc_score(
        y_true,
        y_proba,
        multi_class="ovr",
        average="weighted",
    )

    precision = precision_score(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0,
    )

    f1 = f1_score(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0,
    )

    metrics = pd.DataFrame({
        "Metric": [
            "Area under ROC Curve",
            "Weighted average Precision",
            "Weighted average Recall",
            "Weighted average F1 score",
        ],
        "Value": [
            auc,
            precision,
            recall,
            f1,
        ],
    })

    # Création d'une copie formatée uniquement pour l'affichage
    metrics_affichage = metrics.copy()

    metrics_affichage["Value"] = (
        metrics_affichage["Value"]
        .map(lambda valeur: f"{valeur:.2f}")
    )

    print(titre)
    display(
        metrics_affichage.style.hide(axis="index")
    )

    return metrics


def afficher_matrice_confusion(y_true, y_pred, labels):
    """
    Affiche une matrice de confusion normalisée en pourcentage.

    Paramètres
    ----------
    y_true : array
        Labels réels (encodés).
    y_pred : array
        Labels prédits (encodés).
    labels : list
        Liste des noms des classes.
    """

    # Matrice de confusion
    cm = confusion_matrix(y_true, y_pred)

    # Normalisation par ligne (classe réelle)
    cm_percent = cm.astype(float) / cm.sum(axis=1, keepdims=True) * 100

    plt.figure(figsize=(8, 6))

    sns.heatmap(
        cm_percent,
        annot=True,
        fmt=".1f",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        vmin=0,
        vmax=100,
        cbar_kws={"label": "Pourcentage (%)"}
    )

    plt.xlabel("Classe prédite")
    plt.ylabel("Classe réelle")
    plt.title("Matrice de confusion (%)")

    plt.tight_layout()
    plt.show()

def afficher_accuracy(
    history,
    titre="Accuracy du réseau de neurones",
):
    """
    Affiche l'évolution de l'accuracy d'entraînement et de validation.

    Paramètres
    ----------
    history : keras.callbacks.History
        Historique retourné par model.fit().

    titre : str
        Titre du graphique.
    """

    if not hasattr(history, "history"):
        raise TypeError(
            "history doit être l'objet retourné par model.fit()."
        )

    historiques = history.history

    if "accuracy" not in historiques:
        raise ValueError(
            "L'historique ne contient pas la clé 'accuracy'."
        )

    if "val_accuracy" not in historiques:
        raise ValueError(
            "L'historique ne contient pas la clé 'val_accuracy'."
        )

    epochs = range(
        1,
        len(historiques["accuracy"]) + 1,
    )

    plt.figure(figsize=(10, 5))

    plt.plot(
        epochs,
        historiques["accuracy"],
        label="Training accuracy",
    )

    plt.plot(
        epochs,
        historiques["val_accuracy"],
        label="Validation accuracy",
    )

    plt.title(titre)
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def afficher_loss(
    history,
    titre="Loss du réseau de neurones",
):
    """
    Affiche l'évolution de la loss d'entraînement et de validation.

    Paramètres
    ----------
    history : keras.callbacks.History
        Historique retourné par model.fit().

    titre : str
        Titre du graphique.
    """

    if not hasattr(history, "history"):
        raise TypeError(
            "history doit être l'objet retourné par model.fit()."
        )

    historiques = history.history

    if "loss" not in historiques:
        raise ValueError(
            "L'historique ne contient pas la clé 'loss'."
        )

    if "val_loss" not in historiques:
        raise ValueError(
            "L'historique ne contient pas la clé 'val_loss'."
        )

    epochs = range(
        1,
        len(historiques["loss"]) + 1,
    )

    plt.figure(figsize=(10, 5))

    plt.plot(
        epochs,
        historiques["loss"],
        label="Training loss",
    )

    plt.plot(
        epochs,
        historiques["val_loss"],
        label="Validation loss",
    )

    plt.title(titre)
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()