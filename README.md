# Software defined network avec Neutron
Projet de Software defined network avec OpenStack Neutron

# Objectifs:

• Mettre en place un réseau multi-tenant avec isolation via VLAN ou VXLAN

• Développer une interface graphique pour la gestion simplifiée des réseaux virtuels et des règles de sécurité
___

## 🗂️ Structure du dépôt

```
.
├── installation/                           # Guide d'installation OpenStack
│   └── guide-installation-openstack-devstack.md
├── scripts/                                 # Scripts Bash d’automatisation
│   ├── setup_tenants.sh
│   ├── create_tenant_network.sh
│   ├── launch_instance.sh
│   └── test_isolation.sh
├── flask_app/                               # Application Flask (GUI)
│   ├── app.py
│   ├── requirements.txt
│   └── templates/
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── networks.html
│       ├── instances.html
│       └── security_groups.html
└── README.md
```

## 1️⃣ Installation

Avant toute utilisation des scripts ou de l'interface graphique, une installation fonctionelle d'OpenStack est requise.

📄 **Guide d’installation**  
👉 [`installation/guide-installation-openstack-devstack.md`](Installation/Guide-Installation-OpenStack-Devstack.md)

Ce guide couvre :
- La préparation du système
- L’installation de DevStack
- La configuration de Neutron pour le SDN

  ## ✅ Prérequis

* DevStack installé et opérationnel.
* Exécution depuis la machine DevStack (ou accès API OpenStack configuré).

---

## 🚀 Utilisation

### 1️⃣ Rendre les scripts exécutables

```bash
cd scripts
chmod +x *.sh
```

---

### 2️⃣ Création des projets et utilisateurs

```bash
./setup_tenants.sh
```

📌 Ce script :

* Crée 3 projets :

  * `client_a`
  * `client_b`
  * `client_c`
* Crée leurs utilisateurs respectifs :

  * `user_a`
  * `user_b`
  * `user_c`
* Définit leurs mots de passe :

  * `password_a`
  * `password_b`
  * `password_c`

---

### 3️⃣ Configuration réseau d’un projet

```bash
./create_tenant_network.sh <projet> <utilisateur> <mot_de_passe> <VNI> <sous_réseau>
```

**Exemple :**

```bash
./create_tenant_network.sh client_a user_a password_a 1001 10.1.0.0/24
```

📌 Ce script :

* Crée un réseau privé **VXLAN**
* Crée le sous-réseau associé
* Déploie un routeur
* Connecte le réseau au réseau externe
* Configure un groupe de sécurité (SSH, ICMP, HTTP, trafic interne)

---

### 4️⃣ Déploiement d’une instance

```bash
./launch_instance.sh <projet> <utilisateur> <mot_de_passe> <nom_instance>
```

**Exemple :**

```bash
./launch_instance.sh client_a user_a password_a vm_a1
```

📌 Ce script :

* Télécharge l’image Cirros si nécessaire
* Déploie une instance
* Assigne une IP flottante

---

### 5️⃣ Test d’isolation inter-projets

```bash
./test_isolation.sh
```

📌 Le script :

* Tente un ping entre les instances de `client_a` et `client_b`
* Vérifie que l’isolation réseau est effective

---

## 🧾 Rôle des scripts

| Script                     | Fonction                               |
| -------------------------- | -------------------------------------- |
| `setup_tenants.sh`         | Création des projets et utilisateurs   |
| `create_tenant_network.sh` | Configuration complète du réseau       |
| `launch_instance.sh`       | Déploiement d’une VM avec IP flottante |
| `test_isolation.sh`        | Vérification de l’isolation            |

---

# 3️⃣ Application Flask (Interface Graphique)

Application web simplifiée permettant à chaque projet de consulter ses ressources OpenStack.

## 🖥️ Fonctionnalités

* 🔐 Authentification par projet
* 📊 Dashboard avec indicateurs (réseaux, instances, routeurs, security groups)
* 🌐 Visualisation des réseaux et sous-réseaux
* 💻 Liste des instances avec IP
* 🛡️ Gestion des groupes de sécurité

---

## ⚙️ Installation

### 1️⃣ Installer les dépendances

```bash
cd flask_app
pip install -r requirements.txt
```

---

### 2️⃣ Lancer l’application

```bash
python app.py
```

Par défaut, l'application écoute sur **0.0.0.0:5001**.
Accédez-y via **http://<IP_de_la_machine>:5001** (par exemple _http://192.168.56.1:5001_ si vous utilisez le réseau Host-Only).

---

## 🏗️ Architecture de l’application

| Fichier            | Rôle                               |
| ------------------ | ---------------------------------- |
| `app.py`           | Routes Flask + connexion OpenStack |
| `requirements.txt` | Dépendances Python                 |
| `templates/`       | Templates HTML (Jinja2)            |

---

# 📋 Prérequis généraux

* Installation fonctionnelle de :

  * Keystone
  * Neutron
  * Nova
  * Glance
* Python **3.8+**
* Connectivité réseau vers la VM DevStack

---

# 🔬 Exemple de workflow complet

```bash
cd scripts
./setup_tenants.sh

./create_tenant_network.sh client_a user_a password_a 1001 10.1.0.0/24
./create_tenant_network.sh client_b user_b password_b 1002 10.2.0.0/24
./create_tenant_network.sh client_c user_c password_c 1003 10.3.0.0/24

./launch_instance.sh client_a user_a password_a vm_a1
./launch_instance.sh client_b user_b password_b vm_b1
./launch_instance.sh client_c user_c password_c vm_c1
```

Puis :

```bash
./test_isolation.sh
```

---


# 🏗️ Schéma d’architecture logique (3 Tenants – Isolation VXLAN)

```
                           +----------------------+
                           |     External Net     |
                           | (Provider Network)   |
                           +----------+-----------+
                                      |
                               +------+------+
                               |  Neutron L3 |
                               |   Router    |
                               +------+------+
                                      |
        -----------------------------------------------------------------
        |                               |                               |
+-------+--------+              +-------+--------+              +-------+--------+
|    Tenant A    |              |    Tenant B    |              |    Tenant C    |
|   VXLAN 1001   |              |   VXLAN 1002   |              |   VXLAN 1003   |
+-------+--------+              +-------+--------+              +-------+--------+
        |                               |                               |
   +----+----+                     +----+----+                     +----+----+
   |  VM A1  |                     |  VM B1  |                     |  VM C1  |
   +---------+                     +---------+                     +---------+

          ❌ Pas de communication inter-tenant (Isolation L2 via VXLAN)
```
___
          
# 📘 Licence

📚 Projet fourni à des fins éducatives.
Libre d’utilisation, de modification et d’extension.

