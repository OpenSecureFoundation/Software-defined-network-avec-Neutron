# Software defined network avec Neutron
Application web de gestion d’infrastructure **Software Defined Networking (SDN)** basée sur **OpenStack Neutron**, permettant l’administration d’environnements **multi-tenant isolés via VXLAN** à travers une interface graphique simplifiée.

Le projet fournit un **tableau de bord web** permettant de gérer les ressources réseau et compute d’OpenStack sans utiliser directement la ligne de commande.

# Objectifs:

• Mettre en place un réseau multi-tenant avec isolation via VLAN ou VXLAN

• Développer une interface graphique pour la gestion simplifiée des réseaux virtuels et des règles de sécurité
___

## 🗂️ Structure du dépôt

```
.
sdn-dashboard/
│
├── app.py                      # Application Flask principale
├── requirements.txt            # Dépendances Python
│
├── templates/
│   ├── base.html               # Layout principal (sidebar, navbar, thème sombre)
│   ├── login.html              # Page de connexion (onglets Admin/Utilisateur)
│   ├── dashboard.html          # Dashboard + topologie vis-network
│   ├── networks.html           # Gestion réseaux VXLAN
│   ├── routers.html            # Gestion routeurs L3
│   ├── instances.html          # Gestion instances VM
│   ├── security_groups.html    # Gestion groupes de sécurité
│   └── users.html              # Gestion utilisateurs (admin uniquement)
│
└── scripts/
    ├── setup_admin.sh          # Initialisation infrastructure
    ├── cleanup.sh              # Nettoyage complet
    └── test_isolation.sh       # Test isolation VXLAN
```
---

# Architecture

L’application agit comme une **couche d’orchestration** entre l’interface web et les services OpenStack.

```
Utilisateur (via Navigateur)
    │
    ▼
Application Flask (Intermédiaire)
    │
    ▼
OpenStack API 
    ├── Keystone  → Authentification
    ├── Neutron   → Gestion des réseaux SDN
    ├── Nova      → Gestion des machines virtuelles
    └── Glance    → Gestion des images VM
```

Le backend OpenStack traduit les actions réalisées dans l’interface graphique Flask en **appels API vers les services OpenStack**.

L’infrastructure réseau repose sur **OpenStack Neutron**, qui permet de créer des **réseaux virtuels isolés entre différents tenants** grâce à la technologie **VXLAN**.

---

# Technologies utilisées

| Composant             | Technologie |
| --------------------- | ----------- |
| Backend               | Python      |
| Framework web         | Flask       |
| Infrastructure cloud  | OpenStack   |
| Virtualisation réseau | Neutron     |
| Compute               | Nova        |
| Authentification      | Keystone    |
| Frontend              | Bootstrap   |

---

# Prérequis

Avant d’exécuter l’application, les éléments suivants doivent être disponibles :

* **Ubuntu 22.04 ou supérieur**
* **Python 3.10+**
* **OpenStack (DevStack)** installé et fonctionnel
* Services OpenStack requis :

  * Keystone
  * Neutron
  * Nova
  * Glance

Pour une installation fonctionelle d'OpenStack : 

📄 **Guide d’installation**  
👉 [`installation/guide-installation-openstack-devstack.md`](Installation/Guide-Installation-OpenStack-Devstack.md)

Ce guide couvre :
- La préparation du système
- L’installation de DevStack
- La configuration de Neutron pour le SDN


# Installation

### 1. Cloner le projet

```bash
git clone https://github.com/OpenSecureFoundation/Software-defined-network-avec-Neutron.git
cd Software-defined-network-avec-Neutron
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt --break-system-packages
```

### 3. Initialiser l’environnement

```bash
cd scripts
chmod +x *.sh
./setup_admin.sh
```

### 4. Lancer l’application

```bash
cd ~/sdn-dashboard
python app.py
```

L’application sera accessible à l’adresse :

```
http://<IP-SERVEUR>:5001
```
---

# Utilisation

## Connexion administrateur

1. Accéder à l’interface web
2. Sélectionner **Administrateur**
3. S’authentifier avec les identifiants OpenStack

L’administrateur peut :

* gérer les utilisateurs et projets
* créer les réseaux virtuels
* déployer les machines virtuelles
* configurer les routeurs et groupes de sécurité

## Connexion utilisateur

Les utilisateurs standards peuvent :

* consulter leurs ressources
* créer des réseaux
* lancer des machines virtuelles
* gérer leurs groupes de sécurité

Les actions disponibles dépendent du **rôle attribué par l’administrateur**.

---

# Scripts d’automatisation

Le projet inclut plusieurs scripts permettant de simplifier la gestion de l’environnement :

| Script              | Description                                      |
| ------------------- | ------------------------------------------------ |
| `setup_admin.sh`    | Initialise l’infrastructure OpenStack            |
| `cleanup.sh`        | Supprime les ressources créées par l’application |
| `test_isolation.sh` | Vérifie l’isolation réseau entre tenants         |


---

# Workflows

## Workflow Administrateur

L’administrateur initialise l’infrastructure et gère les ressources des différents projets.

```
1. Initialiser l’environnement
   ./scripts/setup_admin.sh

2. Créer les utilisateurs et projets

3. Créer les réseaux virtuels VXLAN

4. Configurer les routeurs

5. Créer les groupes de sécurité

6. Déployer les machines virtuelles

7. Attacher des IP flottantes

8. Vérifier l’isolation réseau entre tenants
   ./scripts/test_isolation.sh

9. Surveiller l’infrastructure via le Dashboard
```

---

## Workflow Utilisateur

Les utilisateurs gèrent les ressources de leur projet uniquement.

```
1. Se connecter à l’interface

2. Consulter les ressources du projet via le Dashboard

3. Créer ou modifier des réseaux virtuels

4. Déployer des machines virtuelles

5. Gérer les groupes de sécurité

6. Attacher une IP flottante à une instance

7. Tester la connectivité réseau
```

---
          
# 📘 Licence

📚 Projet fourni à des fins éducatives.
Libre d’utilisation, de modification et d’extension.

