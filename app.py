import flask
from flask import Flask, request, url_for, redirect, render_template, flash
from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired
from flask_login import UserMixin, LoginManager, login_required, logout_user, login_user, current_user
import pymysql
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import time
from datetime import datetime
import os

app = flask.Flask(__name__)

# flask 参数
app.config['SECRET_KEY'] = 'nx8W3LOiPOHsEmY0zP0h'  # 秘钥
# 数据库信息 格式:mysql://user:password@localhost/database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mysql://user:password@localhost/database?charset=utf8'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_required
def secret():
    return 'Only authenticated users are allowed!'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

#表单类
class ReviewForm(FlaskForm):
	review = TextAreaField(validators=[DataRequired()])
	submit = SubmitField('submit')

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class selectForm(FlaskForm):
	selection = StringField(validators=[DataRequired()])
	submit= SubmitField('submit')

#用户类
class User(db.Model, UserMixin):
	__tablename__ = 'User'
	id = db.Column('id', db.Integer, primary_key=True)
	username = db.Column('username', db.String(50))
	password_hash = db.Column('password', db.String(128))
	is_teacher = db.Column('is_teacher', db.Boolean)
	def verify_password(self, password):
		return check_password_hash(self.password_hash,password)

#数据库类，存放留言信息
class Message(db.Model):
	__tablename__ = 'Message'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(20))
	message = db.Column(db.String(256))
	sendtime = db.Column(db.String(20))

#数据库类，存放作业信息;
class Homework(db.Model):
	__tablename__ = 'Homework'
	id = db.Column(db.Integer, primary_key=True)
	homework = db.Column(db.String(256))
	sendtime = db.Column(db.String(20))

class Sign(db.Model):
	__tablename__ = 'Sign'
	id = db.Column('id', db.String(16), primary_key=True)
	count = db.Column('count', db.Integer)
	time = db.Column('time', db.String(256))

	def __init__(self):
		self.count = 0

def connectdb():
    conn = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        db="webdata",
        user="web",
        password="12345678",
        charset="utf8"
    )
    cursor = conn.cursor()
    return conn, cursor


