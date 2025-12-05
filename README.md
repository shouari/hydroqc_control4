# Hydro-Quebec API Wrapper

## English

A general-purpose REST API wrapper for Hydro-Quebec data, built with FastAPI. This project exposes Hydro-Quebec account information, consumption data, and peak events (Winter Credit / Rate D CPC) through simple JSON endpoints.

It was originally designed for Control4 integration but can be used for any home automation platform (Home Assistant, Node-RED, etc.) or custom application.

### Credits

This project is a wrapper around the excellent [hydroqc](https://github.com/titilambert/hydroqc) library by [titilambert](https://github.com/titilambert). All the heavy lifting of communicating with Hydro-Quebec's servers is handled by that library.

### Features

-   **Peak Events**: Get current and upcoming peak events (Winter Credit).
-   **Consumption**: Get current period consumption data.
-   **Balance**: Get current account balance.
-   **Background Caching**: Data is fetched periodically in the background to ensure instant API responses and avoid timeouts.
-   **Docker Ready**: Easy deployment using Docker.

### Endpoints

#### `GET /api/peak-events`
Returns list of peak events.

**Response Example:**
```json
[
  {
    "customer_id": "123456789",
    "account_id": "987654321",
    "contract_id": "456789123",
    "ispeak": false,
    "start": "2023-12-01T06:00:00",
    "end": "2023-12-01T09:00:00",
    "state": "normal"
  }
]
```

#### `GET /api/customers`
Returns customer and account details.

**Response Example:**
```json
[
  {
    "customer_id": "123456789",
    "accounts": [
      {
        "account_id": "987654321",
        "balance": 123.45,
        "contracts": [
          {
            "contract_id": "456789123",
            "balance": 123.45
          }
        ]
      }
    ]
  }
]
```

#### `GET /api/consumption/current`
Returns current period consumption.

**Response Example:**
```json
[
  {
    "contract_id": "456789123",
    "period_start": "2023-11-01",
    "period_end": "2023-12-01",
    "total_consumption": 1500.5,
    "lower_price_consumption": 1000.0,
    "higher_price_consumption": 500.5,
    "total_days": 30,
    "mean_daily_consumption": 50.0
  }
]
```

#### `GET /api/balance`
Returns account balances.

**Response Example:**
```json
[
  {
    "contract_id": "456789123",
    "balance": 123.45,
    "account_id": "987654321",
    "customer_id": "123456789"
  }
]
```

### Installation & Usage

#### Option 1: Docker (Recommended)

1.  Create a `.env` file with your credentials:
    ```env
    HYDRO_USERNAME=your_username
    HYDRO_PASSWORD=your_password
    ```

2.  Build and run the container:
    ```bash
    docker build -t hydroqc-api .
    docker run -d -p 8000:8000 --env-file .env --name hydroqc-api hydroqc-api
    ```

3.  Access the API at `http://localhost:8000`.

#### Option 2: Python (Local)

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Create a `.env` file as shown above.

3.  Run the application:
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 8000
    ```

### Configuration

| Variable | Description | Default |
| :--- | :--- | :--- |
| `HYDRO_USERNAME` | Your Hydro-Quebec username | Required |
| `HYDRO_PASSWORD` | Your Hydro-Quebec password | Required |

---

## Français

Un wrapper API REST à usage général pour les données d'Hydro-Québec, construit avec FastAPI. Ce projet expose les informations de compte Hydro-Québec, les données de consommation et les événements de pointe (Crédit hivernal / Tarif D CPC) via des endpoints JSON simples.

Il a été conçu à l'origine pour l'intégration Control4 mais peut être utilisé pour n'importe quelle plateforme domotique (Home Assistant, Node-RED, etc.) ou application personnalisée.

### Crédits

Ce projet est un wrapper autour de l'excellente librairie [hydroqc](https://github.com/titilambert/hydroqc) de [titilambert](https://github.com/titilambert). Tout le travail de communication avec les serveurs d'Hydro-Québec est géré par cette librairie.

### Fonctionnalités

-   **Événements de pointe** : Obtenez les événements de pointe actuels et à venir (Crédit hivernal).
-   **Consommation** : Obtenez les données de consommation de la période actuelle.
-   **Solde** : Obtenez le solde actuel du compte.
-   **Mise en cache en arrière-plan** : Les données sont récupérées périodiquement en arrière-plan pour garantir des réponses API instantanées et éviter les délais d'attente.
-   **Prêt pour Docker** : Déploiement facile avec Docker.

### Endpoints

#### `GET /api/peak-events`
Retourne la liste des événements de pointe.

**Exemple de réponse :**
```json
[
  {
    "customer_id": "123456789",
    "account_id": "987654321",
    "contract_id": "456789123",
    "ispeak": false,
    "start": "2023-12-01T06:00:00",
    "end": "2023-12-01T09:00:00",
    "state": "normal"
  }
]
```

#### `GET /api/customers`
Retourne les détails du client et du compte.

**Exemple de réponse :**
```json
[
  {
    "customer_id": "123456789",
    "accounts": [
      {
        "account_id": "987654321",
        "balance": 123.45,
        "contracts": [
          {
            "contract_id": "456789123",
            "balance": 123.45
          }
        ]
      }
    ]
  }
]
```

#### `GET /api/consumption/current`
Retourne la consommation de la période actuelle.

**Exemple de réponse :**
```json
[
  {
    "contract_id": "456789123",
    "period_start": "2023-11-01",
    "period_end": "2023-12-01",
    "total_consumption": 1500.5,
    "lower_price_consumption": 1000.0,
    "higher_price_consumption": 500.5,
    "total_days": 30,
    "mean_daily_consumption": 50.0
  }
]
```

#### `GET /api/balance`
Retourne les soldes des comptes.

**Exemple de réponse :**
```json
[
  {
    "contract_id": "456789123",
    "balance": 123.45,
    "account_id": "987654321",
    "customer_id": "123456789"
  }
]
```

### Installation et Utilisation

#### Option 1 : Docker (Recommandé)

1.  Créez un fichier `.env` avec vos identifiants :
    ```env
    HYDRO_USERNAME=votre_nom_utilisateur
    HYDRO_PASSWORD=votre_mot_de_passe
    ```

2.  Construisez et lancez le conteneur :
    ```bash
    docker build -t hydroqc-api .
    docker run -d -p 8000:8000 --env-file .env --name hydroqc-api hydroqc-api
    ```

3.  Accédez à l'API sur `http://localhost:8000`.

#### Option 2 : Python (Local)

1.  Installez les dépendances :
    ```bash
    pip install -r requirements.txt
    ```

2.  Créez un fichier `.env` comme indiqué ci-dessus.

3.  Lancez l'application :
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 8000
    ```

### Configuration

| Variable | Description | Défaut |
| :--- | :--- | :--- |
| `HYDRO_USERNAME` | Votre nom d'utilisateur Hydro-Québec | Requis |
| `HYDRO_PASSWORD` | Votre mot de passe Hydro-Québec | Requis |
