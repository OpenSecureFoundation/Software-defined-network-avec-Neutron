"""
SDN Manager - Application Flask pour la gestion SDN avec OpenStack Neutron
OpenSecureFoundation
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import openstack, os, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sdn-openstack-secret-2024')

# ── Helpers ──────────────────────────────────────────────────

def get_connection():
    if 'username' not in session:
        return None
    try:
        return openstack.connect(
            auth_url            = session.get('auth_url', 'http://localhost/identity'),
            project_name        = session['project'],
            username            = session['username'],
            password            = session['password'],
            user_domain_name    = 'Default',
            project_domain_name = 'Default',
        )
    except Exception as e:
        logger.error(f"Connexion OpenStack échouée : {e}")
        return None

def get_connection_for_project(project_name):
    try:
        return openstack.connect(
            auth_url            = session.get('auth_url', 'http://localhost/identity'),
            project_name        = project_name,
            username            = session['username'],
            password            = session['password'],
            user_domain_name    = 'Default',
            project_domain_name = 'Default',
        )
    except Exception as e:
        logger.error(f"Connexion projet {project_name} échouée : {e}")
        return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ── Auth ─────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        auth_url = request.form.get('auth_url', 'http://localhost/identity')
        username = request.form.get('username')
        password = request.form.get('password')
        project  = request.form.get('project', 'admin')
        try:
            conn  = openstack.connect(
                auth_url            = auth_url,
                project_name        = project,
                username            = username,
                password            = password,
                user_domain_name    = 'Default',
                project_domain_name = 'Default',
            )
            token = conn.auth_token
            if not token:
                raise Exception("Token invalide")
            role = 'member'
            try:
                roles = [r.name for r in conn.identity.get_token().roles]
                if 'admin' in roles:
                    role = 'admin'
            except Exception:
                if username == 'admin':
                    role = 'admin'
            session.update(
                username = username,
                password = password,
                project  = project,
                auth_url = auth_url,
                os_token = token,
                role     = role,
            )
            flash(f'Bienvenue, {username} !', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            logger.error(f"Erreur login : {e}")
            flash('Identifiants incorrects ou service indisponible.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Déconnexion réussie.', 'info')
    return redirect(url_for('login'))

# ── Dashboard ────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn  = get_connection()
    stats = dict(networks=0, instances=0, routers=0,
                 security_groups=0, floating_ips=0)
    if conn:
        try:
            if session.get('role') == 'admin':
                # Admin voit tout
                stats['instances'] = sum(
                    1 for _ in conn.compute.servers(
                        details=True, all_projects=True))
                stats['networks'] = sum(
                    1 for _ in conn.network.networks())
                stats['routers'] = sum(
                    1 for _ in conn.network.routers())
                stats['security_groups'] = sum(
                    1 for _ in conn.network.security_groups())
                stats['floating_ips'] = sum(
                    1 for _ in conn.network.ips())
            else:
                stats['networks']        = sum(1 for _ in conn.network.networks())
                stats['instances']       = sum(1 for _ in conn.compute.servers())
                stats['routers']         = sum(1 for _ in conn.network.routers())
                stats['security_groups'] = sum(1 for _ in conn.network.security_groups())
                stats['floating_ips']    = sum(1 for _ in conn.network.ips())
        except Exception as e:
            flash(f'Erreur statistiques : {e}', 'warning')
    return render_template('dashboard.html', stats=stats)

# ── Réseaux ──────────────────────────────────────────────────

@app.route('/networks')
@login_required
def networks():
    conn, nets = get_connection(), []
    if conn:
        try:
            for net in conn.network.networks():
                subnets = []
                for sid in net.subnet_ids:
                    try:
                        subnets.append(conn.network.get_subnet(sid))
                    except Exception:
                        pass
                nets.append({'network': net, 'subnets': subnets})
        except Exception as e:
            flash(f'Erreur réseaux : {e}', 'danger')
    return render_template('networks.html', networks=nets)

@app.route('/networks/create', methods=['POST'])
@login_required
def create_network():
    data           = request.get_json()
    target_project = data.get('target_project')
    if session.get('role') == 'admin' and target_project:
        conn = get_connection_for_project(target_project)
    else:
        conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        net_args = {'name': data['name'], 'is_admin_state_up': True}
        if session.get('role') == 'admin' and data.get('vni'):
            net_args['provider:network_type']    = 'vxlan'
            net_args['provider:segmentation_id'] = int(data['vni'])
        network = conn.network.create_network(**net_args)
        dns     = [d.strip() for d in data.get('dns', '8.8.8.8,8.8.4.4').split(',')]
        subnet  = conn.network.create_subnet(
            name            = f"{data['name']}-subnet",
            network_id      = network.id,
            ip_version      = 4,
            cidr            = data['cidr'],
            dns_nameservers = dns,
        )
        return jsonify({'success': True, 'network_id': network.id,
                        'subnet_id': subnet.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/networks/<nid>/update', methods=['PUT'])
@login_required
def update_network(nid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data    = request.get_json()
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'admin_state_up' in data:
            updates['is_admin_state_up'] = data['admin_state_up']
        network = conn.network.update_network(nid, **updates)

        # Mettre à jour le sous-réseau si DNS fourni
        if data.get('dns') and data.get('subnet_id'):
            dns = [d.strip() for d in data['dns'].split(',')]
            conn.network.update_subnet(
                data['subnet_id'],
                dns_nameservers = dns,
            )
        return jsonify({'success': True, 'network_id': network.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/networks/<nid>/delete', methods=['DELETE'])
@login_required
def delete_network(nid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        conn.network.delete_network(nid, ignore_missing=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Routeurs ─────────────────────────────────────────────────

@app.route('/routers')
@login_required
def routers():
    conn              = get_connection()
    router_list, nets = [], []
    if conn:
        try:
            router_list = list(conn.network.routers())
            nets        = list(conn.network.networks())
        except Exception as e:
            flash(f'Erreur routeurs : {e}', 'danger')
    return render_template('routers.html', routers=router_list, networks=nets)

@app.route('/routers/create', methods=['POST'])
@login_required
def create_router():
    data           = request.get_json()
    target_project = data.get('target_project')
    if session.get('role') == 'admin' and target_project:
        conn = get_connection_for_project(target_project)
    else:
        conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        ext_net = next(conn.network.networks(
            name=data.get('external_network', 'public')), None)
        args = {'name': data['name'], 'is_admin_state_up': True}
        if ext_net:
            args['external_gateway_info'] = {'network_id': ext_net.id}
        router = conn.network.create_router(**args)
        if data.get('subnet_id'):
            conn.network.add_interface_to_router(router, subnet_id=data['subnet_id'])
        return jsonify({'success': True, 'router_id': router.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/routers/<rid>/update', methods=['PUT'])
@login_required
def update_router(rid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data    = request.get_json()
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'admin_state_up' in data:
            updates['is_admin_state_up'] = data['admin_state_up']

        router = conn.network.update_router(rid, **updates)

        # Modifier la gateway externe si demandé
        if 'external_network' in data:
            if data['external_network']:
                ext_net = next(conn.network.networks(
                    name=data['external_network']), None)
                if ext_net:
                    conn.network.update_router(
                        rid,
                        external_gateway_info={'network_id': ext_net.id}
                    )
            else:
                conn.network.update_router(
                    rid, external_gateway_info={}
                )

        # Ajouter une interface subnet si demandé
        if data.get('add_subnet_id'):
            conn.network.add_interface_to_router(
                rid, subnet_id=data['add_subnet_id'])

        # Retirer une interface subnet si demandé
        if data.get('remove_subnet_id'):
            conn.network.remove_interface_from_router(
                rid, subnet_id=data['remove_subnet_id'])

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/routers/<rid>/delete', methods=['DELETE'])
@login_required
def delete_router(rid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        conn.network.delete_router(rid, ignore_missing=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Instances ────────────────────────────────────────────────

@app.route('/instances')
@login_required
def instances():
    conn = get_connection()
    srv  = []
    nets = flavors = images = kps = sgs = []
    if conn:
        try:
            # Admin voit toutes les VMs de tous les projets
            if session.get('role') == 'admin':
                srv = list(conn.compute.servers(details=True, all_projects=True))
            else:
                srv = list(conn.compute.servers(details=True))

            nets    = list(conn.network.networks())
            flavors = list(conn.compute.flavors())
            images  = list(conn.compute.images())
            kps     = list(conn.compute.keypairs())
            sgs     = list(conn.network.security_groups())
        except Exception as e:
            flash(f'Erreur instances : {e}', 'danger')
    return render_template('instances.html',
        instances=srv, networks=nets, flavors=flavors,
        images=images, keypairs=kps, security_groups=sgs)

@app.route('/instances/<iid>/update', methods=['PUT'])
@login_required
def update_instance(iid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data    = request.get_json()
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'description' in data:
            updates['description'] = data['description']
        conn.compute.update_server(iid, **updates)

        # Modifier les groupes de sécurité si demandé
        if 'security_groups' in data:
            server = conn.compute.get_server(iid)
            # Retirer les anciens SGs
            for sg in server.security_groups:
                try:
                    conn.compute.remove_security_group_from_server(
                        server, sg['name'])
                except Exception:
                    pass
            # Ajouter les nouveaux SGs
            for sg_name in data['security_groups']:
                try:
                    conn.compute.add_security_group_to_server(server, sg_name)
                except Exception:
                    pass

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/instances/<iid>/action', methods=['POST'])
@login_required
def instance_action(iid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        action = request.get_json().get('action')
        server = conn.compute.get_server(iid)
        if not server:
            return jsonify({'error': 'Instance introuvable'}), 404

        if   action == 'start':  conn.compute.start_server(server)
        elif action == 'stop':   conn.compute.stop_server(server)
        elif action == 'reboot': conn.compute.reboot_server(server, reboot_type='SOFT')
        elif action == 'delete': conn.compute.delete_server(iid)
        elif action == 'attach_floating_ip':
            ports = list(conn.network.ports(device_id=iid))
            if not ports:
                return jsonify({'error': 'Aucun port réseau trouvé'}), 404
            port = ports[0]
            existing = list(conn.network.ips(port_id=port.id))
            if existing:
                return jsonify({'success': True,
                                'floating_ip': existing[0].floating_ip_address,
                                'message': 'IP flottante déjà assignée'})
            ext      = next(conn.network.networks(name='public'), None)
            if not ext:
                return jsonify({'error': 'Réseau externe "public" introuvable'}), 404
            free_ips = [ip for ip in conn.network.ips(floating_network_id=ext.id)
                        if ip.port_id is None]
            fip = free_ips[0] if free_ips else \
                  conn.network.create_ip(floating_network_id=ext.id)
            conn.network.update_ip(fip.id, port_id=port.id)
            fip = conn.network.get_ip(fip.id)
            return jsonify({'success': True, 'floating_ip': fip.floating_ip_address})

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Erreur action instance : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/instances/<iid>/attach_network', methods=['POST'])
@login_required
def attach_network(iid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data = request.get_json()
        port = conn.network.create_port(network_id=data['network_id'])
        conn.compute.create_server_interface(iid, port_id=port.id)
        return jsonify({'success': True, 'port_id': port.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Groupes de sécurité ──────────────────────────────────────

@app.route('/security_groups')
@login_required
def security_groups():
    conn, groups = get_connection(), []
    if conn:
        try:
            groups = list(conn.network.security_groups())
        except Exception as e:
            flash(f'Erreur SG : {e}', 'danger')
    return render_template('security_groups.html', security_groups=groups)

@app.route('/security_groups/create', methods=['POST'])
@login_required
def create_security_group():
    data           = request.get_json()
    target_project = data.get('target_project')
    if session.get('role') == 'admin' and target_project:
        conn = get_connection_for_project(target_project)
    else:
        conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        sg = conn.network.create_security_group(
            name        = data['name'],
            description = data.get('description', ''),
        )
        for rule in data.get('rules', []):
            conn.network.create_security_group_rule(
                security_group_id = sg.id,
                direction         = rule.get('direction', 'ingress'),
                protocol          = rule.get('protocol', 'tcp'),
                port_range_min    = rule.get('port_min'),
                port_range_max    = rule.get('port_max'),
                remote_ip_prefix  = rule.get('remote_ip', '0.0.0.0/0'),
                ethertype         = 'IPv4',
            )
        return jsonify({'success': True, 'sg_id': sg.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/security_groups/<sgid>/update', methods=['PUT'])
@login_required
def update_security_group(sgid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data    = request.get_json()
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'description' in data:
            updates['description'] = data['description']
        conn.network.update_security_group(sgid, **updates)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/security_groups/<sgid>/rule', methods=['POST'])
@login_required
def add_sg_rule(sgid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data = request.get_json()
        rule = conn.network.create_security_group_rule(
            security_group_id = sgid,
            direction         = data.get('direction', 'ingress'),
            protocol          = data.get('protocol', 'tcp'),
            port_range_min    = data.get('port_min'),
            port_range_max    = data.get('port_max'),
            remote_ip_prefix  = data.get('remote_ip', '0.0.0.0/0'),
            ethertype         = 'IPv4',
        )
        return jsonify({'success': True, 'rule_id': rule.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/security_groups/rules/<rule_id>/delete', methods=['DELETE'])
@login_required
def delete_sg_rule(rule_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        conn.network.delete_security_group_rule(rule_id, ignore_missing=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/security_groups/<sgid>/delete', methods=['DELETE'])
@login_required
def delete_security_group(sgid):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        conn.network.delete_security_group(sgid, ignore_missing=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Utilisateurs (admin uniquement) ─────────────────────────

@app.route('/users')
@login_required
@admin_required
def users():
    conn         = get_connection()
    user_list    = []
    project_list = []
    role_list    = []
    if conn:
        try:
            user_list    = list(conn.identity.users())
            project_list = list(conn.identity.projects())
            role_list    = list(conn.identity.roles())
        except Exception as e:
            flash(f'Erreur chargement utilisateurs : {e}', 'danger')
    return render_template('users.html',
        users=user_list, projects=project_list, roles=role_list)

@app.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data     = request.get_json()
        username = data['username']
        password = data['password']
        role     = data.get('role', 'member')
        project  = conn.identity.create_project(
            name        = data.get('project', f"{username}-project"),
            description = f"Projet de {username}",
            domain_id   = 'default',
            is_enabled  = True,
        )
        user = conn.identity.create_user(
            name       = username,
            password   = password,
            domain_id  = 'default',
            is_enabled = True,
        )
        role_obj = next(conn.identity.roles(name=role), None)
        if not role_obj:
            return jsonify({'error': f"Rôle '{role}' introuvable"}), 404
        conn.identity.assign_project_role_to_user(
            project = project.id,
            user    = user.id,
            role    = role_obj.id,
        )
        return jsonify({'success': True, 'user_id': user.id,
                        'project_id': project.id, 'username': username,
                        'project': project.name, 'role': role})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users/<user_id>/update', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data    = request.get_json()
        updates = {}
        if 'username' in data and data['username']:
            updates['name'] = data['username']
        if 'password' in data and data['password']:
            updates['password'] = data['password']
        if 'email' in data:
            updates['email'] = data['email']
        if updates:
            conn.identity.update_user(user_id, **updates)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users/<user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        data       = request.get_json()
        project_id = data['project_id']
        new_role   = data['role']
        assignments = list(conn.identity.role_assignments(
            user_id=user_id, project_id=project_id))
        for assignment in assignments:
            conn.identity.unassign_project_role_from_user(
                project=project_id, user=user_id,
                role=assignment.role['id'])
        role_obj = next(conn.identity.roles(name=new_role), None)
        if not role_obj:
            return jsonify({'error': f"Rôle '{new_role}' introuvable"}), 404
        conn.identity.assign_project_role_to_user(
            project=project_id, user=user_id, role=role_obj.id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users/<user_id>/delete', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        conn.identity.delete_user(user_id, ignore_missing=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/users/<user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Non connecté'}), 401
    try:
        user       = conn.identity.get_user(user_id)
        new_status = not user.is_enabled
        conn.identity.update_user(user_id, is_enabled=new_status)
        return jsonify({'success': True, 'enabled': new_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API temps réel ───────────────────────────────────────────

@app.route('/api/projects')
@login_required
@admin_required
def api_projects():
    conn = get_connection()
    if not conn:
        return jsonify([])
    try:
        return jsonify([{'id': p.id, 'name': p.name}
                        for p in conn.identity.projects()
                        if p.name != 'admin'])
    except Exception:
        return jsonify([])

@app.route('/api/networks/<project_name>')
@login_required
@admin_required
def api_networks_for_project(project_name):
    conn = get_connection_for_project(project_name)
    if not conn:
        return jsonify([])
    try:
        return jsonify([
            {'id': n.id, 'name': n.name,
             'subnets': [{'id': s} for s in n.subnet_ids]}
            for n in conn.network.networks()
        ])
    except Exception:
        return jsonify([])

@app.route('/api/topology')
@login_required
def api_topology():
    conn = get_connection()
    if not conn:
        return jsonify({'nodes': [], 'edges': []})
    try:
        nodes, edges = [], []

        # Récupérer toutes les ressources
        nets    = list(conn.network.networks())
        routers = list(conn.network.routers())

        # Admin voit les VMs de tous les projets
        if session.get('role') == 'admin':
            servers = list(conn.compute.servers(details=True, all_projects=True))
        else:
            servers = list(conn.compute.servers(details=True))

        # Trouver le réseau externe (public)
        ext_net = next(
            (n for n in nets if n.get('router:external') or
             n.name == 'public'), None
        )
        ext_net_id = ext_net.id if ext_net else None

        # Nœud Internet
        nodes.append({
            'id'    : 'ext-net',
            'label' : 'Internet',
            'type'  : 'external',
            'color' : '#6366f1',
            'shape' : 'triangle',
        })

        # Nœuds réseaux
        for net in nets:
            # Ne pas afficher le réseau public comme nœud séparé
            # il est représenté par le triangle Internet
            if net.id == ext_net_id:
                continue
            nodes.append({
                'id'    : f"net-{net.id}",
                'label' : net.name,
                'type'  : 'network',
                'color' : '#3b82f6',
                'shape' : 'box',
            })

        # Nœuds routeurs + liens
        for r in routers:
            nodes.append({
                'id'    : f"router-{r.id}",
                'label' : r.name,
                'type'  : 'router',
                'color' : '#f59e0b',
                'shape' : 'diamond',
            })

            # Lien routeur → Internet si gateway externe définie
            if r.external_gateway_info:
                gw_net_id = r.external_gateway_info.get('network_id')
                if gw_net_id == ext_net_id or gw_net_id:
                    edges.append({
                        'from' : f"router-{r.id}",
                        'to'   : 'ext-net',
                    })

            # Liens routeur → réseaux internes via ses ports
            for port in conn.network.ports(device_id=r.id):
                if port.network_id and port.network_id != ext_net_id:
                    edges.append({
                        'from' : f"router-{r.id}",
                        'to'   : f"net-{port.network_id}",
                    })

        # Nœuds VMs + liens vers leurs réseaux
        for s in servers:
            color = '#10b981' if s.status == 'ACTIVE' else '#ef4444'
            nodes.append({
                'id'     : f"vm-{s.id}",
                'label'  : s.name,
                'type'   : 'vm',
                'color'  : color,
                'shape'  : 'ellipse',
                'status' : s.status,
            })
            for net_name, addrs in (s.addresses or {}).items():
                # Trouver le réseau correspondant par son nom
                tgt = next((n for n in nets if n.name == net_name), None)
                if tgt and tgt.id != ext_net_id:
                    edges.append({
                        'from' : f"vm-{s.id}",
                        'to'   : f"net-{tgt.id}",
                    })

        return jsonify({'nodes': nodes, 'edges': edges})

    except Exception as e:
        logger.error(f"Erreur topologie : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subnets/<network_id>')
@login_required
def api_subnets(network_id):
    conn = get_connection()
    if not conn:
        return jsonify([])
    return jsonify([{'id': s.id, 'name': s.name, 'cidr': s.cidr}
                    for s in conn.network.subnets(network_id=network_id)])

@app.route('/api/instances/status')
@login_required
def api_instances_status():
    conn = get_connection()
    if not conn:
        return jsonify([])
    return jsonify([
        {'id': s.id, 'name': s.name, 'status': s.status, 'addresses': s.addresses}
        for s in conn.compute.servers(details=True)
    ])

# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
