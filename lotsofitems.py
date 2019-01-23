from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

User1 = User(name="Min Cho", email="MINWOOUSA@gmail.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
             #Min Woo Cho Senior Photo.jpg
session.add(User1)
session.commit()


category1 = Category(name="Clothes", user_id=1)
session.add(category1)
session.commit()

item1 = Item(name="LouisVuitton", description= "LouisVuitton is a famous designer company, and its' really expensive.", category=category1, user_id=1)
session.add(item1)
session.commit()

item2 = Item(name="Supreme", description= "For Skateboard brand made in NY. Everyone dies for it.", category=category1, user_id=1)
session.add(item2)
session.commit()


category2 = Category(name="Technology", user_id=1)
session.add(category2)
session.commit()

item1 = Item(name="Apple", description= "Apple is one of the greatest inventions of all time.", category=category2, user_id=1)
session.add(item1)
session.commit()

item2 = Item(name="Tesla", description= "Tesla is created by Elon Musk aimed to replace gas cars to electrical cars.", category=category2, user_id=1)
session.add(item2)
session.commit()


category3 = Category(name="Jobs", user_id=1)
session.add(category3)
session.commit()

item1 = Item(name="PaperEngineering", description= "Pulp and paper is dying, but it's still really important.", category=category3, user_id=1)
session.add(item1)
session.commit()

item2 = Item(name="SoftwareEngineering", description= "Software engineering is aimed for software development.", category=category3, user_id=1)
session.add(item2)
session.commit()

print "added category's items!"
