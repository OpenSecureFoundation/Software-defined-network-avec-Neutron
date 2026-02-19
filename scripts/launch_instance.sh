#!/bin/bash
# launch_instance.sh
# Usage: ./launch_instance.sh <project> <user> <password> <instance_name>

PROJECT=$1
USER=$2
PASSWORD=$3
INSTANCE_NAME=$4

export OS_USERNAME=$USER
export OS_PASSWORD=$PASSWORD
export OS_PROJECT_NAME=$PROJECT
export OS_AUTH_URL=http://10.0.2.15/identity
export OS_IDENTITY_API_VERSION=3

echo "=== Lancement d'une instance pour $PROJECT ==="

# Récupérer les IDs nécessaires
NET_ID=$(openstack network show "${PROJECT}_private_net" -f value -c id)
SECGROUP_ID=$(openstack security group show "${PROJECT}_secgroup" -f value -c id)
IMAGE_ID=$(openstack image list -f value -c ID | head -1)
FLAVOR_ID=$(openstack flavor list -f value -c ID | head -1)

if [ -z "$IMAGE_ID" ]; then
    echo "Téléchargement d'une image Cirros..."
    wget -q http://download.cirros-cloud.net/0.5.2/cirros-0.5.2-x86_64-disk.img
    openstack image create "cirros" --file cirros-0.5.2-x86_64-disk.img --disk-format qcow2 --container-format bare --public
    IMAGE_ID=$(openstack image show cirros -f value -c id)
fi

# Créer l'instance
echo "Création de l'instance $INSTANCE_NAME..."
openstack server create --image $IMAGE_ID --flavor $FLAVOR_ID --nic net-id=$NET_ID --security-group $SECGROUP_ID $INSTANCE_NAME

# Attendre que l'instance soit active
sleep 5

# Créer et attacher une IP flottante
FLOATING_IP=$(openstack floating ip create public -f value -c floating_ip_address 2>/dev/null)
if [ -n "$FLOATING_IP" ]; then
    openstack server add floating ip $INSTANCE_NAME $FLOATING_IP
    echo "IP flottante attribuée : $FLOATING_IP"
else
    echo "Impossible d'attribuer une IP flottante."
fi

echo "Instance $INSTANCE_NAME créée."
