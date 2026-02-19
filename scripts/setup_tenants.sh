#!/bin/bash
# setup_tenants.sh

set -e

echo "=== Création des projets et utilisateurs ==="

# Charger le contexte admin
source ~/devstack/openrc admin admin

# Définir les projets, utilisateurs et mots de passe
PROJECTS=("client_a" "client_b" "client_c")
USERS=("user_a" "user_b" "user_c")
PASSWORDS=("password_a" "password_b" "password_c")

for i in {0..2}; do
    echo "Création du projet ${PROJECTS[$i]}..."
    openstack project create --description "Projet Client $((i+1))" ${PROJECTS[$i]}

    echo "Création de l'utilisateur ${USERS[$i]}..."
    openstack user create --project ${PROJECTS[$i]} --password ${PASSWORDS[$i]} ${USERS[$i]}

    echo "Attribution du rôle member..."
    openstack role add --project ${PROJECTS[$i]} --user ${USERS[$i]} member
done

echo "Terminé."
