import os
import time
import shutil
import subprocess
import deploiement

from pathlib import Path
from serial.tools import list_ports


def charger_firmware_acquisition_xiao(
    arduino_cli=None,
    fqbn="Seeeduino:nrf52:xiaonRF52840Sense",
    timeout_redemarrage=20,
):
    """
    Charge sur la XIAO nRF52840 Sense un firmware permettant
    d'enregistrer 250 mesures IMU pendant 5 secondes à 50 Hz.

    Paramètres
    ----------
    arduino_cli : str, optionnel
        Chemin d'Arduino CLI. Si None, la fonction le recherche.

    fqbn : str
        Identifiant Arduino de la carte.

    timeout_redemarrage : int
        Durée maximale d'attente après le téléversement.

    Retour
    ------
    str
        Port série de la carte après son redémarrage.
    """

    # --------------------------------------------------------
    # Recherche d'Arduino CLI
    # --------------------------------------------------------

    if arduino_cli is None:
        chemin_configure = os.environ.get(
            "ARDUINO_CLI"
        )

        if (
            chemin_configure
            and Path(chemin_configure).is_file()
        ):
            arduino_cli = str(
                Path(chemin_configure).resolve()
            )

        else:
            arduino_cli = shutil.which(
                "arduino-cli"
            )

    if arduino_cli is None:
        for nom in [
            "arduino-cli.exe",
            "arduino-cli",
        ]:
            candidat = Path.cwd() / nom

            if candidat.is_file():
                arduino_cli = str(
                    candidat.resolve()
                )
                break

    if (
        arduino_cli is None
        or not Path(arduino_cli).is_file()
    ):
        raise FileNotFoundError(
            "Arduino CLI est introuvable.\n"
            "Ajoutez-le au PATH ou placez "
            "arduino-cli.exe à côté du notebook."
        )

    print(
        "Arduino CLI détecté :",
        arduino_cli,
    )

    # --------------------------------------------------------
    # Détection automatique de la carte
    # --------------------------------------------------------

    def trouver_port_xiao(
        afficher=True,
    ):
        ports = list(
            list_ports.comports()
        )

        candidats = []

        for port in ports:
            description = (
                f"{port.description or ''} "
                f"{port.manufacturer or ''} "
                f"{port.product or ''}"
            ).lower()

            est_seeed = port.vid == 0x2886

            nom_compatible = any(
                mot in description
                for mot in [
                    "xiao",
                    "nrf52840",
                    "seeed",
                ]
            )

            if est_seeed or nom_compatible:
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
                f"  - {port.device} : "
                f"{port.description}"
                for port in candidats
            )

            raise RuntimeError(
                "Plusieurs cartes XIAO ont été "
                "détectées :\n"
                f"{liste}\n"
                "Débranchez les cartes non utilisées."
            )

        liste_ports = "\n".join(
            f"  - {port.device} : "
            f"{port.description}"
            for port in ports
        )

        if not liste_ports:
            liste_ports = (
                "  Aucun port série détecté."
            )

        raise RuntimeError(
            "Aucune XIAO nRF52840 détectée.\n\n"
            "Ports disponibles :\n"
            f"{liste_ports}"
        )

    # --------------------------------------------------------
    # Attente du redémarrage
    # --------------------------------------------------------

    def attendre_port_xiao():
        debut = time.time()
        derniere_erreur = None

        while (
            time.time() - debut
            < timeout_redemarrage
        ):
            try:
                return trouver_port_xiao(
                    afficher=False
                )

            except RuntimeError as erreur:
                derniere_erreur = erreur
                time.sleep(0.5)

        raise RuntimeError(
            "La carte n'est pas réapparue après "
            "le téléversement."
        ) from derniere_erreur

    # --------------------------------------------------------
    # Exécution silencieuse d'une commande
    # --------------------------------------------------------

    def executer_commande(
        commande,
        action,
    ):
        print(f"{action} en cours...")

        resultat = subprocess.run(
            commande,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )

        if resultat.returncode != 0:
            print(
                f"\n===== ERREUR : "
                f"{action.upper()} =====\n"
            )

            print(resultat.stdout)

            raise RuntimeError(
                f"{action} impossible "
                f"(code {resultat.returncode})."
            )

        print(f"{action} réussie.")

    # --------------------------------------------------------
    # Création du dossier du sketch
    # --------------------------------------------------------

    sketch_name = "acquisition_xiao"

    if os.name == "nt":
        sketch_dir = Path(
            r"C:\temp\acquisition_xiao"
        )
    else:
        sketch_dir = Path(
            "/tmp/acquisition_xiao"
        )

    sketch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    ino_path = (
        sketch_dir
        / f"{sketch_name}.ino"
    )

    # --------------------------------------------------------
    # Firmware Arduino d'acquisition
    # --------------------------------------------------------

    acquisition_code = r"""
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <Wire.h>
#include <LSM6DS3.h>

LSM6DS3 imu(I2C_MODE, 0x6A);

constexpr int LED_D0 = D0;
constexpr int LED_D1 = D1;

constexpr int SAMPLE_RATE_HZ = 50;
constexpr int N_SAMPLES = 250;

constexpr uint32_t SAMPLE_PERIOD_US =
    1000000UL / SAMPLE_RATE_HZ;

void setAllLeds(bool on) {
  digitalWrite(
      LED_BUILTIN,
      on ? LOW : HIGH
  );

  digitalWrite(
      LED_D0,
      on ? HIGH : LOW
  );

  digitalWrite(
      LED_D1,
      on ? HIGH : LOW
  );
}

void setup() {
  Serial.begin(115200);

  const uint32_t start = millis();

  while (
      !Serial
      && millis() - start < 3000
  ) {}

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(LED_D0, OUTPUT);
  pinMode(LED_D1, OUTPUT);

  setAllLeds(false);

  if (imu.begin() != 0) {
    Serial.println("ERREUR_IMU");

    while (true) {
      delay(1000);
    }
  }

  Serial.println("PRET");
}

void loop() {
  if (!Serial.available()) {
    return;
  }

  const char command = Serial.read();

  if (command != 'S') {
    return;
  }

  while (Serial.available()) {
    Serial.read();
  }

  setAllLeds(true);

  uint32_t nextSample = micros();

  for (
      int i = 0;
      i < N_SAMPLES;
      ++i
  ) {
    Serial.print(
        imu.readFloatAccelX(),
        8
    );

    Serial.print(',');

    Serial.print(
        imu.readFloatAccelY(),
        8
    );

    Serial.print(',');

    Serial.print(
        imu.readFloatAccelZ(),
        8
    );

    Serial.print(',');

    Serial.print(
        imu.readFloatGyroX(),
        8
    );

    Serial.print(',');

    Serial.print(
        imu.readFloatGyroY(),
        8
    );

    Serial.print(',');

    Serial.println(
        imu.readFloatGyroZ(),
        8
    );

    nextSample += SAMPLE_PERIOD_US;

    while (
        (int32_t)(micros() - nextSample)
        < 0
    ) {}
  }

  setAllLeds(false);

  Serial.println("FIN");
}
"""

    ino_path.write_text(
        acquisition_code,
        encoding="utf-8",
        newline="\n",
    )

    print(
        "Sketch d'acquisition généré :",
        ino_path,
    )

    # --------------------------------------------------------
    # Compilation et téléversement
    # --------------------------------------------------------

    port = trouver_port_xiao()

    executer_commande(
        [
            arduino_cli,
            "compile",
            "--fqbn",
            fqbn,
            str(sketch_dir),
        ],
        "Compilation du firmware d'acquisition",
    )

    executer_commande(
        [
            arduino_cli,
            "upload",
            "-p",
            port,
            "--fqbn",
            fqbn,
            str(sketch_dir),
        ],
        "Téléversement du firmware d'acquisition",
    )

    # --------------------------------------------------------
    # Nouvelle détection après redémarrage
    # --------------------------------------------------------

    port = attendre_port_xiao()

    print(
        "Carte prête pour les acquisitions sur",
        port,
    )

    return port

