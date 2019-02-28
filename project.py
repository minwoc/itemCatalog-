from flask import Flask, render_template, request
from flask import redirect, url_for, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Item, Category, Base, User

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests


app = Flask(__name__)
engine = create_engine('postgresql://catalog:password@localhost/catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(open('client_secrets.json',
    'r').read())['web']['client_id']
APPLICATION_NAME = "Item Catalog Application"

#Identifying the session with random string and numbers; unique state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state

    return render_template('login.html', STATE=state)

#Function for handling one time code flow for client's call back function
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    #Storing interetsted parameters like username, email, and etc in login_session
    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']


    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    #flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output



#Disconnect function for user to disconnect from google account
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user
    #Grab credentials by login_session
    access_token = login_session.get('access_token')
    if access_token is None:
        #Don't have record of a user
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    #Use access token and passing it into Google's URL
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        #Succesfully disconnected
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        #Something went terribly wrong.
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# Disconnect based on provider, only Google in this case
@app.route('/disconnect')
def disconnect():
    if login_session['provider'] == 'google':
        gdisconnect()
        del login_session['gplus_id']
        del login_session['access_token']

    #Using delete command to delete credentials, gplus_id, username, and email
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    del login_session['user_id']
    del login_session['provider']
    return redirect(url_for('showCategorys'))



#Function for main page passing all of cateogry and item to
#render_template so queries can be passed onto other functions to create more pages
@app.route('/')
@app.route('/category/')
def showCategorys():
    cate = session.query(Category).all()
    ite = session.query(Item).all()
    return render_template('categorys.html', categoryo=cate, itemyo=ite)

#Function for cateogory's items. This function will create foreign key relationship with
#category and item to get specific category's itemsself.
#Render template will check to see if user is logged in or not.
#If logged in, user is able to edit/delete/add. If not, the render public page with no options of edit/delete/add.
@app.route('/category/<category_name>/')
@app.route('/category/<category_name>/item/')
def showItem(category_name):
    allcatenig = session.query(Category).all() #Must display all the categories on the side (All Category)
    #allitenig = session.query(Category.all())
    catenig = session.query(Category).filter_by(name=category_name).one() #Grabbing a specific ones (Category nth item group)
    itenig = session.query(Item).filter_by(category_id=catenig.id).all() #Grabbing category's item (Item nth item group)
    #If logged in, user will have the option to click add button to create new item for certain category.
    if 'username' not in login_session:
        return render_template('publicItems.html', cats=catenig, its=itenig, alls=allcatenig)
    else:
        return render_template('items.html', cats=catenig, its=itenig, alls=allcatenig)


#Function for viewing certain category's item's information and categoryself.
@app.route('/category/<category_name>/<item_name>/')
def showSpecificItem(category_name, item_name):
    specifiCate = session.query(Category).filter_by(name=category_name).one()
    specificIte = session.query(Item).filter_by(name=item_name).one()

    creator = getUserInfo(specificIte.user_id)

    #If logged in, user will have the option to click edit/delete button to create new item for certain category.
    if 'username' not in login_session:
        return render_template('publicSpecificItems.html',  sc=specifiCate, si=specificIte, creator=creator)
    else:
        return render_template('specificItems.html', sc=specifiCate, si=specificIte, creator=creator)

#Function for receiving request as POST and retrieving form as name, descrition, and category from HTMLself.
#Function will add new category item by loading it to stage and database afterwards.
@app.route('/category/add', methods=['GET', 'POST'])
def addSpecificItem():
    if 'username' not in login_session:
	    return redirect('/login')
    if request.method == 'POST':
        newCatItem = Item(name=request.form['name'], description = request.form['description'], category_id=request.form['category'], user_id=login_session['user_id'])
        session.add(newCatItem)
        session.commit()
        flash('New Item Successfully Created!')
        return redirect(url_for('showCategorys'))
    else:
        return render_template('addItems.html')

#Function for editing selected item.
#First, user selects the item. Then, request for POST will come in and see if it's name or descrition that's edited.
#Make the name or description equal to request form's name or description.
@app.route('/category/<item_name>/edit', methods=['GET', 'POST'])
def editSpecificItem(item_name):
    if 'username' not in login_session:
	    return redirect('/login')
    editedItem = session.query(Item).filter_by(name=item_name).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        flash('Selected Item Successfully Edited!')
        return redirect(url_for('showCategorys'))
    else:
        return render_template('editItems.html', editItemYo=editedItem)

#Function for deleting selected item.
#First, user selects the item. Then request for POST will come in.
#Append the delete function with selected item.
@app.route('/category/<item_name>/delete', methods=['GET', 'POST'])
def deleteSpecificItem(item_name):
    if 'username' not in login_session:
	    return redirect('/login')
    deleteItem = session.query(Item).filter_by(name=item_name).one()
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        flash('Selected Item Successfully Deleted!')
        return redirect(url_for('showCategorys'))
    else:
        return render_template('deleteItems.html', deleteItemYo=deleteItem)



@app.route('/category/JSON')
def showCategorysJSON():
    cate = session.query(Category).all()
    return jsonify(cate = [c.serialize for c in cate])


@app.route('/category/<category_name>/item/JSON')
def showItemJSON(category_name):
    catenig = session.query(Category).filter_by(name=category_name).one() #Grabbing a specific ones
    itenig = session.query(Item).filter_by(category_id=catenig.id).all() #Grabbing category's item
    return jsonify(itenig = [i.serialize for i in itenig])

#User helper function
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

#User ID is passed into the function and returns user object.
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

#Take email as input and return user ID number if email belongs to the user stored in our database.
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
