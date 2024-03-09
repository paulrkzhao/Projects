from app import app
from flask import Flask, request, redirect, url_for, session, render_template, flash, jsonify
from base64 import b64encode
from .models.user import User
from .models.business import Business
from .models.review import Review
from .models.db_operations import db_operations
import os
from werkzeug.utils import secure_filename
import csv


UPLOAD_FOLDER = 'app/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        
        email = request.form['email']
        password = request.form['password']

        info = User.getUserByEmail(email)
        if info:
            user = User(*info)
            
            session['user_id'] = info[0]

            if user and user.checkPassword(password):
        
                return redirect(url_for('main_page'))  # Redirect to the main page after login
            else:
                # If login failed
                return render_template('index.html', error="Invalid credentials")
                
    return render_template('index.html')


@app.route('/business-login', methods=['GET', 'POST'])
def business_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        info = Business.getBusinessByEmail(email)
        if info:
            business = Business(*info)
            if business and business.checkPassword(password):
                session['business_id'] = info[0]  # Set business ID in session
                return redirect(url_for('business_portal'))
            else:
                return render_template('business-login.html', error="Invalid credentials")

    return render_template('business-login.html')


@app.route('/business-portal', methods=['GET', 'POST'])
def business_portal():
    db_ops = db_operations()
    categories = db_ops.get_all('Categories')

    business_id = session.get('business_id')
    if not business_id:
        return redirect(url_for('business_login'))

    business_info = Business.getBusinessByID(business_id)
    if not business_info:
        flash("Business information not found", "error")
        return redirect(url_for('business_login'))

    business = Business(*business_info)

    reviews = Business.getReviews(business_id)
    
    photo_binary = business.getPhoto()
    photo_base64 = b64encode(photo_binary).decode("utf-8") if photo_binary else None

    return render_template('business-portal.html', BusinessPhoto=photo_base64, business_info=business_info, reviews=reviews, categories=categories)


@app.route('/create-business', methods=['GET', 'POST'])
def create_business():
    if request.method == 'POST':
        
        businessName = request.form['business_name']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        description = request.form['description']
        password = request.form['password']
        passwordConf = request.form['passwordConf']

        if password != passwordConf:
            return render_template('create-business.html', error="Passwords do not match")

        business = Business.getBusinessByEmail(email)
        if business:
            return render_template('create-business.html', error="Email already in use")
        else:
            newBusiness = Business.createNew(businessName, address, phone, password, email, description)
    # Return the business creation page
    return render_template('create-business.html')

