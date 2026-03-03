#!/bin/bash
# ================================================================
# cleanup.sh — Supprime toute l'infrastructure créée via Flask
# Usage : ./cleanup.sh
# ================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'

log()     { echo -e "${GREEN}[✔]${NC} $1"; }
warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
section() { echo -e "\n${BLUE}── $1 ──${NC}"; }

set +u
source ~/devstack/openrc admin admin
set -u

# Confirmation
echo -e "${RED}⚠ ATTENTION : Ce script supprime TOUTE l'infrastructure SDN.${NC}"
read -rp "Confirmer ? (oui/non) : " CONFIRM
[[ "$CONFIRM" != "oui" ]] && echo "Annulé." && exit 0

section "Suppression des instances"
for ID in $(openstack server list --all-projects -f value -c ID 2>/dev/null); do
    openstack server delete "$ID" --wait 2>/dev/null && log "VM $ID supprimée"
done

section "Suppression des IPs flottantes"
for ID in $(openstack floating ip list -f value -c ID 2>/dev/null); do
    openstack floating ip delete "$ID" 2>/dev/null && log "FIP $ID supprimée"
done

section "Suppression des routeurs"
for ID in $(openstack router list -f value -c ID 2>/dev/null); do
    # Retirer les interfaces
    for SUBNET in $(openstack router show "$ID" -f json 2>/dev/null | \
                   python3 -c "import sys,json; r=json.load(sys.stdin); \
                   [print(i['subnet_id']) for i in r.get('interfaces_info',[])]" 2>/dev/null); do
        openstack router remove subnet "$ID" "$SUBNET" 2>/dev/null || true
    done
    openstack router unset --external-gateway "$ID" 2>/dev/null || true
    openstack router delete "$ID" 2>/dev/null && log "Routeur $ID supprimé"
done

section "Suppression des réseaux (hors public)"
for ID in $(openstack network list -f value -c ID 2>/dev/null); do
    NAME=$(openstack network show "$ID" -f value -c name 2>/dev/null)
    if [[ "$NAME" != "public" ]]; then
        for SUBNET in $(openstack subnet list --network "$ID" -f value -c ID 2>/dev/null); do
            openstack subnet delete "$SUBNET" 2>/dev/null || true
        done
        openstack network delete "$ID" 2>/dev/null && log "Réseau $NAME supprimé"
    fi
done

section "Suppression des groupes de sécurité (hors default)"
for ID in $(openstack security group list -f value -c ID 2>/dev/null); do
    NAME=$(openstack security group show "$ID" -f value -c name 2>/dev/null)
    if [[ "$NAME" != "default" ]]; then
        openstack security group delete "$ID" 2>/dev/null && log "SG $NAME supprimé"
    fi
done

echo -e "\n${GREEN}Nettoyage terminé.${NC}"
