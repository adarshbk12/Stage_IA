
#include <TensorFlowLite.h>
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include "LSM6DS3.h"
#include "Wire.h"

#include "modele_sort.h"
#include "scaler_params.h"

LSM6DS3 imu(I2C_MODE, 0x6A);

#define SAMPLE_RATE_HZ 50
#define WINDOW_SECONDS 2
#define N_SAMPLES (SAMPLE_RATE_HZ * WINDOW_SECONDS)
#define N_AXES 6

float buffer_data[N_SAMPLES][N_AXES];
float features[N_FEATURES];

constexpr int tensor_arena_size = 40 * 1024;
uint8_t tensor_arena[tensor_arena_size];

const tflite::Model* tflite_model;
tflite::MicroInterpreter* interpreter;
TfLiteTensor* input;
TfLiteTensor* output;

tflite::AllOpsResolver resolver;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);

  if (imu.begin() != 0) {
    Serial.println("Erreur IMU");
    while (1);
  }

  tflite_model = tflite::GetModel(modele_sort);

  static tflite::MicroInterpreter static_interpreter(
    tflite_model,
    resolver,
    tensor_arena,
    tensor_arena_size
  );

  interpreter = &static_interpreter;

  if (interpreter->AllocateTensors() != kTfLiteOk) {
    Serial.println("Erreur allocation tenseurs");
    while (1);
  }

  input = interpreter->input(0);
  output = interpreter->output(0);

  Serial.println("XIAO prête pour la reconnaissance.");
}

void loop() {
  Serial.println("Prépare le geste...");
  delay(1000);

  digitalWrite(LED_BUILTIN, LOW);
  enregistrer_fenetre();
  digitalWrite(LED_BUILTIN, HIGH);

  calculer_features();
  normaliser_features();

  for (int i = 0; i < N_FEATURES; i++) {
    input->data.f[i] = features[i];
  }

  if (interpreter->Invoke() != kTfLiteOk) {
    Serial.println("Erreur inference");
    return;
  }

  afficher_prediction();

  delay(2000);
}

void clignoter_led(int nombre) {
  for (int i = 0; i < nombre; i++) {
    digitalWrite(LED_BUILTIN, LOW);   // LED allumée sur XIAO
    delay(250);
    digitalWrite(LED_BUILTIN, HIGH);  // LED éteinte
    delay(250);
  }
}

void enregistrer_fenetre() {
  for (int i = 0; i < N_SAMPLES; i++) {
    buffer_data[i][0] = imu.readFloatAccelX();
    buffer_data[i][1] = imu.readFloatAccelY();
    buffer_data[i][2] = imu.readFloatAccelZ();

    buffer_data[i][3] = imu.readFloatGyroX();
    buffer_data[i][4] = imu.readFloatGyroY();
    buffer_data[i][5] = imu.readFloatGyroZ();

    delay(1000 / SAMPLE_RATE_HZ);
  }
}

float moyenne_axe(int axe) {
  float somme = 0;

  for (int i = 0; i < N_SAMPLES; i++) {
    somme += buffer_data[i][axe];
  }

  return somme / N_SAMPLES;
}

float rms_axe(int axe, float mean) {
  float somme = 0;

  for (int i = 0; i < N_SAMPLES; i++) {
    float x = buffer_data[i][axe] - mean;
    somme += x * x;
  }

  return sqrt(somme / N_SAMPLES);
}

float skewness_axe(int axe, float mean) {
  float m2 = 0;
  float m3 = 0;

  for (int i = 0; i < N_SAMPLES; i++) {
    float x = buffer_data[i][axe] - mean;
    m2 += x * x;
    m3 += x * x * x;
  }

  m2 /= N_SAMPLES;
  m3 /= N_SAMPLES;

  if (m2 == 0) return 0;

  return m3 / pow(m2, 1.5);
}

float kurtosis_axe(int axe, float mean) {
  float m2 = 0;
  float m4 = 0;

  for (int i = 0; i < N_SAMPLES; i++) {
    float x = buffer_data[i][axe] - mean;
    m2 += x * x;
    m4 += x * x * x * x;
  }

  m2 /= N_SAMPLES;
  m4 /= N_SAMPLES;

  if (m2 == 0) return 0;

  return (m4 / (m2 * m2)) - 3.0;
}

void calculer_features() {
  int index = 0;

  for (int axe = 0; axe < N_AXES; axe++) {
    float mean = moyenne_axe(axe);

    features[index++] = rms_axe(axe, mean);
    features[index++] = skewness_axe(axe, mean);
    features[index++] = kurtosis_axe(axe, mean);

    // Les 20 coefficients FFT sont mis à 0.
    // Pour un déploiement strictement identique au notebook,
    // il faudra ajouter une FFT côté Arduino ou réentraîner sans FFT.
    for (int i = 0; i < 20; i++) {
      features[index++] = 0.0;
    }
  }
}

void normaliser_features() {
  for (int i = 0; i < N_FEATURES; i++) {
    features[i] = (features[i] - scaler_mean[i]) / scaler_scale[i];
  }
}

void afficher_prediction() {
  int best_index = 0;
  float best_score = output->data.f[0];

  for (int i = 1; i < N_CLASSES; i++) {
    if (output->data.f[i] > best_score) {
      best_score = output->data.f[i];
      best_index = i;
    }
  }

  Serial.print("Sort reconnu : ");
  Serial.print(labels[best_index]);
  Serial.print(" | Score : ");
  Serial.println(best_score, 4);

  // Clignote selon la classe prédite
  // Classe 0 = 1 clignotement
  // Classe 1 = 2 clignotements
  // Classe 2 = 3 clignotements, etc.
  clignoter_led(best_index + 1);
}
