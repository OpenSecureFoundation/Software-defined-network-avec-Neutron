#!/bin/bash
# ================================================================
# setup_admin.sh — Initialisation de l'infrastructure SDN
# Auteur  :  yannmael
# Usage   : ./setup_admin.sh
# ================================================================

set -e

# ── Couleurs ────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()     { echo -e "${GREEN}[✔]${NC} $1"; }
warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
error()   { echo -e "${RED}[✘]${NC} $1"; exit 1; }
section() { echo -e "\n${BLUE}══════════════════════════════════════${NC}";
            echo -e "${CYAN}  $1${NC}";
            echo -e "${BLUE}══════════════════════════════════════${NC}"; }

# ── Vérification admin ───────────────────────────────────────
section "Vérification des droits administrateur"

if [[ -z "${OS_USERNAME:-}" ]]; then
    if [[ -f ~/devstack/openrc ]]; then
        set +u
        source ~/devstack/openrc admin admin
        set +u
        log "Credentials chargés depuis ~/devstack/openrc"
    else
        error "Fichier openrc introuvable. Sourcez vos credentials OpenStack."
    fi
fi

IS_ADMIN=$(openstack role assignment list --user "$OS_USERNAME" \
           --role admin -f value 2>/dev/null | wc -l)

if [[ "$IS_ADMIN" -eq 0 ]]; then
    error "Ce script doit être exécuté avec un compte admin OpenStack."
fi
log "Connecté en tant qu'admin : $OS_USERNAME"

# ── Configuration des quotas admin ───────────────────────────
section "Configuration des quotas pour le projet admin"

# Quotas réseau (Neutron)
openstack quota set \
    --networks       20 \
    --subnets        20 \
    --routers        10 \
    --ports          100 \
    --secgroups      20 \
    --secgroup-rules 200 \
    --floating-ips   20 \
    admin
log "Quotas réseau configurés"

# Quotas compute (Nova)
openstack quota set \
    --instances 20 \
    --cores     40 \
    --ram       51200 \
    --key-pairs 10 \
    admin
log "Quotas compute configurés"

# ── Réseau externe (provider) ────────────────────────────────
section "Vérification du réseau externe public"

EXT_NET=$(openstack network show public -f value -c id 2>/dev/null || echo "")
if [[ -z "$EXT_NET" ]]; then
    warn "Réseau 'public' introuvable — création..."
    openstack network create \
        --external \
        --provider-network-type flat \
        --provider-physical-network public \
        public
    openstack subnet create \
        --network public \
        --subnet-range 192.168.56.0/24 \
        --gateway 192.168.56.1 \
        --no-dhcp \
        --allocation-pool start=192.168.56.100,end=192.168.56.200 \
        public-subnet
    log "Réseau externe 'public' créé"
else
    log "Réseau externe 'public' déjà présent (id: $EXT_NET)"
fi

# ── Flavors de base ──────────────────────────────────────────
section "Vérification des flavors"

declare -A FLAVORS=(
    ["m1.tiny"]="1 512 1"
    ["m1.small"]="1 2048 20"
    ["m1.medium"]="2 4096 40"
)

for NAME in "${!FLAVORS[@]}"; do
    read -r VCPUS RAM DISK <<< "${FLAVORS[$NAME]}"
    EXISTS=$(openstack flavor show "$NAME" -f value -c id 2>/dev/null || echo "")
    if [[ -z "$EXISTS" ]]; then
        openstack flavor create \
            --vcpus "$VCPUS" --ram "$RAM" --disk "$DISK" \
            --public "$NAME" > /dev/null
        log "Flavor $NAME créé (${VCPUS}vCPU / ${RAM}MB RAM / ${DISK}GB)"
    else
        log "Flavor $NAME déjà présent"
    fi
done

# ── Image Cirros ─────────────────────────────────────────────
section "Vérification de l'image Cirros"

CIRROS_EXISTS=$(openstack image list -f value -c Name 2>/dev/null | grep -i cirros | head -1 || echo "")

if [[ -n "$CIRROS_EXISTS" ]]; then
    log "Image cirros déjà présente : $CIRROS_EXISTS"
else
    warn "Image cirros introuvable — recherche locale..."
    LOCAL_IMG=$(find /opt/stack /home -name "*.img" 2>/dev/null | grep -i cirros | head -1 || echo "")

    if [[ -n "$LOCAL_IMG" ]]; then
        openstack image create \
            --disk-format qcow2 \
            --container-format bare \
            --public \
            --file "$LOCAL_IMG" \
            cirros
        log "Image cirros importée depuis $LOCAL_IMG"
    else
        warn "Pas d'image locale — téléchargement..."
        wget -q --show-progress -O /tmp/cirros.img \
            "https://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img"
        openstack image create \
            --disk-format qcow2 --container-format bare \
            --public --file /tmp/cirros.img cirros
        rm -f /tmp/cirros.img
        log "Image cirros importée"
    fi
fi

# ── Résumé final ─────────────────────────────────────────────
section "Initialisation terminée"

echo -e "${GREEN}"
echo "  ┌─────────────────────────────────────────┐"
echo "  │   Infrastructure SDN prête              │"
echo "  │                                         │"
echo "  │   ✔ Quotas admin configurés             │"
echo "  │   ✔ Réseau externe vérifié              │"
echo "  │   ✔ Flavors disponibles                 │"
echo "  │   ✔ Image Cirros disponible             │"
echo "  │                                         │"
echo "  │   → Lancez l'application Flask :        │"
echo "  │     cd ~/sdn-dashboard && python app.py │"
echo "  └─────────────────────────────────────────┘"
echo -e "${NC}"
