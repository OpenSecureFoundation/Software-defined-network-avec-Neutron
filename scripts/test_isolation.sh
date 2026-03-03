#!/bin/bash
# ================================================================
# test_isolation.sh — Vérifie l'isolation VXLAN entre réseaux
# Usage : ./test_isolation.sh
# ================================================================

set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()     { echo -e "${GREEN}[✔]${NC} $1"; }
fail()    { echo -e "${RED}[✘]${NC} $1"; }
warn()    { echo -e "${YELLOW}[~]${NC} $1"; }
section() { echo -e "\n${BLUE}── $1 ──${NC}"; }

set +u
source ~/devstack/openrc admin admin
set -u

section "Récupération des instances actives"

# Lister toutes les VMs actives avec leurs IPs
mapfile -t VM_LIST < <(openstack server list --status ACTIVE -f value \
    -c ID -c Name -c Networks 2>/dev/null)

if [[ ${#VM_LIST[@]} -lt 2 ]]; then
    warn "Moins de 2 VMs actives trouvées. Lancez d'abord des instances via Flask."
    exit 1
fi

echo -e "${CYAN}VMs actives détectées :${NC}"
openstack server list --status ACTIVE \
    -c Name -c Status -c Networks -c "Flavor" 2>/dev/null

section "Récupération des réseaux VXLAN"

echo -e "${CYAN}Réseaux présents :${NC}"
openstack network list -c Name -c "Provider Network Type" \
    -c "Provider Segmentation ID" 2>/dev/null

section "Tests d'isolation inter-réseaux"

# Récupérer les IPs flottantes
declare -A VM_FIPS
while IFS= read -r line; do
    VM_ID=$(echo "$line" | awk '{print $1}')
    FIP=$(echo "$line"   | awk '{print $2}')
    VM_NAME=$(openstack server show "$VM_ID" -f value -c name 2>/dev/null)
    VM_FIPS["$VM_NAME"]="$FIP"
done < <(openstack floating ip list -f value -c "Fixed IP Address" \
         -c "Floating IP Address" 2>/dev/null | head -10)

# Récupérer toutes les IPs privées par réseau
declare -A NET_IPS
while IFS= read -r server_line; do
    VM_NAME=$(openstack server show "$(echo "$server_line" | awk '{print $1}')" \
              -f value -c name 2>/dev/null)
    NETWORKS=$(openstack server show "$(echo "$server_line" | awk '{print $1}')" \
               -f value -c addresses 2>/dev/null)
    NET_IPS["$VM_NAME"]="$NETWORKS"
done < <(openstack server list --status ACTIVE -f value -c ID 2>/dev/null \
         | awk '{print $1}')

PASS=0; FAIL=0

# ── Test 1 : Ping inter-réseaux (doit ÉCHOUER = isolation OK) ──
section "Test 1 — Isolation L2 VXLAN (ping inter-réseaux)"

VM_NAMES=($(openstack server list --status ACTIVE -f value -c Name 2>/dev/null))

if [[ ${#VM_NAMES[@]} -ge 2 ]]; then
    VM_A="${VM_NAMES[0]}"
    VM_B="${VM_NAMES[1]}"

    NET_A=$(openstack server show "$VM_A" -f value -c addresses 2>/dev/null \
            | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
    NET_B=$(openstack server show "$VM_B" -f value -c addresses 2>/dev/null \
            | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)

    echo -e "  Test ping : ${CYAN}$VM_A${NC} ($NET_A) → ${CYAN}$VM_B${NC} ($NET_B)"

    FIP_A="${VM_FIPS[$VM_A]:-}"
    if [[ -n "$FIP_A" ]]; then
        # Tenter le ping depuis VM_A vers l'IP privée de VM_B
        RESULT=$(ssh -o StrictHostKeyChecking=no \
                     -o ConnectTimeout=5 \
                     -o PasswordAuthentication=yes \
                     cirros@"$FIP_A" \
                     "ping -c 2 -W 2 $NET_B 2>/dev/null; echo exitcode:\$?" \
                     2>/dev/null | grep "exitcode" | cut -d: -f2 || echo "1")

        if [[ "$RESULT" == "1" ]]; then
            log "ISOLATION OK — $VM_A ne peut pas pinguer $VM_B (réseaux différents)"
            ((PASS++))
        else
            fail "ISOLATION ÉCHOUÉE — $VM_A peut pinguer $VM_B (vérifier la config VXLAN)"
            ((FAIL++))
        fi
    else
        warn "Pas d'IP flottante sur $VM_A — test SSH ignoré"
        warn "Vérification manuelle requise : connectez-vous à $VM_A et pingez $NET_B"
    fi
fi

# ── Test 2 : Ping intra-réseau (doit RÉUSSIR) ──────────────────
section "Test 2 — Connectivité intra-réseau (ping même réseau)"

# Chercher deux VMs sur le même réseau
declare -A NET_VMS
for VM in "${VM_NAMES[@]}"; do
    NET=$(openstack server show "$VM" -f value -c addresses 2>/dev/null \
          | grep -oP '^\w[\w-]+(?==)' | head -1)
    if [[ -n "$NET" ]]; then
        NET_VMS["$NET"]+="$VM "
    fi
done

INTRA_TESTED=false
for NET in "${!NET_VMS[@]}"; do
    VMS=(${NET_VMS[$NET]})
    if [[ ${#VMS[@]} -ge 2 ]]; then
        VM_X="${VMS[0]}"; VM_Y="${VMS[1]}"
        IP_Y=$(openstack server show "$VM_Y" -f value -c addresses 2>/dev/null \
               | grep -oP '\d+\.\d+\.\d+\.\d+' | head -1)
        FIP_X="${VM_FIPS[$VM_X]:-}"

        echo -e "  Test ping intra : ${CYAN}$VM_X${NC} → ${CYAN}$VM_Y${NC} ($IP_Y)"

        if [[ -n "$FIP_X" ]]; then
            RESULT=$(ssh -o StrictHostKeyChecking=no \
                         -o ConnectTimeout=5 \
                         cirros@"$FIP_X" \
                         "ping -c 2 -W 2 $IP_Y 2>/dev/null; echo exitcode:\$?" \
                         2>/dev/null | grep "exitcode" | cut -d: -f2 || echo "1")
            if [[ "$RESULT" == "0" ]]; then
                log "CONNECTIVITÉ OK — $VM_X peut pinguer $VM_Y (même réseau)"
                ((PASS++))
            else
                fail "CONNECTIVITÉ ÉCHOUÉE — $VM_X ne peut pas pinguer $VM_Y"
                ((FAIL++))
            fi
        fi
        INTRA_TESTED=true
        break
    fi
done

[[ "$INTRA_TESTED" == false ]] && \
    warn "Pas assez de VMs sur le même réseau pour le test intra-réseau"

# ── Test 3 : Ping Internet ──────────────────────────────────
section "Test 3 — Connectivité Internet"

for VM in "${VM_NAMES[@]:0:1}"; do
    FIP="${VM_FIPS[$VM]:-}"
    if [[ -n "$FIP" ]]; then
        echo -e "  Test ping Internet depuis ${CYAN}$VM${NC} ($FIP) → 8.8.8.8"
        RESULT=$(ssh -o StrictHostKeyChecking=no \
                     -o ConnectTimeout=5 \
                     cirros@"$FIP" \
                     "ping -c 2 -W 3 8.8.8.8 2>/dev/null; echo exitcode:\$?" \
                     2>/dev/null | grep "exitcode" | cut -d: -f2 || echo "1")
        if [[ "$RESULT" == "0" ]]; then
            log "INTERNET OK — $VM a accès à Internet via le routeur"
            ((PASS++))
        else
            fail "PAS D'INTERNET — vérifiez la gateway du routeur"
            ((FAIL++))
        fi
    fi
done

# ── Résumé ───────────────────────────────────────────────────
section "Résultats"

TOTAL=$((PASS + FAIL))
echo ""
echo -e "  Tests réussis  : ${GREEN}$PASS / $TOTAL${NC}"
echo -e "  Tests échoués  : ${RED}$FAIL / $TOTAL${NC}"
echo ""

if [[ $FAIL -eq 0 ]]; then
    echo -e "${GREEN}"
    echo "  ┌──────────────────────────────────────────┐"
    echo "  │  ✔ Isolation VXLAN multi-tenant validée  │"
    echo "  │    Les réseaux sont correctement isolés  │"
    echo "  └──────────────────────────────────────────┘"
    echo -e "${NC}"
else
    echo -e "${RED}"
    echo "  ┌──────────────────────────────────────────┐"
    echo "  │  ✘ Des tests ont échoué                  │"
    echo "  │    Vérifiez la config VXLAN et les SGs   │"
    echo "  └──────────────────────────────────────────┘"
    echo -e "${NC}"
fi

