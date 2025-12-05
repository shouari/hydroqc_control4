# Hydro-Quebec API Wrapper / Wrapper API Hydro-Québec

A general-purpose REST API wrapper for Hydro-Quebec data, built with FastAPI. This project exposes Hydro-Quebec account information, consumption data, and peak events (Winter Credit / Rate D CPC) through simple JSON endpoints.

*Un wrapper API REST à usage général pour les données d'Hydro-Québec, construit avec FastAPI. Ce projet expose les informations de compte Hydro-Québec, les données de consommation et les événements de pointe (Crédit hivernal / Tarif D CPC) via des endpoints JSON simples.*

It was originally designed for Control4 integration but can be used for any home automation platform (Home Assistant, Node-RED, etc.) or custom application.

*Il a été conçu à l'origine pour l'intégration Control4 mais peut être utilisé pour n'importe quelle plateforme domotique (Home Assistant, Node-RED, etc.) ou application personnalisée.*

## Credits / Crédits

This project is a wrapper around the excellent [hydroqc](https://github.com/titilambert/hydroqc) library by [titilambert](https://github.com/titilambert). All the heavy lifting of communicating with Hydro-Quebec's servers is handled by that library.

*Ce projet est un wrapper autour de l'excellente librairie [hydroqc](https://github.com/titilambert/hydroqc) de [titilambert](https://github.com/titilambert). Tout le travail de communication avec les serveurs d'Hydro-Québec est géré par cette librairie.*

## Features / Fonctionnalités

-   **Peak Events**: Get current and upcoming peak events (Winter Credit).
    -   *Événements de pointe : Obtenez les événements de pointe actuels et à venir (Crédit hivernal).*
-   **Consumption**: Get current period consumption data.
    -   *Consommation : Obtenez les données de consommation de la période actuelle.*
-   **Balance**: Get current account balance.
    -   *Solde : Obtenez le solde actuel du compte.*
-   **Background Caching**: Data is fetched periodically in the background to ensure instant API responses and avoid timeouts.
    -   *Mise en cache en arrière-plan : Les données sont récupérées périodiquement en arrière-plan pour garantir des réponses API instantanées et éviter les délais d'attente.*
-   **Docker Ready**: Easy deployment using Docker.
    -   *Prêt pour Docker : Déploiement facile avec Docker.*

## Endpoints

-   `GET /api/peak-events`: Returns list of peak events. (*Retourne la liste des événements de pointe.*)
-   `GET /api/customers`: Returns customer and account details. (*Retourne les détails du client et du compte.*)
-   `GET /api/consumption/current`: Returns current period consumption. (*Retourne la consommation de la période actuelle.*)
-   `GET /api/balance`: Returns account balances. (*Retourne les soldes des comptes.*)

## Installation & Usage / Installation et Utilisation

### Option 1: Docker (Recommended / Recommandé)

1.  Create a `.env` file with your credentials:
    *Créez un fichier `.env` avec vos identifiants :*
    ```env
    HYDRO_USERNAME=your_username
    HYDRO_PASSWORD=your_password
    ```

2.  Build and run the container:
    *Construisez et lancez le conteneur :*
    ```bash
    docker build -t hydroqc-api .
    docker run -d -p 8000:8000 --env-file .env --name hydroqc-api hydroqc-api
    ```

3.  Access the API at `http://localhost:8000`.
    *Accédez à l'API sur `http://localhost:8000`.*

### Option 2: Python (Local)

1.  Install dependencies:
    *Installez les dépendances :*
    ```bash
    pip install -r requirements.txt
    ```

2.  Create a `.env` file as shown above.
    *Créez un fichier `.env` comme indiqué ci-dessus.*

3.  Run the application:
    *Lancez l'application :*
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 8000
    ```

## Configuration

| Variable | Description (En) | Description (Fr) | Default / Défaut |
| :--- | :--- | :--- | :--- |
| `HYDRO_USERNAME` | Your Hydro-Quebec username | *Votre nom d'utilisateur Hydro-Québec* | Required / Requis |
| `HYDRO_PASSWORD` | Your Hydro-Quebec password | *Votre mot de passe Hydro-Québec* | Required / Requis |
