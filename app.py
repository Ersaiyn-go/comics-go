from fileinput import filename
import os
from dotenv import load_dotenv
import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, current_user
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy import text




# --- Настройки Flask ---
app = Flask(__name__)

load_dotenv() 


database_url = os.getenv('DATABASE_URL')

if database_url:
    print("Using DATABASE_URL from environment")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    print("Using local PostgreSQL database")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:tucson@localhost:5432/manga_db'
app.config['UPLOAD_FOLDER'] = 'static/img'
app.secret_key = 'tucson'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Модели ---
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')



class Comic(db.Model):
    __tablename__ = 'comics'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    genre = db.Column(db.String(50), nullable=False, default='Unknown')   
    is_recommended = db.Column(db.Boolean, default=False)  

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending')  # Статус заказа: 'pending', 'confirmed', и т.д.
    user = db.relationship('User', backref=db.backref('orders', lazy=True))

    def __repr__(self):
        return f'<Order {self.id} - {self.status}>'
               

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comic_id = db.Column(db.Integer, db.ForeignKey('comics.id'), nullable=False)
    comic = db.relationship('Comic', backref=db.backref('cart_items', lazy=True))
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))

    def __repr__(self):
        return f'<CartItem {self.comic.title}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Декоратор для проверки прав ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- Маршруты ---
@app.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    selected_genre = request.args.get('genre')
    if selected_genre and selected_genre != 'All':
        comics = Comic.query.filter_by(genre=selected_genre).all()
    else:
        comics = Comic.query.all()

    genres = ['All', 'Horror', 'Drama', 'Comedy', 'Detective', 'Action']
    
    is_admin = current_user.is_authenticated and current_user.role == 'admin'
    is_user = current_user.is_authenticated and current_user.role == 'user'

    # Передаем flash-сообщения в шаблон
    return render_template('sitegpt.html', comics=comics, genres=genres, selected_genre=selected_genre, is_admin=is_admin, is_user=is_user)


@app.route('/add_to_cart/<int:comic_id>', methods=['POST'])
@login_required
def add_to_cart(comic_id):
    comic = Comic.query.get_or_404(comic_id)
    if CartItem.query.filter_by(user_id=current_user.id, comic_id=comic.id).first():
        flash('Этот товар уже в вашей корзине!', 'warning')
    else:
        cart_item = CartItem(user_id=current_user.id, comic_id=comic.id)
        db.session.add(cart_item)
        db.session.commit()
        flash('Товар добавлен в корзину!', 'success')
    return redirect(url_for('home'))


@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('cart.html', cart_items=cart_items)