@app.route('/')
@app.route('/index')
@login_required
def index():
	return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		if user is not None and user.verify_password(form.password.data):
			login_user(user, form.remember_me.data)
			return redirect(url_for('index'))
		flash('Invalid username or password.')
	return render_template('loginpage.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
	username = request.form.get('username')
	password = request.form.get('password')
	repassword = request.form.get('repassword')  # get之后跟html表单中的内容名
	message = request.form.get('is_teacher')
	global is_teacher
	is_teacher = 0
	if(message == 'teacher'):
		is_teacher = 1
	# 3 获取完参数
	if request.method == 'POST':
		if not all([username, password, repassword]):
			flash(u'信息输入不完整')
		elif password != repassword:
			flash('两次输入密码不相同')
		else:
			'''
			前面的步骤输入了完整信息
			解下来对信息进行查找
			->在数据库中已存在
			->在数据库中未存在
			'''
			if User.query.filter_by(username=username).first():
				flash(u'该用户名已存在')
			else:
				new_user = User()
				new_user.username = username
				new_user.password_hash = generate_password_hash(password)
				new_user.is_teacher = is_teacher
				if not is_teacher:
					signs = Sign()
					signs.time = "1970-01-01 00:00:00"
					signs.id = username
					db.session.add(signs)
				db.session.add(new_user)
				db.session.commit()
				flash(u'注册成功,现返回登陆界面')
				return redirect(url_for('login'))

	return render_template('registerpage.html')


@app.route('/sign', methods=['GET', 'POST'])
@login_required
def sign():
	row = 0
	day = 0
	is_teacher = current_user.is_teacher
	my_id = current_user.username
	if is_teacher:
		(conn, cursor) = connectdb()
		sql = "select * from Sign"
		cursor.execute(sql)
		conn.commit()
		result = cursor.fetchall()
		return render_template('sign.html', result=result, is_teacher=is_teacher)
	else:
		(conn, cursor) = connectdb()
		sql = "select * from Sign where id=%s"
		cursor.execute(sql, my_id)
		conn.commit()
		result = cursor.fetchone()
		last = result[2]
		# 取数据库内时间
		sql = "update Sign set time=CURRENT_TIMESTAMP where id=%s"
		cursor.execute(sql, my_id)
		conn.commit()
		sql = "select * from Sign where id=%s"
		cursor.execute(sql, my_id)
		conn.commit()
		result = cursor.fetchone()
		new = result[2]
		d1 = datetime.strptime(new, "%Y-%m-%d %H:%M:%S")
		d2 = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
		d = d1-d2
		if d1.date() != d2.date():
			if d.days == 1:
				sql = "update Sign set count=count+1 where id=%s"
				row = cursor.execute(sql, my_id)
				conn.commit()
			else:
				sql = "update Sign set count=1 where id=%s"
				row = cursor.execute(sql, my_id)
				conn.commit()
		else:
			row = 0

		sql = "select * from Sign where id=%s"
		cursor.execute(sql, my_id)
		conn.commit()
		result = cursor.fetchone()
		day = result[1]
		conn.close()
		return render_template('sign.html', is_teacher=is_teacher, row=row, day=day)


@app.route('/function3')
@login_required
def function3():
	return render_template('function3.html')

@app.route('/sendhw', methods=['GET', 'POST'])
@login_required
def sendhw():
	is_teacher = current_user.is_teacher
	if not is_teacher:
		flash('只有老师可以发作业！')
		return render_template('function3.html')
	review = None
	form = ReviewForm()
	if form.validate_on_submit():  # 有评论
		review = form.review.data.replace('\n', '<br/>')
		form.review.data = ''
		homework = Homework(
			homework=review, sendtime=time.strftime('%Y-%m-%d %H:%M:%S'))
		db.session.add(homework)
		db.session.commit()
	hlist = Homework.query.all()
	hlist=hlist[-1:]
	return render_template('sendhw.html', review=review, form=form, hlist=hlist)

@app.route('/myreview',methods=['GET', 'POST'])
def myreview():
	mlist=Message.query.filter(Message.username==current_user.username).all()
	selection = None
	form = selectForm()
	
	if form.validate_on_submit():
		selection = int(form.selection.data)
		form.selection.data = ''
		message_to_del=Message.query.filter(Message.id==selection).first()
		if message_to_del != None:
			db.session.delete(message_to_del)
			db.session.commit()
			mlist=Message.query.filter(Message.username==current_user.username).all()
	return render_template('myreview.html',mlist=mlist,selection=selection,form=form)

@app.route('/gethw')
@login_required
def gethw():
	hlist = Homework.query.all()
	hlist=hlist[-1:]
	return render_template('gethw.html', hlist=hlist)

@app.route('/allmessage')
@login_required
def allmessage():
	mlist=Message.query.all()
	mlist=mlist[::-1]
	return render_template('allmessage.html',mlist=mlist)

@app.route('/allhw')
@login_required
def allhw():
	hlist=Homework.query.all()
	hlist=hlist[::-1]
	return render_template('allhw.html',hlist=hlist)

@app.route('/reveiews', methods=['GET', 'POST'])
@login_required
def function4():
	review = None
	form = ReviewForm()
	if form.validate_on_submit():  # 有评论
		review = form.review.data.replace('\n', '<br/>')
		form.review.data = ''
		message = Message(message=review, sendtime=time.strftime(
			'%Y-%m-%d %H:%M:%S'), username=current_user.username)
		db.session.add(message)
		db.session.commit()
	mlist = Message.query.all()
	mlist=mlist[::-1]
	if len(mlist)>20:
		mlist=mlist[0:20]
	return render_template('function4.html', review=review, form=form, mlist=mlist)

@app.errorhandler(404)  # 传入要处理的错误代码
def page_not_found(e):  # 接受异常对象作为参数
	return render_template('404.html'), 404  # 返回模板和状态码


if __name__ == '__main__':
	#db.drop_all()
	db.create_all()
	app.run()
	#app.run(debug = True)
