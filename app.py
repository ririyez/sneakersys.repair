from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import config
from models import db, Admin, Customer, Repair, StatusHistory
from datetime import datetime
import os
import string
import random

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Silakan login terlebih dahulu'
    
    @login_manager.user_loader
    def load_user(user_id):
        return Admin.query.get(user_id)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # ==================== PUBLIC ROUTES ====================
    
    @app.route('/')
    def index():
        """Landing page"""
        return render_template('index.html')
    
    @app.route('/track', methods=['GET', 'POST'])
    def track():
        """Public tracking page"""
        repair = None
        status_history = None
        error = None
        
        if request.method == 'POST':
            tracking_number = request.form.get('tracking_number', '').strip().upper()
            
            if not tracking_number:
                error = 'Nomor tracking tidak boleh kosong'
            else:
                repair = Repair.query.filter_by(tracking_number=tracking_number).first()
                if not repair:
                    error = 'Nomor tracking tidak ditemukan'
                else:
                    status_history = StatusHistory.query.filter_by(repair_id=repair.id).order_by(StatusHistory.created_at.desc()).all()
        
        return render_template('track.html', repair=repair, status_history=status_history, error=error)
    
    @app.route('/api/track/<tracking_number>')
    def api_track(tracking_number):
        """API endpoint for tracking"""
        repair = Repair.query.filter_by(tracking_number=tracking_number.upper()).first()
        
        if not repair:
            return jsonify({'error': 'Tracking number not found'}), 404
        
        status_history = StatusHistory.query.filter_by(repair_id=repair.id).order_by(StatusHistory.created_at).all()
        
        return jsonify({
            'tracking_number': repair.tracking_number,
            'status': repair.status,
            'status_display': repair.get_status_display(),
            'shoe_type': repair.shoe_type,
            'shoe_color': repair.shoe_color,
            'date_in': repair.date_in.isoformat(),
            'date_completed': repair.date_completed.isoformat() if repair.date_completed else None,
            'cost': repair.cost,
            'history': [
                {
                    'status': h.status,
                    'status_display': Repair.STATUS_CHOICES.get(h.status, h.status),
                    'notes': h.notes,
                    'created_at': h.created_at.isoformat()
                }
                for h in status_history
            ]
        })
    
    # ==================== AUTHENTICATION ROUTES ====================
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Admin login"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Username dan password harus diisi', 'danger')
            else:
                admin = Admin.query.filter_by(username=username).first()
                
                if admin and admin.check_password(password):
                    login_user(admin, remember=True)
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('dashboard'))
                else:
                    flash('Username atau password salah', 'danger')
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        """Admin logout"""
        logout_user()
        flash('Anda telah logout', 'success')
        return redirect(url_for('index'))
    
    # ==================== ADMIN DASHBOARD ROUTES ====================
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Admin dashboard"""
        total_repairs = Repair.query.count()
        received = Repair.query.filter_by(status='received').count()
        in_progress = Repair.query.filter_by(status='in_progress').count()
        completed = Repair.query.filter_by(status='completed').count()
        ready = Repair.query.filter_by(status='ready_pickup').count()
        
        recent_repairs = Repair.query.order_by(Repair.created_at.desc()).limit(10).all()
        
        return render_template('admin/dashboard.html',
                             total_repairs=total_repairs,
                             received=received,
                             in_progress=in_progress,
                             completed=completed,
                             ready=ready,
                             recent_repairs=recent_repairs)
    
    @app.route('/dashboard/repairs')
    @login_required
    def repairs_list():
        """List all repairs"""
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', '')
        search = request.args.get('search', '')
        
        query = Repair.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        if search:
            query = query.filter(
                (Repair.tracking_number.ilike(f'%{search}%')) |
                (Repair.shoe_type.ilike(f'%{search}%')) |
                (Customer.name.ilike(f'%{search}%'))
            ).outerjoin(Customer)
        
        repairs = query.order_by(Repair.created_at.desc()).paginate(page=page, per_page=20)
        
        return render_template('admin/repairs_list.html', repairs=repairs, status_filter=status_filter, search=search)
    
    @app.route('/dashboard/repair/<repair_id>')
    @login_required
    def view_repair(repair_id):
        """View repair details"""
        repair = Repair.query.get_or_404(repair_id)
        status_history = StatusHistory.query.filter_by(repair_id=repair_id).order_by(StatusHistory.created_at.desc()).all()
        
        return render_template('admin/view_repair.html', repair=repair, status_history=status_history)
    
    @app.route('/dashboard/repair/add', methods=['GET', 'POST'])
    @login_required
    def add_repair():
        """Add new repair"""
        if request.method == 'POST':
            # Get or create customer
            email = request.form.get('email', '').strip()
            customer = Customer.query.filter_by(email=email).first()
            
            if not customer:
                customer = Customer(
                    name=request.form.get('customer_name', '').strip(),
                    email=email,
                    phone=request.form.get('phone', '').strip(),
                    address=request.form.get('address', '').strip()
                )
                db.session.add(customer)
                db.session.flush()
            
            # Generate tracking number
            tracking_number = generate_tracking_number()
            
            # Create repair
            repair = Repair(
                tracking_number=tracking_number,
                customer_id=customer.id,
                admin_id=current_user.id,
                shoe_type=request.form.get('shoe_type', '').strip(),
                shoe_color=request.form.get('shoe_color', '').strip(),
                problem_description=request.form.get('problem_description', '').strip(),
                status='received'
            )
            
            db.session.add(repair)
            db.session.flush()
            
            # Add initial status history
            status_entry = StatusHistory(
                repair_id=repair.id,
                status='received',
                notes='Sepatu diterima di workshop'
            )
            db.session.add(status_entry)
            db.session.commit()
            
            flash(f'Reparasi baru ditambahkan. Nomor tracking: {tracking_number}', 'success')
            return redirect(url_for('view_repair', repair_id=repair.id))
        
        return render_template('admin/add_repair.html')
    
    @app.route('/dashboard/repair/<repair_id>/status', methods=['POST'])
    @login_required
    def update_repair_status(repair_id):
        """Update repair status"""
        repair = Repair.query.get_or_404(repair_id)
        new_status = request.form.get('status', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if new_status not in Repair.STATUS_CHOICES:
            flash('Status tidak valid', 'danger')
            return redirect(url_for('view_repair', repair_id=repair_id))
        
        repair.status = new_status
        repair.updated_at = datetime.utcnow()
        
        if new_status == 'completed':
            repair.date_completed = datetime.utcnow()
        elif new_status == 'picked_up':
            repair.date_pickup = datetime.utcnow()
        
        status_entry = StatusHistory(
            repair_id=repair.id,
            status=new_status,
            notes=notes or f'Status diubah menjadi {Repair.STATUS_CHOICES[new_status]}'
        )
        
        db.session.add(status_entry)
        db.session.commit()
        
        flash(f'Status diperbarui menjadi {Repair.STATUS_CHOICES[new_status]}', 'success')
        return redirect(url_for('view_repair', repair_id=repair_id))
    
    @app.route('/dashboard/repair/<repair_id>/cost', methods=['POST'])
    @login_required
    def update_repair_cost(repair_id):
        """Update repair cost"""
        repair = Repair.query.get_or_404(repair_id)
        try:
            cost = float(request.form.get('cost', 0))
            repair.cost = cost
            db.session.commit()
            flash(f'Biaya diperbarui: Rp {cost:,.0f}', 'success')
        except ValueError:
            flash('Biaya harus berupa angka', 'danger')
        
        return redirect(url_for('view_repair', repair_id=repair_id))
    
    @app.route('/dashboard/customers')
    @login_required
    def customers_list():
        """List all customers"""
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        query = Customer.query
        
        if search:
            query = query.filter(
                (Customer.name.ilike(f'%{search}%')) |
                (Customer.email.ilike(f'%{search}%')) |
                (Customer.phone.ilike(f'%{search}%'))
            )
        
        customers = query.order_by(Customer.created_at.desc()).paginate(page=page, per_page=20)
        
        return render_template('admin/customers_list.html', customers=customers, search=search)
    
    @app.route('/dashboard/statistics')
    @login_required
    def statistics():
        """Statistics page"""
        total_repairs = Repair.query.count()
        total_customers = Customer.query.count()
        total_revenue = db.session.query(db.func.sum(Repair.cost)).scalar() or 0
        
        # Status breakdown
        status_breakdown = db.session.query(
            Repair.status,
            db.func.count(Repair.id)
        ).group_by(Repair.status).all()
        
        # Recent repairs by month
        monthly_repairs = db.session.query(
            db.func.strftime('%Y-%m', Repair.created_at).label('month'),
            db.func.count(Repair.id).label('count')
        ).group_by('month').order_by('month').all()
        
        return render_template('admin/statistics.html',
                             total_repairs=total_repairs,
                             total_customers=total_customers,
                             total_revenue=total_revenue,
                             status_breakdown=status_breakdown,
                             monthly_repairs=monthly_repairs)
    
    @app.errorhandler(404)
    def not_found(error):
        """404 error handler"""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """500 error handler"""
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    return app

def generate_tracking_number():
    """Generate unique tracking number"""
    prefix = 'SR'  # SneakerRepair
    timestamp = datetime.utcnow().strftime('%Y%m%d')
    random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f'{prefix}{timestamp}{random_code}'

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    app.run(debug=True, host='0.0.0.0', port=5000)
