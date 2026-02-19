#!/bin/bash
# test_isolation.sh

source ~/devstack/openrc admin admin

echo "=== Test d'isolation entre projets ==="

# Récupérer les IP flottantes des instances
FIP_A=$(openstack floating ip list --project client_a -f value -c "Floating IP Address" | head -1)
FIP_B=$(openstack floating ip list --project client_b -f value -c "Floating IP Address" | head -1)

if [ -z "$FIP_A" ] || [ -z "$FIP_B" ]; then
    echo "Assurez-vous que des instances avec IP flottante existent dans client_a et client_b."
    exit 1
fi

echo "Instance A : $FIP_A"
echo "Instance B : $FIP_B"

# Tester ping de A vers B
echo "Ping de A vers B (devrait échouer) :"
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 cirros@$FIP_A "ping -c 2 $FIP_B" 2>/dev/null && echo "=> CONNEXION POSSIBLE (échec de l'isolation)" || echo "=> Isolation OK (pas de ping)"

# Tester ping de B vers A
echo "Ping de B vers A (devrait échouer) :"
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 cirros@$FIP_B "ping -c 2 $FIP_A" 2>/dev/null && echo "=> CONNEXION POSSIBLE (échec de l'isolation)" || echo "=> Isolation OK (pas de ping)"
