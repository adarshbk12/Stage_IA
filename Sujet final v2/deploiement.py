import os
import shutil
import subprocess
from pathlib import Path
import numpy as np


def installer_support_xiao_nrf52840():
    """
    Recherche Arduino CLI, installe le support de la XIAO nRF52840
    et vérifie que l'installation a réussi.

    Retour
    ------
    str
        Chemin de l'exécutable Arduino CLI.
    """

    seeed_index = (
        "https://files.seeedstudio.com/arduino/"
        "package_seeeduino_boards_index.json"
    )

    coeur_arduino = "Seeeduino:nrf52"

    # --------------------------------------------------------
    # Recherche d'Arduino CLI
    # --------------------------------------------------------

    chemin_configure = os.environ.get("ARDUINO_CLI")

    if (
        chemin_configure
        and Path(chemin_configure).is_file()
    ):
        arduino_cli = str(
            Path(chemin_configure).resolve()
        )

    else:
        chemin_path = shutil.which("arduino-cli")

        if chemin_path:
            arduino_cli = chemin_path

        else:
            arduino_cli = None

            noms_possibles = [
                "arduino-cli.exe",  # Windows
                "arduino-cli",      # Linux et macOS
            ]

            for nom in noms_possibles:
                candidat = Path.cwd() / nom

                if candidat.is_file():
                    arduino_cli = str(
                        candidat.resolve()
                    )
                    break

    if arduino_cli is None:
        raise FileNotFoundError(
            "Arduino CLI est introuvable.\n\n"
            "Solutions possibles :\n"
            "1. installer Arduino CLI et l'ajouter au PATH ;\n"
            "2. placer arduino-cli.exe dans le même dossier "
            "que le notebook ;\n"
            "3. définir la variable d'environnement ARDUINO_CLI."
        )

    print("Arduino CLI détecté :", arduino_cli)

    # --------------------------------------------------------
    # Fonction interne d'exécution
    # --------------------------------------------------------

    def executer_commande(
        commande,
        description,
        afficher_sortie=False,
    ):
        print(f"{description}...")

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
                f"{description.upper()} =====\n"
            )

            print(resultat.stdout)

            raise RuntimeError(
                f"{description} impossible "
                f"(code {resultat.returncode})."
            )

        if afficher_sortie:
            print(resultat.stdout)

        print(f"{description} réussie.")

        return resultat.stdout

    # --------------------------------------------------------
    # Vérification d'Arduino CLI
    # --------------------------------------------------------

    executer_commande(
        [
            arduino_cli,
            "version",
        ],
        "Vérification d'Arduino CLI",
        afficher_sortie=True,
    )

    # --------------------------------------------------------
    # Téléchargement de l'index Seeed Studio
    # --------------------------------------------------------

    executer_commande(
        [
            arduino_cli,
            "core",
            "update-index",
            "--additional-urls",
            seeed_index,
        ],
        "Mise à jour de l'index Seeed Studio",
    )

    # --------------------------------------------------------
    # Installation du support nRF52
    # --------------------------------------------------------

    executer_commande(
        [
            arduino_cli,
            "core",
            "install",
            coeur_arduino,
            "--additional-urls",
            seeed_index,
        ],
        "Installation du support XIAO nRF52840",
    )

    # --------------------------------------------------------
    # Vérification finale
    # --------------------------------------------------------

    liste_coeurs = executer_commande(
        [
            arduino_cli,
            "core",
            "list",
        ],
        "Vérification des supports installés",
    )

    if coeur_arduino.lower() not in liste_coeurs.lower():
        print(liste_coeurs)

        raise RuntimeError(
            "La commande d'installation s'est terminée, "
            "mais le support Seeeduino:nrf52 n'apparaît pas "
            "dans la liste des supports installés."
        )

    print(
        "\nSupport de la Seeed XIAO nRF52840 "
        "correctement installé."
    )

    return arduino_cli



