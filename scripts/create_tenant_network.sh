#!/bin/bash
# create_tenant_network.sh
# Usage: ./create_tenant_network.sh <project> <user> <password> <vni> <subnet_cidr>

PROJECT=$1
USER=$2
PASSWORD=$3
VNI=$4
SUBNET_CIDR=$5

# Extraire le préfixe réseau pour la gateway
GATEWAY=$(echo $SUBNET_CIDR | sed 's/0\/24/1/')

# Charger le contexte du projet
export OS_USERNAME=$USER
export OS_PASSWORD=$PASSWORD
export OS_PROJECT_NAME=$PROJECT
export OS_AUTH_URL=http://10.0.2.15/identity
export OS_IDENTITY_API_VERSION=3
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default

echo "=== Configuration du réseau pour le projet $PROJECT ==="

# Nom des ressources
NET_NAME="${PROJECT}_private_net"
SUBNET_NAME="${PROJECT}_subnet"
ROUTER_NAME="${PROJECT}_router"
SECGROUP_NAME="${PROJECT}_secgroup"

# Créer le réseau VXLAN
echo "Création du réseau VXLAN (VNI $VNI)..."
openstack network create --provider-network-type vxlan --provider-segment $VNI $NET_NAME

# Créer le sous-réseau
echo "Création du sous-réseau $SUBNET_CIDR..."
openstack subnet create --network $NET_NAME --subnet-range $SUBNET_CIDR --gateway $GATEWAY $SUBNET_NAME

# Créer le routeur
echo "Création du routeur..."
openstack router create $ROUTER_NAME

# Connecter le routeur au réseau externe
PUBLIC_NET_ID=$(openstack network list --external -f value -c ID | head -1)
if [ -n "$PUBLIC_NET_ID" ]; then
    openstack router set $ROUTER_NAME --external-gateway $PUBLIC_NET_ID
    echo "Routeur connecté au réseau externe."
else
    echo "Attention : aucun réseau externe trouvé."
fi

# Ajouter le sous-réseau au routeur
openstack router add subnet $ROUTER_NAME $SUBNET_NAME

# Créer le groupe de sécurité
echo "Création du groupe de sécurité..."
openstack security group create $SECGROUP_NAME --description "Groupe de sécurité pour $PROJECT"

# Règles de base : SSH, ICMP, HTTP
openstack security group rule create --protocol tcp --dst-port 22 --remote-ip 0.0.0.0/0 $SECGROUP_NAME
openstack security group rule create --protocol icmp $SECGROUP_NAME
openstack security group rule create --protocol tcp --dst-port 80 --remote-ip 0.0.0.0/0 $SECGROUP_NAME
openstack security group rule create --protocol tcp --dst-port 443 --remote-ip 0.0.0.0/0 $SECGROUP_NAME
# Autoriser le trafic interne au sous-réseau
openstack security group rule create --protocol any --remote-ip $SUBNET_CIDR $SECGROUP_NAME

echo "Terminé pour $PROJECT."