@app.route('/create-user', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':

        # Return the account creation page
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        passwordConf = request.form['passwordConf']

        if password != passwordConf:
            return render_template('create-user.html', error = "Passwords do not match")

        user = User.getUserByEmail(email)
        if user:
            return render_template('create-user.html', error ="Email already in use")
        else:
            newUser = User.createNew(username, password, email)
    # Return the business creation page
    return render_template('create-user.html')

@app.route('/main-page', methods=['GET', 'POST'])
def main_page():
    db_ops = db_operations()
    businesses = Business.getAll()
    temp_businesses = []
    for business in businesses:
       
        temp_business = business
        if isinstance(business, tuple):
            if business[10]:
                photo = b64encode(business[10]).decode("utf-8")
                temp_business += (photo,)
            else:
                with open("app/static/images/defaultStore.png", "rb") as file:
                    blob_data = file.read()
                    photo = b64encode(blob_data).decode("utf-8")
                    temp_business += (photo,)
            category_id = business[11]
            if category_id:
                # Fetch the category name from the Categories table
                category_name = db_ops.get_category_name(category_id)
                # Add the category name to the business dictionary
                temp_business += (category_name,)
            else:
                temp_business += ("",)
            temp_businesses.append(temp_business)

                
    return render_template('main-page.html', Businesses=temp_businesses)

@app.route('/business/<int:id>')
def business_page(id):
    business = Business.getBusinessByID(id)  # Fetch the business details

    # Fetch reviews for the business
    reviews = Business.getReviews(id)
    reviews_decoded = []
    if reviews:
        for review in reviews:
            if(review[-1]):
                review += (b64encode(review[-1]).decode("utf-8"), )
            else:
                review += ('', )
            reviews_decoded.append(review)
    return render_template('business_page.html', business=business, reviews=reviews_decoded)


@app.route('/search-results')
def search_results():
    query = request.args.get('query')

    # Perform search logic using your Business class
    results = Business.search(query)

    # Render the search results template with the search results
    return render_template('search_results.html', results=results)

def convertToBinaryData(filename):
        # Convert digital data to binary format
        with open(filename, 'rb') as file:
            binaryData = file.read()
        return binaryData


@app.route('/submit-review/<int:business_id>', methods=['POST'])
def submit_review(business_id):
    user_id = session['user_id']
    print("userid:", user_id)
    if not user_id:
        flash("You must be logged in to submit a review.", "error")
        return redirect(url_for('business_page', id=business_id))

    rating = request.form['rating']
    review_text = request.form['reviewText']
    
    db_ops = db_operations()
    photo_id = None
    photo = request.files['photo']
    print("photo:", photo)
    if photo and allowed_file(photo.filename):
        filename = secure_filename(photo.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            photo.save(filepath)
            binaryData = convertToBinaryData(filepath)
            db_ops.send_query("INSERT INTO Photos (photo) VALUES (%s)", (binaryData,))
            photo_id = db_ops.getLastID()
            print("id:", photo_id)
        except Exception as e:
            flash(f"An error occurred: {e}")
        finally:
            if os.path.exists(filepath):
                os.remove(filepath) 

    newReview = Review(business_id, user_id, rating, review_text, photo_id)
    newReview.addReview()

    query = f"SELECT AVG(Rating) FROM Reviews WHERE BusinessID = {business_id}"
    avg = db_ops.get_agg(query)
    b_info = Business.getBusinessByID(business_id)

    business = Business(*b_info) 
    
    business.updateRating(avg[0])
    # Add logic to save the review to your database here
    
    flash("Review submitted successfully!", "success")
    return redirect(url_for('business_page', id=business_id))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/update-business-info', methods=['POST'])
def update_business_info():

    business_id = session.get('business_id')
    business_info = Business.getBusinessByID(business_id)
    business = Business(*business_info)

    if not business_id:
        flash("You need to be logged in to update business information.", "error")
        return redirect(url_for('business_login'))

    # Extract form data
    business_name = request.form.get('business_name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    email = request.form.get('email')
    description = request.form.get('description')
    
    category_id = request.form.get('categoryID')


    file = request.files.get('profile_picture')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
            business.setPhoto(filepath)
            flash("Profile picture updated successfully!")
        except Exception as e:
            flash(f"An error occurred: {e}")
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)  # Remove the file after saving to DB

        flash("Profile picture updated successfully!")
        return redirect(url_for('business_portal'))

    business.updateDetails(business_name, address, phone, email, description, category_id)

    # Save changes to the database (assuming your Business class has a method to do this)
    business.updateDetails(business_name, address, phone, email, description, category_id)

    flash("Business information updated successfully!", "success")
    return redirect(url_for('business_portal'))


@app.route('/logout', methods=['POST'])
def logout():
    # Remove 'user_id' from session
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/get-categories', methods=['GET'])
def get_categories():
    # Fetch categories from the database
    categories = db_operations.get_categories()
    return jsonify(categories)

@app.route('/submit-business', methods=['POST'])
def submit_business():
    # Create an instance of the db_operations class
    db_ops = db_operations()

    selected_category_name = request.form['categoryName']
    category_id = db_ops.get_category_id(selected_category_name)

    # Check if category_id is not None before further processing
    if category_id is not None:
        # Code to update the businesses table with the category_id
        # (You can use db_ops.send_query or any other method you have in your db_operations class)

        flash("Business submitted successfully!", "success")
    else:
        flash("Invalid category selected", "error")

    # Don't forget to close the connection when done
    db_ops.destructor()

    return redirect(url_for('main_page'))


@app.route('/delete-business/<int:business_id>', methods=['POST'])
def delete_business(business_id):
    # Check if the logged-in business is the one being deleted
    if 'business_id' in session and session['business_id'] == business_id:
        business = Business.getBusinessByID(business_id)
        business = Business(*business)
        if business:
            business.delete()
            flash("Business account deleted successfully.", "success")
            # Add any additional clean-up here (e.g., log out the user)
        else:
            flash("Business not found.", "error")
    else:
        flash("Unauthorized request.", "error")
    return redirect(url_for('index'))

@app.route('/top_rated_businesses')
def top_rated_businesses():
    query = """
        SELECT B.BusinessName, B.Address, B.Phone, B.Email, B.Description, A.AvgRating
        FROM Businesses B
        JOIN (
            SELECT BusinessID, AVG(Rating) as AvgRating
            FROM Reviews
            GROUP BY BusinessID
        ) A ON B.BusinessID = A.BusinessID
        ORDER BY A.AvgRating DESC;
        """
    print("inside")
    db_ops = db_operations()
    output = db_ops.get_custom_query(query)
    print(output)
    with open("top_rated_businesses.csv", 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            # Write the header (optional, adjust field names as needed)
            writer.writerow(['BusinessName', 'Address', 'Phone', 'Email', 'Description', 'Website', 'HoursOfOp', 'AvgRating'])

            # Write the data
            for row in output:
                writer.writerow(row)
    return redirect(url_for('main_page'))