def installer_bibliotheque_lsm6ds3(arduino_cli):
    """
    Installe la bibliothèque Arduino du capteur IMU LSM6DS3.

    Paramètres
    ----------
    arduino_cli : str
        Chemin de l'exécutable Arduino CLI.

    Retour
    ------
    bool
        True si la bibliothèque est installée.
    """

    nom_bibliotheque = "Seeed Arduino LSM6DS3"

    commande = [
        arduino_cli,
        "lib",
        "install",
        nom_bibliotheque,
    ]

    print(
        "Installation de la bibliothèque "
        f"« {nom_bibliotheque} »..."
    )

    resultat = subprocess.run(
        commande,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )

    if resultat.returncode != 0:
        print(
            "\n===== ERREUR D'INSTALLATION =====\n"
        )

        print(resultat.stdout)

        raise RuntimeError(
            "Échec de l'installation de la bibliothèque "
            f"{nom_bibliotheque} "
            f"(code {resultat.returncode})."
        )

    # Vérification dans la liste des bibliothèques installées
    verification = subprocess.run(
        [
            arduino_cli,
            "lib",
            "list",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )

    if verification.returncode != 0:
        print(verification.stdout)

        raise RuntimeError(
            "Impossible de vérifier les bibliothèques installées."
        )

    if nom_bibliotheque.lower() not in verification.stdout.lower():
        print(verification.stdout)

        raise RuntimeError(
            "La commande s'est terminée correctement, "
            "mais la bibliothèque LSM6DS3 n'apparaît pas "
            "dans la liste des bibliothèques installées."
        )

    print(
        "Bibliothèque Seeed Arduino LSM6DS3 installée."
    )

    return True


def exporter_modele_cpp(
    model,
    scaler,
    label_encoder,
    fichier_sortie="model_params.h",
):
    """
    Exporte un réseau Keras à trois couches Dense vers un fichier C++.

    Paramètres
    ----------
    model : modèle Keras entraîné
    scaler : StandardScaler entraîné
    label_encoder : LabelEncoder entraîné
    fichier_sortie : nom ou chemin du fichier .h à générer

    Retour
    ------
    Path
        Chemin absolu du fichier généré.
    """

    # --------------------------------------------------------
    # Conversion d'une valeur en littéral float C++ valide
    # --------------------------------------------------------

    def cpp_float(value):
        value = float(value)

        if not np.isfinite(value):
            raise ValueError(
                "Un paramètre du modèle contient NaN "
                "ou une valeur infinie."
            )

        text = f"{value:.9g}"

        # 818421f est invalide en C++ : il faut 818421.0f.
        if "." not in text and "e" not in text.lower():
            text += ".0"

        return text + "f"

    # --------------------------------------------------------
    # Écriture d'un tableau C++
    # --------------------------------------------------------

    def write_float_array(file, name, array, per_line=8):
        values = np.asarray(
            array,
            dtype=np.float32,
        ).ravel(order="C")

        file.write(
            f"const float {name}[{len(values)}] = {{\n"
        )

        for start in range(0, len(values), per_line):
            end = start + per_line

            row = ", ".join(
                cpp_float(value)
                for value in values[start:end]
            )

            file.write("  " + row)

            if end < len(values):
                file.write(",")

            file.write("\n")

        file.write("};\n\n")

    # --------------------------------------------------------
    # Vérification des objets
    # --------------------------------------------------------

    if not hasattr(model, "layers"):
        raise TypeError(
            "'model' ne contient pas un modèle Keras valide."
        )

    if not hasattr(scaler, "mean_"):
        raise TypeError(
            "'scaler' ne contient pas un StandardScaler entraîné."
        )

    if not hasattr(scaler, "scale_"):
        raise TypeError(
            "'scaler' ne contient pas un StandardScaler entraîné."
        )

    if not hasattr(label_encoder, "classes_"):
        raise TypeError(
            "'label_encoder' ne contient pas un "
            "LabelEncoder entraîné."
        )

    # --------------------------------------------------------
    # Récupération des couches Dense
    # --------------------------------------------------------

    # Les couches Dropout n'ont aucun rôle pendant l'inférence.
    dense_layers = [
        layer
        for layer in model.layers
        if len(layer.get_weights()) == 2
    ]

    if len(dense_layers) != 3:
        raise ValueError(
            "La fonction attend exactement trois couches Dense.\n"
            f"Nombre de couches trouvé : {len(dense_layers)}"
        )

    (w1, b1), (w2, b2), (w3, b3) = [
        layer.get_weights()
        for layer in dense_layers
    ]

    labels = [
        str(label)
        for label in label_encoder.classes_
    ]

    # --------------------------------------------------------
    # Vérification des dimensions
    # --------------------------------------------------------

    if w1.shape[0] != len(scaler.mean_):
        raise ValueError(
            "Le nombre d'entrées du modèle ne correspond pas "
            "au nombre de features du scaler.\n"
            f"Entrées du modèle : {w1.shape[0]}\n"
            f"Features du scaler : {len(scaler.mean_)}"
        )

    if len(scaler.mean_) != len(scaler.scale_):
        raise ValueError(
            "Les tableaux mean_ et scale_ du scaler "
            "n'ont pas la même longueur."
        )

    if w1.shape[1] != w2.shape[0]:
        raise ValueError(
            "Les dimensions des couches Dense 1 et 2 "
            "sont incompatibles."
        )

    if w2.shape[1] != w3.shape[0]:
        raise ValueError(
            "Les dimensions des couches Dense 2 et 3 "
            "sont incompatibles."
        )

    if w3.shape[1] != len(labels):
        raise ValueError(
            "Le nombre de sorties du modèle ne correspond pas "
            "au nombre de labels."
        )

    # --------------------------------------------------------
    # Génération du fichier model_params.h
    # --------------------------------------------------------

    header_path = Path(fichier_sortie)

    with header_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:

        file.write(
            "#ifndef MODEL_PARAMS_H\n"
            "#define MODEL_PARAMS_H\n\n"
        )

        file.write("#include <Arduino.h>\n\n")

        file.write(
            f"constexpr int N_FEATURES = {w1.shape[0]};\n"
        )

        file.write(
            f"constexpr int N_HIDDEN_1 = {w1.shape[1]};\n"
        )

        file.write(
            f"constexpr int N_HIDDEN_2 = {w2.shape[1]};\n"
        )

        file.write(
            f"constexpr int N_CLASSES = {w3.shape[1]};\n\n"
        )

        write_float_array(
            file,
            "SCALER_MEAN",
            scaler.mean_,
        )

        write_float_array(
            file,
            "SCALER_SCALE",
            scaler.scale_,
        )

        # Matrices Keras : ordre [entrée, sortie].
        write_float_array(file, "MODEL_W1", w1)
        write_float_array(file, "MODEL_B1", b1)

        write_float_array(file, "MODEL_W2", w2)
        write_float_array(file, "MODEL_B2", b2)

        write_float_array(file, "MODEL_W3", w3)
        write_float_array(file, "MODEL_B3", b3)

        escaped_labels = [
            label
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            for label in labels
        ]

        file.write(
            "const char* const LABELS[N_CLASSES] = {\n  "
        )

        file.write(
            ", ".join(
                f'"{label}"'
                for label in escaped_labels
            )
        )

        file.write("\n};\n\n")
        file.write("#endif\n")

    # --------------------------------------------------------
    # Affichage du résumé
    # --------------------------------------------------------

    parameter_count = sum(
        weights.size + bias.size
        for weights, bias in [
            (w1, b1),
            (w2, b2),
            (w3, b3),
        ]
    )

    header_path = header_path.resolve()

    print(f"Fichier généré : {header_path}")

    print(
        "Architecture : "
        f"{w1.shape[0]} -> "
        f"{w1.shape[1]} -> "
        f"{w2.shape[1]} -> "
        f"{w3.shape[1]}"
    )

    print("Labels :", labels)
    print(f"Paramètres exportés : {parameter_count}")

    print(
        "Mémoire approximative des poids en float32 : "
        f"{4 * parameter_count / 1024:.1f} Kio"
    )

    return header_path


import os
import time
import shutil
import subprocess
from pathlib import Path

import serial
from serial.tools import list_ports


def deployer_modele_xiao(
    arduino_code,
    arduino_cli,
    fichier_parametres="model_params.h",
    fqbn="Seeeduino:nrf52:xiaonRF52840Sense",
    baudrate=115200,
    ouvrir_moniteur=True,
):
    """
    Génère, compile et téléverse un programme d'inférence
    sur une Seeed XIAO nRF52840 Sense.

    Paramètres
    ----------
    arduino_code : str
        Code C++ complet du programme Arduino.

    arduino_cli : str
        Chemin de l'exécutable Arduino CLI.

    fichier_parametres : str
        Chemin du fichier model_params.h.

    fqbn : str
        Identifiant de la carte Arduino.

    baudrate : int
        Vitesse du moniteur série.

    ouvrir_moniteur : bool
        Ouvre le moniteur série après le téléversement.

    Retour
    ------
    dict
        Informations sur le déploiement.
    """

    # --------------------------------------------------------
    # Recherche automatique de la carte
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Attente du redémarrage de la carte
    # --------------------------------------------------------

    def attendre_port_xiao(timeout=20):
        debut = time.time()
        derniere_erreur = None

        while time.time() - debut < timeout:
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
        description,
    ):
        print(f"{description} en cours...")

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
                f"{description.upper()} =====\n"
            )

            print(resultat.stdout)

            print(
                "\n===== FIN DE L'ERREUR =====\n"
            )

            raise RuntimeError(
                f"{description} impossible "
                f"(code {resultat.returncode})."
            )

        print(f"{description} réussie.")

        return resultat.stdout

    # --------------------------------------------------------
    # Vérification des fichiers et paramètres
    # --------------------------------------------------------

    chemin_cli = Path(arduino_cli)
    chemin_parametres = Path(fichier_parametres)

    if not chemin_cli.is_file():
        raise FileNotFoundError(
            f"Arduino CLI est introuvable : "
            f"{chemin_cli}"
        )

    if not chemin_parametres.is_file():
        raise FileNotFoundError(
            f"Le fichier {chemin_parametres} "
            "est introuvable.\n"
            "Exécutez d'abord l'export du modèle C++."
        )

    if not isinstance(arduino_code, str):
        raise TypeError(
            "arduino_code doit contenir une chaîne "
            "de caractères."
        )

    if not arduino_code.strip():
        raise ValueError(
            "arduino_code est vide."
        )

    # --------------------------------------------------------
    # Préparation du dossier du sketch
    # --------------------------------------------------------

    sketch_name = "deploiement_xiao_cpp"

    if os.name == "nt":
        sketch_dir = Path(
            r"C:\temp\deploiement_xiao_cpp"
        )
    else:
        sketch_dir = Path(
            "/tmp/deploiement_xiao_cpp"
        )

    sketch_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    ino_path = (
        sketch_dir
        / f"{sketch_name}.ino"
    )

    destination_parametres = (
        sketch_dir
        / "model_params.h"
    )

    # Copie du fichier contenant les poids
    shutil.copy2(
        chemin_parametres,
        destination_parametres,
    )

    # Création du programme Arduino
    ino_path.write_text(
        arduino_code,
        encoding="utf-8",
        newline="\n",
    )

    print("Sketch généré :", ino_path)

    # --------------------------------------------------------
    # Détection de la carte
    # --------------------------------------------------------

    port = trouver_port_xiao()

    # --------------------------------------------------------
    # Compilation
    # --------------------------------------------------------

    executer_commande(
        [
            str(chemin_cli),
            "compile",
            "--fqbn",
            fqbn,
            str(sketch_dir),
        ],
        "Compilation",
    )

    # --------------------------------------------------------
    # Téléversement
    # --------------------------------------------------------

    executer_commande(
        [
            str(chemin_cli),
            "upload",
            "-p",
            port,
            "--fqbn",
            fqbn,
            str(sketch_dir),
        ],
        "Téléversement",
    )

    # La carte peut changer de port après son redémarrage.
    port = attendre_port_xiao(
        timeout=20
    )

    print(
        "Modèle correctement téléversé sur",
        port,
    )

    # --------------------------------------------------------
    # Moniteur série
    # --------------------------------------------------------

    if ouvrir_moniteur:
        print(
            "Ouverture du moniteur série..."
        )
        print(
            "Interrompez la cellule pour le fermer.\n"
        )

        connexion = None

        try:
            connexion = serial.Serial(
                port,
                baudrate,
                timeout=1,
            )

            time.sleep(2)

            while True:
                ligne = (
                    connexion.readline()
                    .decode(
                        "utf-8",
                        errors="ignore",
                    )
                    .strip()
                )

                if ligne:
                    print(ligne)

        except KeyboardInterrupt:
            print(
                "\nMoniteur série arrêté."
            )

        finally:
            if (
                connexion is not None
                and connexion.is_open
            ):
                connexion.close()

    return {
        "port": port,
        "fqbn": fqbn,
        "sketch_dir": sketch_dir,
        "ino_path": ino_path,
        "model_params_path": (
            destination_parametres
        ),
    }

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