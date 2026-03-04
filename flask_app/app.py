import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import openstack
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)
load_dotenv()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configuration des projets (à adapter si nécessaire)
PROJECTS = {
    'admin': {'user': 'admin', 'password': 'PasswordSvcs!'},
    'client_a': {'user': 'user_a', 'password': 'password_a'},
    'client_b': {'user': 'user_b', 'password': 'password_b'},
    'client_c': {'user': 'user_c', 'password': 'password_c'}
}

class User(UserMixin):
    def __init__(self, project_name):
        self.id = project_name
        self.project_name = project_name
        self.credentials = PROJECTS.get(project_name)

@login_manager.user_loader
def load_user(project_name):
    if project_name in PROJECTS:
        return User(project_name)
    return None

def get_connection():
    """Retourne une connexion OpenStack pour le projet connecté."""
    if not current_user.is_authenticated:
        return None
    creds = current_user.credentials
    return openstack.connect(
        auth_url=os.getenv('OPENSTACK_AUTH_URL', 'http://localhost/identity'),
        project_name=current_user.project_name,
        username=creds['user'],
        password=creds['password'],
        user_domain_name='Default',
        project_domain_name='Default'
    )

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        project = request.form.get('project')
        password = request.form.get('password')
        if project in PROJECTS and PROJECTS[project]['password'] == password:
            user = User(project)
            login_user(user)
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Identifiants incorrects")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_connection()
    stats = {
        'networks': len(list(conn.network.networks())),
        'instances': len(list(conn.compute.servers())),
        'security_groups': len(list(conn.network.security_groups())),
        'routers': len(list(conn.network.routers())),
    }
    return render_template('dashboard.html', stats=stats)

@app.route('/networks')
@login_required
def networks():
    conn = get_connection()
    networks_list = []
    for net in conn.network.networks():
        subnets = list(conn.network.subnets(network_id=net.id))
        networks_list.append({
            'name': net.name,
            'id': net.id,
            'status': net.status,
            'subnets': [s.cidr for s in subnets],
            'shared': net.is_shared,
            'external': net.is_router_external
        })
    return render_template('networks.html', networks=networks_list)

@app.route('/instances')
@login_required
def instances():
    conn = get_connection()
    instances_list = []
    for server in conn.compute.servers():
        instances_list.append({
            'name': server.name,
            'id': server.id,
            'status': server.status,
            'flavor': server.flavor['original_name'],
            'image': server.image['id'] if server.image else 'N/A',
            'addresses': server.addresses
        })
    return render_template('instances.html', instances=instances_list)

@app.route('/security-groups')
@login_required
def security_groups():
    conn = get_connection()
    sec_groups = []
    for sg in conn.network.security_groups():
        rules = []
        for rule in sg.security_group_rules:
            rules.append({
                'direction': rule.direction,
                'protocol': rule.protocol,
                'port_range': f"{rule.port_range_min}-{rule.port_range_max}" if rule.port_range_min else 'Any',
                'remote_ip': rule.remote_ip_prefix or 'Any'
            })
        sec_groups.append({
            'name': sg.name,
            'id': sg.id,
            'description': sg.description,
            'rules': rules
        })
    return render_template('security_groups.html', security_groups=sec_groups)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

