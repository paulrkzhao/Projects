from .db_operations import db_operations
from datetime import date


class Review:
    def __init__(self, userID, businessID, score, text, photoID):
        self.userID = userID
        self.businessID = businessID
        self.score = score
        self.text = text
        self.photoID = photoID
        self.date = date.today()

    def addReview(self):
        db_ops = db_operations()
        query = "INSERT INTO Reviews (BusinessID, userID, Rating, ReviewText, ReviewDate, PhotoID) VALUES (%s, %s, %s, %s, %s, %s);"
        params = (self.userID, self.businessID, self.score, self.text, self.date, self.photoID)
        db_ops.send_query(query, params)

     