def fine_tuner_avec_nouveau_label(
    model_base,
    scaler_base,
    label_encoder_base,
    dataset,
    fonction_construire_features,
    epochs_tete=10,
    epochs_completes=20,
    batch_size=16,
    random_state=42,
):
    import numpy as np
    import pandas as pd
    import tensorflow as tf
    import matplotlib.pyplot as plt
    import seaborn as sns

    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import (
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    )
    from sklearn.utils.class_weight import compute_class_weight

    # 1. Vérifier les labels et générer les mêmes features qu'en partie 1.
    anciens_labels = [str(x) for x in label_encoder_base.classes_]
    nouveaux_labels = sorted(dataset["label"].astype(str).unique())
    labels_ajoutes = sorted(set(nouveaux_labels) - set(anciens_labels))

    if not labels_ajoutes:
        raise ValueError(
            "Aucun nouveau label détecté. Enregistrez d'abord un nouveau geste."
        )

    if not callable(fonction_construire_features):
        raise TypeError(
            "fonction_construire_features doit être une fonction."
        )

    features = fonction_construire_features(
        dataset
    )
    colonnes_features = [
        c for c in features.columns if c not in {"source_file", "label"}
    ]

    if len(colonnes_features) != len(scaler_base.mean_):
        raise ValueError(
            "Les features ne correspondent pas au scaler de la partie 1."
        )

    # 2. Nouveau découpage par acquisition, stratifié label par label.
    fichiers_train, fichiers_validation, fichiers_test = [], [], []
    for label in nouveaux_labels:
        fichiers = (
            features.loc[features["label"].astype(str) == label, "source_file"]
            .drop_duplicates()
            .tolist()
        )
        if len(fichiers) < 5:
            raise ValueError(
                f"Le label « {label} » ne contient que {len(fichiers)} "
                "acquisitions. Il en faut au moins 5, idéalement 10 à 20."
            )

        train_val, test = train_test_split(
            fichiers, test_size=0.20, random_state=random_state, shuffle=True
        )
        train, validation = train_test_split(
            train_val, test_size=0.20, random_state=random_state, shuffle=True
        )
        fichiers_train.extend(train)
        fichiers_validation.extend(validation)
        fichiers_test.extend(test)

    def selection(fichiers):
        subset = features[features["source_file"].isin(fichiers)].copy()
        X = subset[colonnes_features]
        y = subset["label"].astype(str)
        return X, y

    X_train, y_train = selection(fichiers_train)
    X_validation, y_validation = selection(fichiers_validation)
    X_test, y_test = selection(fichiers_test)

    # Le scaler original est volontairement conservé.
    X_train_scaled = scaler_base.transform(X_train)
    X_validation_scaled = scaler_base.transform(X_validation)
    X_test_scaled = scaler_base.transform(X_test)

    nouvel_encodeur = LabelEncoder()
    nouvel_encodeur.classes_ = np.asarray(nouveaux_labels, dtype=object)
    y_train_encoded = nouvel_encodeur.transform(y_train)
    y_validation_encoded = nouvel_encodeur.transform(y_validation)
    y_test_encoded = nouvel_encodeur.transform(y_test)

    # 3. Construire le réseau étendu et transférer les poids.
    anciennes_dense = [
        layer for layer in model_base.layers
        if isinstance(layer, tf.keras.layers.Dense)
    ]
    if len(anciennes_dense) != 3:
        raise ValueError("Le modèle de la partie 1 doit contenir 3 couches Dense.")

    units_1 = anciennes_dense[0].units
    units_2 = anciennes_dense[1].units
    input_size = X_train_scaled.shape[1]

    modele_finetune = tf.keras.Sequential([
        tf.keras.Input(shape=(input_size,)),
        tf.keras.layers.Dense(units_1, activation="relu", name="dense_1"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(units_2, activation="relu", name="dense_2"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(
            len(nouveaux_labels), activation="softmax", name="sortie_etendue"
        ),
    ])

    modele_finetune.get_layer("dense_1").set_weights(
        anciennes_dense[0].get_weights()
    )
    modele_finetune.get_layer("dense_2").set_weights(
        anciennes_dense[1].get_weights()
    )

    old_w, old_b = anciennes_dense[2].get_weights()
    new_layer = modele_finetune.get_layer("sortie_etendue")
    new_w, new_b = new_layer.get_weights()

    for old_index, label in enumerate(anciens_labels):
        new_index = nouveaux_labels.index(label)
        new_w[:, new_index] = old_w[:, old_index]
        new_b[new_index] = old_b[old_index]

    for label in labels_ajoutes:
        new_index = nouveaux_labels.index(label)
        new_w[:, new_index] = 0.0
        new_b[new_index] = 0.0

    new_layer.set_weights([new_w, new_b])

    classes = np.unique(y_train_encoded)
    poids = compute_class_weight(
        class_weight="balanced", classes=classes, y=y_train_encoded
    )
    class_weight = dict(zip(classes.tolist(), poids.tolist()))

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=6, restore_best_weights=True
    )

    # 4. Phase 1 : entraîner uniquement la nouvelle tête.
    modele_finetune.get_layer("dense_1").trainable = False
    modele_finetune.get_layer("dense_2").trainable = False
    modele_finetune.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    print("Phase 1/2 : adaptation de la couche de sortie")
    historique_tete = modele_finetune.fit(
        X_train_scaled,
        y_train_encoded,
        validation_data=(X_validation_scaled, y_validation_encoded),
        epochs=epochs_tete,
        batch_size=batch_size,
        class_weight=class_weight,
        callbacks=[early_stop],
        verbose=1,
    )

    # 5. Phase 2 : ajustement léger de tout le réseau.
    modele_finetune.get_layer("dense_1").trainable = True
    modele_finetune.get_layer("dense_2").trainable = True
    modele_finetune.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    print("Phase 2/2 : ajustement fin de toutes les couches")
    historique_complet = modele_finetune.fit(
        X_train_scaled,
        y_train_encoded,
        validation_data=(X_validation_scaled, y_validation_encoded),
        epochs=epochs_completes,
        batch_size=batch_size,
        class_weight=class_weight,
        callbacks=[early_stop],
        verbose=1,
    )

    # --------------------------------------------------------
    # 6. Regroupement des historiques des deux phases
    # --------------------------------------------------------

    accuracy_complete = (
        historique_tete.history["accuracy"]
        + historique_complet.history["accuracy"]
    )

    val_accuracy_complete = (
        historique_tete.history["val_accuracy"]
        + historique_complet.history["val_accuracy"]
    )

    loss_complete = (
        historique_tete.history["loss"]
        + historique_complet.history["loss"]
    )

    val_loss_complete = (
        historique_tete.history["val_loss"]
        + historique_complet.history["val_loss"]
    )

    epochs_complete = range(1, len(accuracy_complete) + 1)
    fin_phase_tete = len(historique_tete.history["accuracy"])

    # --------------------------------------------------------
    # 7. Courbe de l'accuracy
    # --------------------------------------------------------

    plt.figure(figsize=(10, 5))

    plt.plot(
        epochs_complete,
        accuracy_complete,
        label="Training accuracy",
    )

    plt.plot(
        epochs_complete,
        val_accuracy_complete,
        label="Validation accuracy",
    )

    plt.axvline(
        x=fin_phase_tete,
        color="black",
        linestyle="--",
        label="Début du fine-tuning complet",
    )

    plt.title("Accuracy du réseau après fine-tuning")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # --------------------------------------------------------
    # 8. Courbe de la loss
    # --------------------------------------------------------

    plt.figure(figsize=(10, 5))

    plt.plot(
        epochs_complete,
        loss_complete,
        label="Training loss",
    )

    plt.plot(
        epochs_complete,
        val_loss_complete,
        label="Validation loss",
    )

    plt.axvline(
        x=fin_phase_tete,
        color="black",
        linestyle="--",
        label="Début du fine-tuning complet",
    )

    plt.title("Loss du réseau après fine-tuning")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # --------------------------------------------------------
    # Fonctions d'affichage des métriques
    # --------------------------------------------------------

    def calculer_et_afficher_metriques(
        y_true,
        y_pred,
        y_proba,
        titre,
    ):
        """
        Calcule les mêmes métriques que dans la partie 1.
        """

        metrics = pd.DataFrame({
            "Metric": [
                "Area under ROC Curve",
                "Weighted average Precision",
                "Weighted average Recall",
                "Weighted average F1 score",
            ],
            "Value": [
                roc_auc_score(
                    y_true,
                    y_proba,
                    multi_class="ovr",
                    average="weighted",
                    labels=np.arange(len(nouveaux_labels)),
                ),
                precision_score(
                    y_true,
                    y_pred,
                    average="weighted",
                    zero_division=0,
                ),
                recall_score(
                    y_true,
                    y_pred,
                    average="weighted",
                    zero_division=0,
                ),
                f1_score(
                    y_true,
                    y_pred,
                    average="weighted",
                    zero_division=0,
                ),
            ],
        })

        metrics["Value"] = metrics["Value"].map(
            lambda valeur: f"{valeur:.2f}"
        )

        print(f"\n{titre}")
        display(metrics.style.hide(axis="index"))

        return metrics

    def afficher_matrice_confusion_finetuning(
        y_true,
        y_pred,
        titre,
    ):
        """
        Affiche une matrice de confusion normalisée par classe.
        """

        matrice = confusion_matrix(
            y_true,
            y_pred,
            labels=np.arange(len(nouveaux_labels)),
        )

        sommes_lignes = matrice.sum(
            axis=1,
            keepdims=True,
        )

        pourcentages = np.divide(
            matrice,
            sommes_lignes,
            out=np.zeros_like(
                matrice,
                dtype=float,
            ),
            where=sommes_lignes != 0,
        ) * 100

        plt.figure(figsize=(8, 6))

        sns.heatmap(
            pourcentages,
            annot=True,
            fmt=".1f",
            cmap="Blues",
            xticklabels=nouveaux_labels,
            yticklabels=nouveaux_labels,
            vmin=0,
            vmax=100,
            cbar_kws={
                "label": "Pourcentage (%)",
            },
        )

        plt.title(titre)
        plt.xlabel("Classe prédite")
        plt.ylabel("Classe réelle")
        plt.tight_layout()
        plt.show()

        return matrice

    # --------------------------------------------------------
    # 9. Évaluation sur les données de validation
    # --------------------------------------------------------

    validation_proba = modele_finetune.predict(
        X_validation_scaled
    )

    validation_pred = np.argmax(
        validation_proba,
        axis=1,
    )

    validation_metrics = calculer_et_afficher_metriques(
        y_validation_encoded,
        validation_pred,
        validation_proba,
        "Métriques - Validation après fine-tuning",
    )

    validation_confusion = (
        afficher_matrice_confusion_finetuning(
            y_validation_encoded,
            validation_pred,
            "Matrice de confusion - Validation (%)",
        )
    )

    # --------------------------------------------------------
    # 10. Évaluation sur les données de test
    # --------------------------------------------------------

    test_proba = modele_finetune.predict(
        X_test_scaled
    )

    test_pred = np.argmax(
        test_proba,
        axis=1,
    )

    test_metrics = calculer_et_afficher_metriques(
        y_test_encoded,
        test_pred,
        test_proba,
        "Métriques - Test après fine-tuning",
    )

    test_confusion = (
        afficher_matrice_confusion_finetuning(
            y_test_encoded,
            test_pred,
            "Matrice de confusion - Test (%)",
        )
    )

        # --------------------------------------------------------
    # 11. Résultats renvoyés par la fonction
    # --------------------------------------------------------

    print("\nFine-tuning terminé.")
    print("Anciennes classes :", anciens_labels)
    print("Nouvelles classes :", nouveaux_labels)
    print("Classes ajoutées :", labels_ajoutes)

    resultats = {
        "labels_ajoutes": labels_ajoutes,

        "history_head": historique_tete,
        "history_full": historique_complet,

        "accuracy": accuracy_complete,
        "val_accuracy": val_accuracy_complete,
        "loss": loss_complete,
        "val_loss": val_loss_complete,

        "validation_metrics": validation_metrics,
        "validation_confusion": validation_confusion,

        "test_metrics": test_metrics,
        "test_confusion": test_confusion,

        "features": features,

        "X_validation_scaled": X_validation_scaled,
        "y_validation_encoded": y_validation_encoded,
        "validation_proba": validation_proba,
        "validation_pred": validation_pred,

        "X_test_scaled": X_test_scaled,
        "y_test_encoded": y_test_encoded,
        "test_proba": test_proba,
        "test_pred": test_pred,
    }

    return (
        modele_finetune,
        scaler_base,
        nouvel_encodeur,
        resultats,
    )

def exporter_et_deployer_modele_xiao(
    model,
    scaler,
    label_encoder,
    arduino_code,
    fonction_exporter,
    fonction_deployer,
    arduino_cli,
    fichier_parametres="model_params.h",
    ouvrir_moniteur=True,
):
    """
    Exporte le modèle en C++, puis le compile et le téléverse
    sur la Seeed XIAO nRF52840 Sense.

    Paramètres
    ----------
    model : modèle Keras
        Modèle entraîné ou adapté par fine-tuning.

    scaler : StandardScaler
        Scaler utilisé pour normaliser les features.

    label_encoder : LabelEncoder
        Encodeur contenant les classes du modèle.

    arduino_code : str
        Code C++ d'inférence à charger sur la carte.

    arduino_cli : str, optionnel
        Chemin d'Arduino CLI. Il est recherché automatiquement
        si ce paramètre vaut None.

    fichier_parametres : str
        Nom du fichier d'en-tête à générer.

    ouvrir_moniteur : bool
        Ouvre le moniteur série après le téléversement.

    Retour
    ------
    dict
        Informations sur l'export et le déploiement.
    """

    # --------------------------------------------------------
    # 1. Vérifications
    # --------------------------------------------------------

    if not hasattr(model, "layers"):
        raise TypeError(
            "model ne contient pas un modèle Keras valide."
        )

    if not hasattr(scaler, "mean_"):
        raise TypeError(
            "scaler ne contient pas un StandardScaler entraîné."
        )

    if not hasattr(label_encoder, "classes_"):
        raise TypeError(
            "label_encoder ne contient pas un "
            "LabelEncoder entraîné."
        )
        
    if not callable(fonction_exporter):
        raise TypeError(
            "fonction_exporter doit être une fonction."
        )

    if not callable(fonction_deployer):
        raise TypeError(
            "fonction_deployer doit être une fonction."
        )

    if arduino_cli is None:
        raise ValueError(
            "Le chemin d'Arduino CLI doit être fourni."
        )

    if not isinstance(arduino_code, str):
        raise TypeError(
            "arduino_code doit être une chaîne de caractères."
        )

    if not arduino_code.strip():
        raise ValueError(
            "arduino_code ne peut pas être vide."
        )

    # --------------------------------------------------------
    # 2. Recherche d'Arduino CLI
    # --------------------------------------------------------

    if arduino_cli is None:
        arduino_cli = trouver_arduino_cli()

    print(
        "Arduino CLI utilisé :",
        arduino_cli,
    )

    # --------------------------------------------------------
    # 3. Export du modèle
    # --------------------------------------------------------

    print("\n===== EXPORT DU MODÈLE =====")

    chemin_parametres = fonction_exporter(
        model=model,
        scaler=scaler,
        label_encoder=label_encoder,
        fichier_sortie=fichier_parametres,
    )

    # --------------------------------------------------------
    # 4. Compilation et téléversement
    # --------------------------------------------------------

    print("\n===== DÉPLOIEMENT SUR LA CARTE =====")

    informations_deploiement = fonction_deployer(
        arduino_code=arduino_code,
        arduino_cli=arduino_cli,
        fichier_parametres=str(chemin_parametres),
        ouvrir_moniteur=ouvrir_moniteur,
    )

    # --------------------------------------------------------
    # 5. Résultats
    # --------------------------------------------------------

    resultats = {
        "model": model,
        "scaler": scaler,
        "label_encoder": label_encoder,
        "classes": list(
            label_encoder.classes_
        ),
        "model_params_path": chemin_parametres,
        "port": informations_deploiement["port"],
        "fqbn": informations_deploiement["fqbn"],
        "sketch_dir": informations_deploiement[
            "sketch_dir"
        ],
        "ino_path": informations_deploiement[
            "ino_path"
        ],
    }

    print("\n===== DÉPLOIEMENT TERMINÉ =====")
    print(
        "Classes embarquées :",
        resultats["classes"],
    )
    print(
        "Fichier des paramètres :",
        resultats["model_params_path"],
    )
    print(
        "Port de la carte :",
        resultats["port"],
    )

    return resultats

arduino_code = r"""
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <Wire.h>
#include <LSM6DS3.h>
#include <math.h>
#include "model_params.h"

LSM6DS3 imu(I2C_MODE, 0x6A);

constexpr int LED_D0 = D0;
constexpr int LED_D1 = D1;

constexpr int SAMPLE_RATE_HZ = 50;
constexpr int N_SAMPLES = 250;
constexpr int N_AXES = 6;
constexpr int N_FFT = 20;
constexpr uint32_t SERIAL_BAUDRATE = 115200;
constexpr uint32_t SAMPLE_PERIOD_US = 1000000UL / SAMPLE_RATE_HZ;
constexpr float EPSILON = 1.0e-12f;

float samples[N_SAMPLES][N_AXES];
float features[N_FEATURES];
float hidden1[N_HIDDEN_1];
float hidden2[N_HIDDEN_2];
float probabilities[N_CLASSES];

static_assert(N_FEATURES == N_AXES * (3 + N_FFT),
              "N_FEATURES ne correspond pas au calcul des features");

void acquireWindow();
void computeFeatures();
void normalizeFeatures();
void predictDirectCpp(const float* input, float* output);
void blinkLed(int count);
void setAllLeds(bool on);

void setup() {
  Serial.begin(SERIAL_BAUDRATE);
  // Ne pas bloquer la carte si elle fonctionne ensuite sans câble USB.
  const uint32_t serialStart = millis();
  while (!Serial && millis() - serialStart < 3000) {}

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(LED_D0, OUTPUT);
  pinMode(LED_D1, OUTPUT);

  // Toutes les LED sont éteintes au démarrage.
  setAllLeds(false);

  if (imu.begin() != 0) {
    Serial.println("Erreur : IMU non detectee");
    while (true) delay(1000);
  }
    Serial.println("XIAO prete - inference C++ directe.");
    Serial.println();
    Serial.println("Correspondance labels / clignotements :");

    for (int i = 0; i < N_CLASSES; ++i) {
      Serial.print("  ");
      Serial.print(LABELS[i]);
      Serial.print(" : ");
      Serial.print(i + 1);
      Serial.println((i + 1 == 1) ? " clignotement" : " clignotements");
    }

    Serial.println();
}

void loop() {
  Serial.println("Preparez le geste...");
  delay(1000);

  // Les trois LED restent allumées pendant l'acquisition.
  setAllLeds(true);
  acquireWindow();
  setAllLeds(false);

  computeFeatures();
  normalizeFeatures();
  predictDirectCpp(features, probabilities);

  int best = 0;
  for (int i = 1; i < N_CLASSES; ++i) {
    if (probabilities[i] > probabilities[best]) best = i;
  }

  const int blinkCount = best + 1;

  Serial.print("Sort reconnu : ");
  Serial.print(LABELS[best]);

  Serial.print(" | Score : ");
  Serial.print(probabilities[best], 4);

  Serial.print(" | Clignotements attendus : ");
  Serial.println(blinkCount);

  blinkLed(blinkCount);
  delay(2000);
}

void acquireWindow() {
  uint32_t nextSample = micros();
  for (int i = 0; i < N_SAMPLES; ++i) {
    samples[i][0] = imu.readFloatAccelX();
    samples[i][1] = imu.readFloatAccelY();
    samples[i][2] = imu.readFloatAccelZ();
    samples[i][3] = imu.readFloatGyroX();
    samples[i][4] = imu.readFloatGyroY();
    samples[i][5] = imu.readFloatGyroZ();

    nextSample += SAMPLE_PERIOD_US;
    while ((int32_t)(micros() - nextSample) < 0) {}
  }
}

void computeFeatures() {
  int featureIndex = 0;

  for (int axis = 0; axis < N_AXES; ++axis) {
    float mean = 0.0f;

    for (int n = 0; n < N_SAMPLES; ++n) {
      mean += samples[n][axis];
    }

    mean /= N_SAMPLES;

    float m2 = 0.0f;
    float m3 = 0.0f;
    float m4 = 0.0f;

    for (int n = 0; n < N_SAMPLES; ++n) {
      const float x = samples[n][axis] - mean;
      const float x2 = x * x;

      m2 += x2;
      m3 += x2 * x;
      m4 += x2 * x2;
    }

    m2 /= N_SAMPLES;
    m3 /= N_SAMPLES;
    m4 /= N_SAMPLES;

    // Caractéristiques statistiques
    features[featureIndex++] = sqrtf(m2);

    features[featureIndex++] =
        (m2 > EPSILON)
            ? m3 / powf(m2, 1.5f)
            : 0.0f;

    features[featureIndex++] =
        (m2 > EPSILON)
            ? m4 / (m2 * m2) - 3.0f
            : 0.0f;

    // Coefficients FFT 1 à 20.
    // k = 0 est ignoré car la composante continue a déjà été retirée.
    for (int k = 1; k <= N_FFT; ++k) {
      float re = 0.0f;
      float im = 0.0f;

      for (int n = 0; n < N_SAMPLES; ++n) {
        const float x = samples[n][axis] - mean;
        const float angle =
            -2.0f * PI * static_cast<float>(k * n)
            / static_cast<float>(N_SAMPLES);

        re += x * cosf(angle);
        im += x * sinf(angle);
      }

      features[featureIndex++] = re * re + im * im;
    }
  }
}

void normalizeFeatures() {
  for (int i = 0; i < N_FEATURES; ++i) {
    features[i] = (features[i] - SCALER_MEAN[i]) / SCALER_SCALE[i];
  }
}

void denseRelu(const float* input, int inputSize,
               const float* weights, const float* bias,
               float* output, int outputSize) {
  for (int j = 0; j < outputSize; ++j) {
    float sum = bias[j];
    for (int i = 0; i < inputSize; ++i) {
      // Matrices Keras exportées en ordre [entrée, sortie].
      sum += input[i] * weights[i * outputSize + j];
    }
    output[j] = (sum > 0.0f) ? sum : 0.0f;
  }
}

void denseLinear(const float* input, int inputSize,
                 const float* weights, const float* bias,
                 float* output, int outputSize) {
  for (int j = 0; j < outputSize; ++j) {
    float sum = bias[j];
    for (int i = 0; i < inputSize; ++i) {
      sum += input[i] * weights[i * outputSize + j];
    }
    output[j] = sum;
  }
}

void softmax(float* values, int size) {
  float maximum = values[0];
  for (int i = 1; i < size; ++i) maximum = max(maximum, values[i]);

  float total = 0.0f;
  for (int i = 0; i < size; ++i) {
    values[i] = expf(values[i] - maximum); // stabilisation numérique
    total += values[i];
  }
  if (total <= 0.0f) return;
  for (int i = 0; i < size; ++i) values[i] /= total;
}

void predictDirectCpp(const float* input, float* output) {
  denseRelu(
      input,
      N_FEATURES,
      MODEL_W1,
      MODEL_B1,
      hidden1,
      N_HIDDEN_1
  );

  denseRelu(
      hidden1,
      N_HIDDEN_1,
      MODEL_W2,
      MODEL_B2,
      hidden2,
      N_HIDDEN_2
  );

  denseLinear(
      hidden2,
      N_HIDDEN_2,
      MODEL_W3,
      MODEL_B3,
      output,
      N_CLASSES
  );

  softmax(output, N_CLASSES);
}

void setAllLeds(bool on) {
  // LED utilisateur : logique inversée.
  digitalWrite(
      LED_BUILTIN,
      on ? LOW : HIGH
  );

  // LED externes D0 et D1 : logique normale.
  digitalWrite(
      LED_D0,
      on ? HIGH : LOW
  );

  digitalWrite(
      LED_D1,
      on ? HIGH : LOW
  );
}

void blinkLed(int count) {
  for (int i = 0; i < count; ++i) {
    setAllLeds(true);
    delay(250);

    setAllLeds(false);
    delay(250);
  }
}
"""