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
cat > local.conf << 'EOF'
[[local|localrc]]

# Mots de passe
ADMIN_PASSWORD=secret
DATABASE_PASSWORD=$ADMIN_PASSWORD
RABBIT_PASSWORD=$ADMIN_PASSWORD
SERVICE_PASSWORD=$ADMIN_PASSWORD

# Hôte
HOST_IP=10.0.2.15
SERVICE_HOST=10.0.2.15

# Désactivation des services superflus
disable_service cinder c-sch c-api c-vol
disable_service heat h-api h-api-cfn h-api-cw h-eng
disable_service tempest
disable_service horizon

# ---------- CONFIGURATION RESEAU CRITIQUE ----------
# Interface physique (NAT VirtualBox)
FLAT_INTERFACE=enp0s3
PUBLIC_INTERFACE=enp0s3
PUBLIC_BRIDGE=br-ex
OVS_PHYSICAL_BRIDGE=br-ex

# Plages IP
FIXED_RANGE=10.0.3.0/24
FLOATING_RANGE=10.0.2.128/25
NETWORK_GATEWAY=10.0.2.1
PUBLIC_NETWORK_GATEWAY=10.0.2.1

# ---------- NEUTRON : ACTIVATION VXLAN ----------
disable_service n-net
enable_service q-svc q-agt q-dhcp q-l3 q-meta

Q_AGENT=openvswitch
Q_ML2_TENANT_NETWORK_TYPE=vxlan
Q_ML2_PLUGIN_MECHANISM_DRIVERS=openvswitch,l2population
Q_USE_SECGROUP=True
FIREWALL_DRIVER=openvswitch
LIBVIRT_FIREWALL_DRIVER=nova.virt.firewall.NoopFirewallDriver

# ---------- PLAGES VXLAN ----------
VXLAN_VNID_RANGE=1:1000
OVS_ENABLE_TUNNELING=True
ENABLE_TENANT_VLANS=False

# ---------- PLUGINS ----------
enable_plugin neutron https://opendev.org/openstack/neutron
# NE SURTOUT PAS ajouter service_plugins ici, il sera écrasé.

# ---------- CORRECTIF POST-CONFIG ----------
[[post-config|$NEUTRON_CONF]]
[DEFAULT]
# NE PAS DEFINIR service_plugins MANUELLEMENT (cause bug connu)
# Laisser DevStack le gérer.
debug = True
verbose = True

[[post-config|$Q_PLUGIN_CONF_FILE]]
[ml2]
tenant_network_types = vxlan
mechanism_drivers = openvswitch,l2population
type_drivers = vxlan,flat

[ml2_type_vxlan]
vni_ranges = 1:1000

[ml2_type_flat]
flat_networks = public

[ovs]
bridge_mappings = public:br-ex
local_ip = 10.0.2.15
enable_tunneling = True

[agent]
tunnel_types = vxlan
l2_population = True
arp_responder = True

[[post-config|/etc/neutron/dhcp_agent.ini]]
[DEFAULT]
enable_isolated_metadata = True
force_metadata = True

[[post-config|/etc/neutron/metadata_agent.ini]]
[DEFAULT]
nova_metadata_host = $SERVICE_HOST
metadata_proxy_shared_secret = $ADMIN_PASSWORD
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

- URL : **http://[HOST_IP]/dashboard**

Les Identifiants :
Identifiants :

- Utilisateur : *admin*

- Mot de passe : *secret*
