## 🧰 Prérequis

### Système
- Ubuntu **22.04-Live-Server LTS**
- Accès Internet stable
- Utilisateur avec droits `sudo`

### Ressources minimales recommandées
- RAM :  **16Go** (Minimum 8Go)
- CPU : **6 vCPU** (Minimum 4Go)
- Disque : **100Go** (Minimum 40Go)
- Hyperviseur : **VirtualBox / VMWare** 

___

## 🏗️ Architecture technique

- **Plateforme cloud** : OpenStack (DevStack)
- **Service réseau** : Neutron
- **Commutateur virtuel** : Open vSwitch (OVS)
- **Plugin réseau** : ML2
- **Type de réseau locataire** : VLAN / VXLAN
- **Interface utilisateur** : Horizon

---

## 🚀 Installation de DevStack

### 1️⃣ Se placer dans le répertoire personnel
```bash
cd ~
```
### 2️⃣ Cloner le dépôt DevStack
```bash
git clone https://opendev.org/openstack/devstack
cd devstack
```
### 3️⃣ Créer le fichier de configuration local.conf
```bash
cat > local.conf << EOF
[[local|localrc]]

# Mots de passe
ADMIN_PASSWORD=secret
DATABASE_PASSWORD=\$ADMIN_PASSWORD
RABBIT_PASSWORD=\$ADMIN_PASSWORD
SERVICE_PASSWORD=\$ADMIN_PASSWORD

# Activation de Neutron (SDN)
enable_plugin neutron https://opendev.org/openstack/neutron

# Désactivation des services non nécessaires
disable_service cinder c-sch c-api c-vol
disable_service heat h-api h-api-cfn h-api-cw h-eng
disable_service tempest

# Configuration réseau
HOST_IP=10.0.2.15
FLAT_INTERFACE=enp0s3
FIXED_RANGE=10.0.3.0/24
FLOATING_RANGE=10.0.2.128/25

# Environnement VirtualBox (NAT)
MULTI_HOST=0
EOF
```
- FLAT_INTERFACE doit correspondre à l’interface réseau active de la VM
- Les plages IP doivent être cohérentes avec la configuration de l'hyperviseur

### 4️⃣ Lancer l’installation
```bash
./stack.sh
```
- ⏳ Durée estimée : 30 à 60 minutes
- ⚠️ Ne pas interrompre le processus.

___

## 🌐 Accès à Horizon (Dashboard OpenStack)

Une fois l’installation terminée :

- URL : **http://10.0.2.15/dashboard**

Les Identifiants :
Identifiants :

- Utilisateur : *admin*

- Mot de passe : *secret*