@app.route('/delete_cart_item/<int:item_id>', methods=['POST'])
@login_required
def delete_cart_item(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Товар удалён из корзины.', 'success')
    else:
        flash('Ошибка удаления товара из корзины.', 'danger')
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    # Логика оформления заказа
    # Например, получение товаров из корзины текущего пользователя
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_price = sum(item.comic.price for item in cart_items)

    return render_template('checkout.html', cart_items=cart_items, total_price=total_price)


@app.route('/confirm_order', methods=['POST'])
@login_required
def confirm_order():
    # Логика подтверждения заказа
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if cart_items:
        total_price = sum(item.comic.price for item in cart_items)
        
        # Создаем новый заказ
        order = Order(user_id=current_user.id, total_price=total_price)
        db.session.add(order)
        db.session.commit()

        # Перемещаем товары в заказ или изменяем их статус
        for item in cart_items:
            item.status = 'confirmed'  # Пример изменения статуса, если необходимо
            item.order_id = order.id  # Привязываем товар к заказу
            db.session.add(item)
        
        db.session.commit()

        # Очистка корзины
        db.session.query(CartItem).filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash('Ваш заказ был успешно оформлен!', 'success')
        return redirect(url_for('home'))  # Перенаправляем на главную страницу
    else:
        flash('Ваша корзина пуста, невозможно оформить заказ.', 'danger')
        return redirect(url_for('cart'))


@app.route('/order_confirmation')
@login_required
def order_confirmation():
    return render_template('order_confirmation.html')


@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        return render_template('403.html'), 403  

    users = User.query.all()

    if request.method == 'POST':
        user_id = request.form['user_id']
        new_role = request.form['new_role']

        user = User.query.get(user_id)
        if user:
            user.role = new_role
            db.session.commit()
            flash(f'Роль пользователя {user.username} изменена на {new_role}', 'success')
        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', users=users)



@app.route('/count_genre/<genre>')
@admin_required
def count_genre(genre):
    result = db.session.execute(f"SELECT count_comics_by_genre('{genre}')")
    count = result.scalar()
    flash(f'Количество комиксов в жанре "{genre}": {count}', 'info')
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Аккаунт создан!', 'success')
            login_user(new_user)
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка регистрации: {e}', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))  
        else:
            flash('Неверные данные для входа', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


# --- CRUD Комиксы ---
@app.route('/add_comic', methods=['GET', 'POST'])
@admin_required
def add_comic():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        genre = request.form['genre']
        is_recommended = 'is_recommended' in request.form

        file = request.files['image_file']

        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            name_part, ext_part = os.path.splitext(original_filename)
            unique_suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{name_part}_{unique_suffix}{ext_part}"

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))  # Save using unique_filename
            image_url = f'img/{unique_filename}'  # Update image_url with unique filename

            new_comic = Comic(
                title=title,
                description=description,
                price=price,
                image_url=image_url,
                genre=genre,
                is_recommended=is_recommended
            )
            try:
                db.session.add(new_comic)
                db.session.commit()
                flash('Комикс успешно добавлен!', 'success')
                return redirect(url_for('home'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении: {e}', 'danger')
        else:
            flash('Недопустимый формат файла!', 'danger')
    return render_template('add_comic.html')




@app.route('/edit_comic/<int:comic_id>', methods=['GET', 'POST'])
@admin_required
def edit_comic(comic_id):
    comic = Comic.query.get_or_404(comic_id)

    if request.method == 'POST':
        comic.title = request.form['title']
        comic.description = request.form['description']
        comic.price = request.form['price']
        comic.genre = request.form['genre']
        comic.is_recommended = 'is_recommended' in request.form

        file = request.files.get('image_file')
        
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            name_part, ext_part = os.path.splitext(original_filename)
            unique_suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{name_part}_{unique_suffix}{ext_part}"
           
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))  # Save using unique_filename
            image_url = f'img/{unique_filename}'  # Update image_url with unique filename

            # Update the image_url for the existing comic
            comic.image_url = image_url

        try:
            db.session.commit()
            flash('Комикс успешно обновлен!', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении: {e}', 'danger')

    return render_template('edit_comic.html', comic=comic)



@app.route('/delete_comic/<int:comic_id>', methods=['POST'])
@admin_required
def delete_comic(comic_id):
    comic = Comic.query.get_or_404(comic_id)

    # Получаем пользователей, у кого этот комикс в корзине
    users_with_comic = db.session.execute(
        text("""
            SELECT u.username
            FROM cart_item c
            JOIN "user" u ON c.user_id = u.id
            WHERE c.comic_id = :cid
        """),
        {'cid': comic_id}
    ).fetchall()

    usernames = [row[0] for row in users_with_comic]

    if usernames:
        user_list = ', '.join(usernames)
        flash(f'⚠️ Этот комикс есть в корзинах у: {user_list}. Он будет удалён из их корзин.', 'warning-long')

    try:
        # Удаляем вручную связанные записи из корзины
        db.session.execute(
            text("DELETE FROM cart_item WHERE comic_id = :cid"),
            {'cid': comic_id}
        )

        # Теперь удаляем сам комикс
        db.session.delete(comic)
        db.session.commit()

        flash('Комикс удален.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {e}', 'danger')

    return redirect(url_for('home'))




# --- Обработчик ошибки 403 ---
@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

# --- Запуск приложения ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Comic.query.first():
            demo_comic = Comic(title="Demo Comic", description="First comic", price=1500, image_url="img/Алдар.webp")
            db.session.add(demo_comic)
            db.session.commit()

    app.run(host='0.0.0.0', port=5000, debug=True)